import pytest
from ... import conftest as fix
import connaisseur.validators.notrayv1.notaryv1_validator as nv1
from connaisseur.image import Image
import connaisseur.exceptions as exc


@pytest.fixture
def sample_nv1(sample_notary):
    val = nv1.NotaryV1Validator(
        **{"name": "dockerhub", "host": "none", "root_keys": ["none"]}
    )
    val.notary = sample_notary
    return val


@pytest.mark.parametrize(
    "val_config", [{"name": "nv1", "host": "me", "root_keys": ["not_empty"]}]
)
def test_init(m_notary, val_config):
    val = nv1.NotaryV1Validator(**val_config)
    assert val.name == val_config["name"]


@pytest.mark.parametrize(
    "image, key, delegations, digest, exception",
    [
        (
            "securesystemsengineering/alice-image:test",
            None,
            ["phbelitz", "chamsen"],
            "ac904c9b191d14faf54b7952f2650a4bb21c201bf34131388b851e8ce992a652",
            fix.no_exc(),
        ),
        (
            (
                (
                    "securesystemsengineering/alice-image@sha256"
                    ":ac904c9b191d14faf54b7952f2650a4bb21"
                    "c201bf34131388b851e8ce992a652"
                )
            ),
            None,
            ["phbelitz", "chamsen"],
            "ac904c9b191d14faf54b7952f2650a4bb21c201bf34131388b851e8ce992a652",
            fix.no_exc(),
        ),
        (
            "securesystemsengineering/sample-image:sign",
            None,
            [],
            "a154797b8300165956ee1f16d98f3a1426301c1168f0462c73ce9bc03361cabf",
            fix.no_exc(),
        ),
        (
            "securesystemsengineering/sample-image:v1",
            None,
            [],
            "799c0fa8aa4c9fbff5a99aef1b4b5c3abb9c2f34134345005982fad3489893c7",
            fix.no_exc(),
        ),
        (
            "securesystemsengineering/charlie-image:test2",
            "charlie",
            ["del1"],
            "",
            pytest.raises(exc.InsufficientTrustDataError),
        ),
        (
            "securesystmesengineering/dave-image:test",
            "charlie",
            ["del1", "del2"],
            "",
            pytest.raises(exc.AmbiguousDigestError),
        ),
        (
            "securesystemsengineering/alice-image:missingtag",
            None,
            [],
            "ac904c9b191d14faf54b7952f2650a4bb21c201bf34131388b851e8ce992a652",
            pytest.raises(exc.NotFoundException, match=r".*digest.*"),
        ),
    ],
)
def test_validate(
    sample_nv1,
    m_trust_data,
    m_request,
    m_expiry,
    image: str,
    key: str,
    delegations: list,
    digest: str,
    exception,
):
    with exception:
        assert sample_nv1.validate(Image(image), key, delegations) == digest


@pytest.mark.parametrize(
    "url, acr, health",
    [
        ("healthy.url", False, True),
        ("unhealthy.url", False, False),
        ("exceptional.url", False, False),
        ("irrelevant.url", True, True),
    ],
)
def test_healthy(m_request, url, acr, health):
    val = nv1.NotaryV1Validator(
        **{"name": "sample", "host": url, "root_keys": ["not_empty"], "is_acr": acr}
    )
    assert val.healthy is health


@pytest.mark.parametrize(
    "delegation_role, out",
    [
        ("phbelitz", "targets/phbelitz"),
        ("chamsen", "targets/chamsen"),
        ("targets/releases", "targets/releases"),
    ],
)
def test_normalize_delegations(delegation_role: str, out: str):
    assert (
        nv1.NotaryV1Validator._NotaryV1Validator__normalize_delegation(delegation_role)
        == out
    )


