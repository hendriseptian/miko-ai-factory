import base64
import io

from huggingface_hub import InferenceClient

from .base import ImageProvider


class HuggingFaceImageProvider(ImageProvider):
    """
    Hugging Face Inference Provider
    for Miko image generation.

    Uses Hugging Face InferenceClient
    with FLUX.1-schnell.
    """

    name = "huggingface"

    def __init__(self, env):

        self.env = env

        self.api_key = getattr(
            env,
            "HUGGINGFACE_API_KEY",
            None
        )

        self.model = getattr(
            env,
            "HUGGINGFACE_IMAGE_MODEL",
            "black-forest-labs/FLUX.1-schnell"
        )

        self.provider = getattr(
            env,
            "HUGGINGFACE_IMAGE_PROVIDER",
            "fal-ai"
        )

        if not self.api_key:
            raise RuntimeError(
                "HUGGINGFACE_API_KEY is not configured."
            )

        self.client = InferenceClient(
            provider=self.provider,
            api_key=self.api_key
        )

    async def generate(
        self,
        prompt,
        aspect_ratio="9:16",
        reference_images=None
    ):

        if not prompt:
            raise ValueError(
                "Image prompt is required."
            )

        # ==========================================
        # ASPECT RATIO
        # ==========================================

        width = 768
        height = 1344

        if aspect_ratio == "16:9":

            width = 1344
            height = 768

        elif aspect_ratio == "1:1":

            width = 1024
            height = 1024

        # ==========================================
        # IMAGE GENERATION
        # ==========================================

        image = self.client.text_to_image(

            prompt=prompt,

            model=self.model,

            width=width,

            height=height

        )

        # ==========================================
        # VALIDATE RESULT
        # ==========================================

        if image is None:

            raise RuntimeError(
                "Hugging Face returned no image."
            )

        # ==========================================
        # CONVERT IMAGE TO PNG BYTES
        # ==========================================

        image_buffer = io.BytesIO()

        image.save(
            image_buffer,
            format="PNG"
        )

        image_bytes = (
            image_buffer.getvalue()
        )

        if not image_bytes:

            raise RuntimeError(
                "Hugging Face returned empty image data."
            )

        # ==========================================
        # BASE64
        # ==========================================

        image_data = base64.b64encode(
            image_bytes
        ).decode("ascii")

        # ==========================================
        # RESULT
        # ==========================================

        return {

            "provider":
                self.name,

            "provider_backend":
                self.provider,

            "model":
                self.model,

            "mime_type":
                "image/png",

            "aspect_ratio":
                aspect_ratio,

            "image_size":
                f"{width}x{height}",

            "data":
                image_data

        }
