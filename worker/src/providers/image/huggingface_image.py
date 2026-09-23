import base64
import json

from workers import fetch

from .base import ImageProvider


class HuggingFaceImageProvider(ImageProvider):
    """
    Hugging Face Inference Provider
    for Miko image generation.

    Uses direct HTTP fetch to Hugging Face Router.
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

        self.base_url = "https://router.huggingface.co"

    async def generate(
        self,
        prompt,
        aspect_ratio="9:16",
        reference_images=None
    ):
        if not self.api_key:
            raise RuntimeError(
                "HUGGINGFACE_API_KEY is not configured."
            )

        if not prompt:
            raise ValueError(
                "Image prompt is required."
            )

        # ---------------------------------
        # IMAGE SIZE
        # ---------------------------------

        width = 768
        height = 1344

        if aspect_ratio == "16:9":
            width = 1344
            height = 768

        elif aspect_ratio == "1:1":
            width = 1024
            height = 1024

        # ---------------------------------
        # HUGGING FACE ROUTER
        # ---------------------------------

        url = (
            f"{self.base_url}"
            f"/{self.provider}"
            f"/models/"
            f"{self.model}"
        )

        payload = {
            "inputs": prompt,
            "parameters": {
                "width": width,
                "height": height,
                "num_inference_steps": 4
            }
        }

        response = await fetch(
            url,
            method="POST",
            headers={
                "Authorization": (
                    f"Bearer {self.api_key}"
                ),
                "Content-Type": "application/json",
                "Accept": "image/png"
            },
            body=json.dumps(
                payload,
                ensure_ascii=False
            )
        )

        # ---------------------------------
        # ERROR HANDLING
        # ---------------------------------

        if not response.ok:
            error_text = await response.text()

            raise RuntimeError(
                "Hugging Face Image API error "
                f"{response.status}: "
                f"{error_text}"
            )

        # ---------------------------------
        # IMAGE DATA
        # ---------------------------------

        image_buffer = await response.array_buffer()

        if not image_buffer:
            raise RuntimeError(
                "Hugging Face returned empty image data."
            )

        image_data = base64.b64encode(
            bytes(image_buffer)
        ).decode("ascii")

        mime_type = (
            response.headers.get("content-type")
            or "image/png"
        )

        mime_type = mime_type.split(
            ";",
            1
        )[0].strip()

        # ---------------------------------
        # RESULT
        # ---------------------------------

        return {
            "provider": self.name,
            "provider_backend": self.provider,
            "model": self.model,
            "mime_type": mime_type,
            "aspect_ratio": aspect_ratio,
            "image_size": (
                f"{width}x{height}"
            ),
            "data": image_data
        }
