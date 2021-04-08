from connaisseur.validators.notrayv1.notaryv1validator import NotaryV1Validator
from connaisseur.validators.notaryv2.notaryv2validator import NotaryV2Validator
from connaisseur.validators.cosign.cosignvalidator import CosignValidator
from connaisseur.exceptions import NoSuchClassError


class Validator:
    def __new__(cls, type: str, **kwargs):
        if type == "notaryv1":
            return super(Validator, cls).__new__(NotaryV1Validator)
        elif type == "notaryv2":
            return super(Validator, cls).__new__(NotaryV2Validator)
        elif type == "cosign":
            return super(Validator, cls).__new__(CosignValidator)
        else:
            raise NoSuchClassError
