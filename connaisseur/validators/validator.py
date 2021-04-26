from connaisseur.validators.notrayv1.notaryv1_validator import NotaryV1Validator
from connaisseur.validators.notaryv2.notaryv2_validator import NotaryV2Validator
from connaisseur.validators.cosign.cosign_validator import CosignValidator
from connaisseur.validators.static.static_validator import StaticValidator
from connaisseur.exceptions import NoSuchClassError


class Validator:
    class_map = {
        "notaryv1": NotaryV1Validator,
        "notaryv2": NotaryV2Validator,
        "cosign": CosignValidator,
        "static": StaticValidator,
    }

    def __new__(cls, type: str, **kwargs):
        try:
            return cls.class_map[type](**kwargs)
        except KeyError:
            msg = f"{type} is not a supported validator."
            raise NoSuchClassError(message=msg)
