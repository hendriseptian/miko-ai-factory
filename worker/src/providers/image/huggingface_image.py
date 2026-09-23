import base64
import json

from workers import fetch

from .base import ImageProvider


class HuggingFaceImageProvider(ImageProvider):
    """
    Hugging Face Inference Providers image provider.

    Uses a Hugging Face token with Fal AI routing and
    FLUX.1-schnell. Does not import huggingface_hub,
    keeping the Cloudflare Python Worker lightweight.
    """

    name = "huggingface"

    def __init__(self, env):
        self.env = env

        self.api_key = getattr(
            env,
            "HUGGINGFACE_API_KEY",
            None,
        )

        # Hugging Face model ID.
        self.model = getattr(
            env,
            "HUGGINGFACE_IMAGE_MODEL",
            "black-forest-labs/FLUX.1-schnell",
        )

        # Hugging Face Inference Provider.
        self.provider = getattr(
            env,
            "HUGGINGFACE_IMAGE_PROVIDER",
            "fal-ai",
        )

        # Provider-specific Fal model ID.
        self.provider_model = getattr(
            env,
            "HUGGINGFACE_PROVIDER_MODEL",
            "fal-ai/flux/schnell",
        )

        self.base_url = "https://router.huggingface.co"

    def _get_image_size(self, aspect_ratio):
        if aspect_ratio == "16:9":
            return 1344, 768

        if aspect_ratio == "1:1":
            return 1024, 1024

        # Default: vertical 9:16
        return 768, 1344

    async def generate(
        self,
        prompt,
        aspect_ratio="9:16",
        reference_images=None,
    ):
        if not self.api_key:
            raise RuntimeError(
                "HUGGINGFACE_API_KEY is not configured."
            )

        if not prompt or not str(prompt).strip():
            raise ValueError(
                "Image prompt is required."
            )

        width, height = self._get_image_size(
            aspect_ratio
        )

        # Hugging Face provider routing:
        # /fal-ai/{provider_model}
        #
        # Final URL:
        # https://router.huggingface.co/fal-ai/
        # fal-ai/flux/schnell
        url = (
            f"{self.base_url}"
            f"/fal-ai/"
            f"{self.provider_model}"
        )

        # Fal text-to-image payload.
        payload = {
            "prompt": str(prompt),
            "image_size": {
                "width": width,
                "height": height,
            },
            "num_inference_steps": 4,
        }

        response = await fetch(
            url,
            method="POST",
            headers={
                "Authorization": (
                    f"Bearer {self.api_key}"
                ),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            body=json.dumps(
                payload,
                ensure_ascii=False,
            ),
        )

        if not response.ok:
            error_text = await response.text()

            raise RuntimeError(
                "Hugging Face Image API error "
                f"{response.status}: "
                f"{error_text}"
            )

        try:
            result = await response.json()
        except Exception:
            raw_text = await response.text()

            raise RuntimeError(
                "Hugging Face/Fal returned "
                "an invalid JSON response: "
                f"{raw_text}"
            )

        if not isinstance(result, dict):
            raise RuntimeError(
                "Hugging Face/Fal returned an "
                "unexpected response object."
            )

        images = result.get("images")

        if not isinstance(images, list) or not images:
            raise RuntimeError(
                "Hugging Face/Fal response does not "
                "contain an images array. "
                f"Response: {json.dumps(result)}"
            )

        first_image = images[0]

        if not isinstance(first_image, dict):
            raise RuntimeError(
                "Hugging Face/Fal returned an invalid "
                "image object."
            )

        image_url = first_image.get("url")

        if not image_url:
            raise RuntimeError(
                "Hugging Face/Fal response does not "
                "contain an image URL. "
                f"Response: {json.dumps(result)}"
            )

        image_response = await fetch(
            image_url,
            method="GET",
            headers={
                "Accept": "image/*",
            },
        )

        if not image_response.ok:
            image_error = await image_response.text()

            raise RuntimeError(
                "Failed to download generated image "
                "from provider: "
                f"{image_response.status}: "
                f"{image_error}"
            )

        image_buffer = (
            await image_response.array_buffer()
        )

        if not image_buffer:
            raise RuntimeError(
                "Generated image is empty."
            )

        image_data = base64.b64encode(
            bytes(image_buffer)
        ).decode("ascii")

        mime_type = (
            image_response.headers.get(
                "content-type"
            )
            or "image/png"
        )

        mime_type = mime_type.split(
            ";",
            1,
        )[0].strip()

        return {
            "provider": self.name,
            "provider_backend": self.provider,
            "model": self.model,
            "provider_model": self.provider_model,
            "mime_type": mime_type,
            "aspect_ratio": aspect_ratio,
            "image_size": f"{width}x{height}",
            "data": image_data,
        }
