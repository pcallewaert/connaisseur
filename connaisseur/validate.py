import base64
from multiprocessing import Pool
from connaisseur.image import Image
from connaisseur.config import Notary
from connaisseur.key_store import KeyStore
from connaisseur.util import normalize_delegation
from connaisseur.sigstore_validator import get_cosign_validated_digests
from connaisseur.tuf_role import TUFRole
from connaisseur.exceptions import (
    NotFoundException,
    InsufficientTrustDataError,
    AmbiguousDigestError,
)
from connaisseur.policy import Rule
from connaisseur.trust_data import TrustData
import connaisseur.debug_timer as dbgt


def get_trusted_digest(notary_config: Notary, image: Image, policy_rule: Rule):
    """
    Searches in given notary server(`host`) for trust data, that belongs to the
    given `image`, by using the notary API. Also checks whether the given
    `policy_rule` complies.

    Returns the signed digest, belonging to the `image` or throws if validation fails.
    """
    # get root key
    pub_key = notary_config.get_key(policy_rule.key)
    if not pub_key:
        msg = "Unable to get public root key from configuration."
        raise NotFoundException(message=msg)

    if notary_config.is_cosign:
        # validate with cosign
        digests = get_cosign_validated_digests(str(image), pub_key)
    else:
        # prepend `targets/` to the required delegation roles, if not already present
        req_delegations = list(map(normalize_delegation, policy_rule.delegations))

        # get list of targets fields, containing tag to signed digest mapping from
        # `targets.json` and all potential delegation roles
        dbgt.start(f"{str(image)}_process_chain")
        signed_image_targets = __process_chain_of_trust(
            notary_config, image, req_delegations, pub_key
        )
        dbgt.stop(f"{str(image)}_process_chain")

        # search for digests or tag, depending on given image
        search_image_targets = (
            __search_image_targets_for_digest
            if image.has_digest()
            else __search_image_targets_for_tag
        )

        # filter out the searched for digests, if present
        digests = list(
            map(lambda x: search_image_targets(x, image), signed_image_targets)
        )

        # in case certain delegations are needed, `signed_image_targets` should only
        # consist of delegation role targets. if searched for the signed digest, none of
        # them should be empty
        if req_delegations and not all(digests):
            msg = "Not all required delegations have trust data for image {image_name}."
            raise InsufficientTrustDataError(message=msg, image_name=str(image))

    # filter out empty results and squash same elements
    digests = set(filter(None, digests))

    # no digests could be found
    if not digests:
        msg = "Unable to find signed digest for image {image_name}."
        raise NotFoundException(message=msg, image_name=str(image))

    # if there is more than one valid digest in the set, no decision can be made, which
    # to chose
    if len(digests) > 1:
        msg = "Found multiple signed digest for image {image_name}."
        raise AmbiguousDigestError(message=msg, image_name=str(image))

    return digests.pop()


