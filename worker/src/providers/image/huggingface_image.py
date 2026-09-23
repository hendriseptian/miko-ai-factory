import base64
import json

from workers import fetch

from .base import ImageProvider


class HuggingFaceImageProvider(ImageProvider):
    """
    Hugging Face Inference Providers
    - Hugging Face token authentication
    - Fal AI provider
    - FLUX.1-schnell image generation

    Cloudflare Python Workers compatible.
    Does not use huggingface_hub SDK.
    """

    name = "huggingface"

    def __init__(self, env):
        self.env = env

        # ---------------------------------
        # HUGGING FACE API KEY
        # ---------------------------------

        self.api_key = getattr(
            env,
            "HUGGINGFACE_API_KEY",
            None
        )

        # ---------------------------------
        # HUGGING FACE MODEL ID
        # ---------------------------------

        self.model = getattr(
            env,
            "HUGGINGFACE_IMAGE_MODEL",
            "black-forest-labs/FLUX.1-schnell"
        )

        # ---------------------------------
        # PROVIDER
        # ---------------------------------

        self.provider = getattr(
            env,
            "HUGGINGFACE_IMAGE_PROVIDER",
            "fal-ai"
        )

        # ---------------------------------
        # FAL PROVIDER MODEL ID
        #
        # This is NOT the same as the
        # Hugging Face model ID.
        # ---------------------------------

        self.provider_model = getattr(
            env,
            "HUGGINGFACE_PROVIDER_MODEL",
            "fal-ai/flux/schnell"
        )

        # ---------------------------------
        # HUGGING FACE ROUTER
        # ---------------------------------

        self.base_url = (
            "https://router.huggingface.co"
        )

    async def generate(
        self,
        prompt,
        aspect_ratio="9:16",
        reference_images=None
    ):
        # =================================
        # VALIDATION
        # =================================

        if not self.api_key:
            raise RuntimeError(
                "HUGGINGFACE_API_KEY is not configured."
            )

        if not prompt:
            raise ValueError(
                "Image prompt is required."
            )

        # =================================
        # IMAGE SIZE
        # =================================

        width = 768
        height = 1344

        if aspect_ratio == "16:9":
            width = 1344
            height = 768

        elif aspect_ratio == "1:1":
            width = 1024
            height = 1024

        # =================================
        # HUGGING FACE → FAL ROUTER
        # =================================
        #
        # IMPORTANT:
        #
        # Hugging Face model:
        # black-forest-labs/FLUX.1-schnell
        #
        # Provider model:
        # fal-ai/flux/schnell
        #
        # Router path:
        # /fal-ai/fal-ai/flux/schnell
        #
        # This follows the provider routing
        # structure used by Hugging Face.
        #

        url = (
            f"{self.base_url}"
            f"/fal-ai/"
            f"{self.provider_model}"
        )

        # =================================
        # FAL PAYLOAD
        # =================================
        #
        # Fal text-to-image expects:
        #
        # prompt
        # image_size
        #
        # NOT:
        # inputs
        #
        # The Hugging Face provider adapter
        # converts width + height into
        # image_size for Fal.
        #

        payload = {
            "prompt": prompt,
            "image_size": {
                "width": width,
                "height": height
            },
            "num_inference_steps": 4
        }

        # =================================
        # REQUEST
        # =================================

        response = await fetch(
            url,
            method="POST",
            headers={
                "Authorization": (
                    f"Bearer {self.api_key}"
                ),
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body=json.dumps(
                payload,
                ensure_ascii=False
            )
        )

        # =================================
        # RESPONSE ERROR
        # =================================

        if not response.ok:
            error_text = await response.text()

            raise RuntimeError(
                "Hugging Face Image API error "
                f"{response.status}: "
                f"{error_text}"
            )

        # =================================
        # PARSE FAL RESPONSE
        # =================================

        try:
            result = await response.json()

        except Exception:
            response_text = await response.text()

            raise RuntimeError(
                "Hugging Face/Fal returned "
                "an invalid JSON response: "
                f"{response_text}"
            )

        # =================================
        # FIND IMAGE URL
        # =================================

        try:
            image_url = (
                result["images"][0]["url"]
            )

        except (
            KeyError,
            IndexError,
            TypeError
        ):
            raise RuntimeError(
                "Hugging Face/Fal response "
                "does not contain an image URL. "
                f"Response: {json.dumps(result)}"
            )

        if not image_url:
            raise RuntimeError(
                "Hugging Face/Fal returned "
                "an empty image URL."
            )

        # =================================
        # DOWNLOAD GENERATED IMAGE
        # =================================

        image_response = await fetch(
            image_url,
            method="GET",
            headers={
                "Accept": "image/*"
            }
        )

        if not image_response.ok:
            image_error = (
                await image_response.text()
            )

            raise RuntimeError(
                "Failed to download generated "
                "image from Fal: "
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

        # =================================
        # BASE64
        # =================================

        image_data = base64.b64encode(
            bytes(image_buffer)
        ).decode("ascii")

        # =================================
        # MIME TYPE
        # =================================

        mime_type = (
            image_response.headers.get(
                "content-type"
            )
            or "image/png"
        )

        mime_type = mime_type.split(
            ";",
            1
        )[0].strip()

        # =================================
        # RESULT
        # =================================

        return {
            "provider": self.name,
            "provider_backend": self.provider,
            "model": self.model,
            "provider_model": self.provider_model,
            "mime_type": mime_type,
            "aspect_ratio": aspect_ratio,
            "image_size": (
                f"{width}x{height}"
            ),
            "data": image_data
        }
