class ImageProvider:
    """
    Base interface for Miko image generation providers.

    Providers must implement generate().
    """

    name = "base"

    async def generate(
        self,
        prompt,
        aspect_ratio="9:16",
        reference_images=None
    ):
        raise NotImplementedError(
            "Image provider must implement generate()."
        )
