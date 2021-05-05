from connaisseur.image import Image


class Container:
    image: Image
    index: int
    container_type: str

    def __init__(self, image: str, index: int, container_type: str):
        self.image = Image(image)
        self.index = index
        self.container_type = container_type

    def __eq__(self, other):
        return self.image == other.image
