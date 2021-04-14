from connaisseur.validators.interface import ValidatorInterface
from connaisseur.image import Image


class CosignValidator(ValidatorInterface):
    def __init__(self, name: str, **kwargs):
        raise NotImplementedError

    def validate(self, image: Image, **kwargs):
        pass