req_delegations1 = ["targets/phbelitz", "targets/chamsen"]
req_delegations2 = []
req_delegations3 = ["targets/someuserthatdidnotsign"]
req_delegations4 = ["targets/del1"]
req_delegations5 = ["targets/del2"]
root_keys = [
    (
        "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEtR5kwrDK22SyCu7WMF8tCjVgeORA"
        "S2PWacRcBN/VQdVK4PVk1w4pMWlz9AHQthDGl+W2k3elHkPbR+gNkK2PCA=="
    ),
    (
        "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEtkQuBJ/wL1MEDy/6kgfSBls04MT1"
        "aUWM7eZ19L2WPJfjt105PPieCM1CZybSZ2h3O4+E4hPz1X5RfmojpXKePg=="
    ),
]
targets1 = [
    {
        "test": {
            "hashes": {"sha256": "rJBMmxkdFPr1S3lS8mUKS7IcIBvzQTE4i4UejOmSplI="},
            "length": 1993,
        }
    },
    {
        "test": {
            "hashes": {"sha256": "rJBMmxkdFPr1S3lS8mUKS7IcIBvzQTE4i4UejOmSplI="},
            "length": 1993,
        }
    },
]
targets2 = [
    {
        "sign": {
            "hashes": {"sha256": "oVR5e4MAFllW7h8W2Y86FCYwHBFo8EYsc86bwDNhyr8="},
            "length": 1994,
        },
        "v1": {
            "hashes": {"sha256": "eZwPqKpMn7/1qZrvG0tcOrucLzQTQ0UAWYL600iYk8c="},
            "length": 1994,
        },
    }
]
targets3 = [
    {
        "test": {
            "hashes": {"sha256": "TgYbzUu1pMskoZbfWdcj2RF0HVUg+J4034p5LVa97j4="},
            "length": 528,
        }
    }
]
targets4 = [
    {
        "test": {
            "hashes": {"sha256": "pkeg+cgtxfPnxL1kg7SWpJ1XC0/bH+rL/VfpZdKh1mI="},
            "length": 528,
        }
    }
]
targets5 = [
    {
        "test": {
            "hashes": {"sha256": "K3tQZXLk87nedST/hCh9uI7SSwz5RIp7BK0GZOze9xs="},
            "length": 528,
        }
    }
]
targets6 = [
    {
        "test": {
            "hashes": {"sha256": "qCXo6VDc64HH2G9tNOTkcwfpjzVQXRgNQE4ZR0KigHk="},
            "length": 528,
        }
    }
]


@pytest.mark.parametrize(
    "image, delegations, key, targets, exception",
    [
        (
            "securesystemsengineering/alice-image",
            req_delegations1,
            root_keys[0],
            targets1,
            fix.no_exc(),
        ),
        (
            "securesystemsengineering/sample-image",
            req_delegations2,
            root_keys[0],
            targets2,
            fix.no_exc(),
        ),
        (
            "securesystemsengineering/bob-image",
            req_delegations2,
            root_keys[1],
            targets3,
            fix.no_exc(),
        ),
        (
            "securesystemsengineering/charlie-image",
            req_delegations2,
            root_keys[1],
            targets4,
            fix.no_exc(),
        ),
        (
            "securesystemsengineering/dave-image",
            req_delegations2,
            root_keys[1],
            targets5,
            fix.no_exc(),
        ),
        (
            "securesystemsengineering/dave-image",
            req_delegations4,
            root_keys[1],
            targets5,
            fix.no_exc(),
        ),
        (
            "securesystemsengineering/dave-image",
            req_delegations5,
            root_keys[1],
            targets6,
            fix.no_exc(),
        ),
    ],
)
def test_process_chain_of_trust(
    sample_nv1,
    m_request,
    m_trust_data,
    m_expiry,
    image: str,
    delegations: list,
    key: str,
    targets: list,
    exception,
):
    with exception:
        assert (
            sample_nv1._NotaryV1Validator__process_chain_of_trust(
                Image(image), delegations, key
            )
            == targets
        )
