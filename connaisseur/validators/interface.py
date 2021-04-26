from connaisseur.image import Image
from connaisseur.admission_request import AdmissionRequest


class ValidatorInterface:
    def __init__(self, name: str, **kwargs):
        """
        Initializes a validator based on the data from the configuration file.
        """
        pass

    def validate(self, image: Image, **kwargs) -> str:
        """
        Validates an admission request, using the extra arguments from the image policy.

        Returns a list of trusted digests.
        """
        raise NotImplementedError

    @property
    def healthy(self):
        return True

    def __str__(self):
        return self.name
