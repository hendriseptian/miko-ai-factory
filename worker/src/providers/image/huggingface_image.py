import base64

from workers import fetch

from .base import ImageProvider


class HuggingFaceImageProvider(ImageProvider):
    """
    Hugging Face Image Generation Provider.

    Uses Hugging Face Inference Providers
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

        self.base_url = (
            "https://router.huggingface.co"
            "/hf-inference/models/"
        )

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

        # ------------------------------------------
        # Aspect ratio
        # ------------------------------------------

        width = 768
        height = 1344

        if aspect_ratio == "16:9":

            width = 1344
            height = 768

        elif aspect_ratio == "1:1":

            width = 1024
            height = 1024

        # ------------------------------------------
        # Hugging Face endpoint
        # ------------------------------------------

        url = (
            f"{self.base_url}"
            f"{self.model}"
        )

        # ------------------------------------------
        # Request payload
        # ------------------------------------------

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
                "Authorization":
                    f"Bearer {self.api_key}",

                "Content-Type":
                    "application/json",

                "Accept":
                    "image/png"
            },
            body=self._json_dumps(payload)
        )

        # ------------------------------------------
        # Error handling
        # ------------------------------------------

        if not response.ok:

            error_text = await response.text()

            raise RuntimeError(
                f"Hugging Face Image API error "
                f"{response.status}: "
                f"{error_text}"
            )

        # ------------------------------------------
        # Read generated image bytes
        # ------------------------------------------

        image_bytes = await response.array_buffer()

        if not image_bytes:

            raise RuntimeError(
                "Hugging Face returned empty image data."
            )

        # ------------------------------------------
        # Convert bytes → Base64
        # ------------------------------------------

        image_data = base64.b64encode(
            bytes(image_bytes)
        ).decode("ascii")

        # ------------------------------------------
        # Determine MIME type
        # ------------------------------------------

        mime_type = (
            response.headers.get(
                "content-type"
            )
            or "image/png"
        )

        # Remove charset if present
        mime_type = mime_type.split(
            ";",
            1
        )[0].strip()

        return {

            "provider":
                self.name,

            "model":
                self.model,

            "mime_type":
                mime_type,

            "aspect_ratio":
                aspect_ratio,

            "image_size":
                f"{width}x{height}",

            "data":
                image_data
        }

    def _json_dumps(self, data):

        import json

        return json.dumps(
            data,
            ensure_ascii=False
        )
