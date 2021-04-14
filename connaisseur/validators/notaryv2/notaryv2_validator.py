from connaisseur.validators.interface import ValidatorInterface
from connaisseur.image import Image


class NotaryV2Validator(ValidatorInterface):
    def __init__(self, name: str, host: str, **kwargs):
        raise NotImplementedError

    def validate(self, image: Image, **kwargs):
        pass
