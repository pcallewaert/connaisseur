from connaisseur.validators.interface import ValidatorInterface
from connaisseur.image import Image
from connaisseur.exceptions import ValidationError
import logging


class StaticValidator(ValidatorInterface):

    name: str
    approve: bool

    def __init__(self, name: str, approve: bool, **kwargs):
        self.name = name
        self.approve = approve

    def validate(self, image: Image, **kwargs):
        if not self.approve:
            msg = "Static deny."
            raise ValidationError(message=msg)
        return None