def __process_chain_of_trust(
    notary_config: Notary, image: Image, req_delegations: list, pub_root_key: str
):  # pylint: disable=too-many-branches
    """
    Processes the whole chain of trust, provided by the notary server (`notary_config`)
    for any given `image`. The 'root', 'snapshot', 'timestamp', 'targets' and
    potentially 'targets/releases' are requested and validated.
    Additionally, it is checked whether all required delegations are valid.

    Returns the signed image targets, which contain the digests.

    Raises `NotFoundExceptions` should no required delegetions be present in
    the trust data, or no image targets be found.
    """
    key_store = KeyStore(pub_root_key)
    tuf_roles = ["root", "snapshot", "timestamp", "targets"]

    # load all trust data
    dbgt.start(f"{str(image)}_getting_trust_data")
    with Pool() as pool:
        try:
            result = pool.starmap_async(
                notary_config.get_trust_data,
                [(image, TUFRole(role)) for role in tuf_roles],
            )
            trust_data_list = result.get(timeout=30)
        except Exception as err:
            msg = "Error retrieving trust data form notary."
            raise NotFoundException(message=msg, notary=str(notary_config)) from err
    trust_data = {
        tuf_roles[i]: TrustData(trust_data_list[i], tuf_roles[i])
        for i in range(len(tuf_roles))
    }
    dbgt.stop(f"{str(image)}_getting_trust_data")

    # validate signature and expiry data of and load root file
    # this does NOT conclude the validation of the root file. To prevent rollback/freeze
    # attacks, the hash still needs to be validated against the snapshot file
    root_trust_data = trust_data["root"]
    root_trust_data.validate_signature(key_store)
    root_trust_data.validate_expiry()

    key_store.update(root_trust_data)

    # validate timestamp file to prevent freeze attacks
    # validates signature and expiry data
    # there is no hash to verify it against since it is short lived
    # TODO should we ensure short expiry duration here?
    timestamp_trust_data = trust_data["timestamp"]
    timestamp_trust_data.validate(key_store)

    # validate snapshot file signature against the key defined in the root file
    # and its hash against the one from the timestamp file
    # and validate expiry
    snapshot_trust_data = trust_data["snapshot"]
    snapshot_trust_data.validate_signature(key_store)

    timestamp_key_store = KeyStore()
    timestamp_key_store.update(timestamp_trust_data)
    snapshot_trust_data.validate_hash(timestamp_key_store)

    snapshot_trust_data.validate_expiry()

    # now snapshot and timestamp files are validated, we can be safe against
    # rollback and freeze attacks if the root file matches the hash of the snapshot file
    # (or the root key has been compromised, which Connaisseur cannot defend against)
    snapshot_key_store = KeyStore()
    snapshot_key_store.update(snapshot_trust_data)
    root_trust_data.validate_hash(snapshot_key_store)

    # if we are safe at this point, we can add the snapshot data to the main KeyStore
    # and proceed with validating the targets file and (potentially) delegation files
    key_store.update(snapshot_trust_data)
    targets_trust_data = trust_data["targets"]
    targets_trust_data.validate(key_store)
    key_store.update(targets_trust_data)

    # if the 'targets.json' has delegation roles defined, get their trust data
    # as well
    delegations = trust_data["targets"].get_delegations()
    if trust_data["targets"].has_delegations():
        __update_with_delegation_trust_data(
            trust_data, delegations, key_store, notary_config, image
        )

    # validate existence of required delegations
    __validate_all_required_delegations_present(req_delegations, delegations)

    # if certain delegations are required, then only take the targets fields of the
    # required delegation JSONs. otherwise take the targets field of the targets JSON, as
    # long as no delegations are defined in the targets JSON. should there be delegations
    # defined in the targets JSON the targets field of the releases JSON will be used.
    # unfortunately there is a case, where delegations could have been added to a
    # repository, but no signatures were created using the delegations. in this special
    # case, the releases JSON doesn't exist yet and the targets JSON must be used instead
    if req_delegations:
        if not all(trust_data[target_role] for target_role in req_delegations):
            tuf_roles = [
                target_role
                for target_role in req_delegations
                if not trust_data[target_role]
            ]
            msg = (
                "Unable to find trust data for delegation "
                "roles {tuf_roles} and image {image_name}."
            )
            raise NotFoundException(
                message=msg, tuf_roles=str(tuf_roles), image_name=str(image)
            )

        image_targets = [
            trust_data[target_role].signed.get("targets", {})
            for target_role in req_delegations
        ]
    else:
        targets_key = (
            "targets/releases"
            if trust_data["targets"].has_delegations()
            and trust_data["targets/releases"]
            else "targets"
        )
        image_targets = [trust_data[targets_key].signed.get("targets", {})]

    if not any(image_targets):
        msg = "Unable to find any image digests in trust data."
        raise NotFoundException(message=msg)

    return image_targets


def __search_image_targets_for_digest(trust_data: dict, image: Image):
    """
    Searches in the `trust_data` for a signed digest, given an `image` with
    digest.
    """
    image_digest = base64.b64encode(bytes.fromhex(image.digest)).decode("utf-8")
    if image_digest in {data["hashes"]["sha256"] for data in trust_data.values()}:
        return image.digest

    return None


def __search_image_targets_for_tag(trust_data: dict, image: Image):
    """
    Searches in the `trust_data` for a digest, given an `image` with tag.
    """
    image_tag = image.tag
    if image_tag not in trust_data:
        return None

    base64_digest = trust_data[image_tag]["hashes"]["sha256"]
    return base64.b64decode(base64_digest).hex()


def __update_with_delegation_trust_data(
    trust_data, delegations, key_store, notary_config, image
):
    with Pool() as pool:
        try:
            result = pool.starmap_async(
                notary_config.get_delegation_trust_data,
                [(image, TUFRole(delegation)) for delegation in delegations],
            )
            delegation_trust_data_list = result.get(timeout=30)
        except Exception as err:
            msg = "Error retrieving delegation trust data form notary."
            raise NotFoundException(message=msg, notary=str(notary_config)) from err

    # when delegations are added to the repository, but weren't yet used for signing, the
    # delegation files don't exist yet and are `None`. in this case validation must be
    # skipped
    delegation_trust_data = {
        delegations[i]: TrustData(delegation_trust_data_list[i], delegations[i])
        for i in range(len(delegations))
        if delegation_trust_data_list[i]
    }

    for delegation in delegation_trust_data:
        delegation.validate(key_store)
    trust_data.update(delegation_trust_data)


def __validate_all_required_delegations_present(
    required_delegations, present_delegations
):
    if required_delegations:
        if present_delegations:
            req_delegations_set = set(required_delegations)
            delegations_set = set(present_delegations)

            delegations_set.discard("targets/releases")

            # make an intersection between required delegations and actually
            # present ones
            if not req_delegations_set.issubset(delegations_set):
                missing = list(req_delegations_set - delegations_set)
                msg = (
                    "Unable to find delegation roles {delegation_roles} in trust data."
                )
                raise NotFoundException(message=msg, delegation_roles=str(missing))
        else:
            msg = "Unable to find any delegations in trust data."
            raise NotFoundException(message=msg)
