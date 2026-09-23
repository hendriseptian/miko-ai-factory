import base64
import json
from urllib.parse import quote

from workers import fetch

from .base import ImageProvider


class HuggingFaceImageProvider(ImageProvider):
    """
    Hugging Face Inference Providers image provider.

    Design goals:
    - No huggingface_hub dependency (Cloudflare Python Worker compatible).
    - Uses the Hugging Face model ID as the source of truth.
    - Resolves the current provider-specific model ID from the
      Hugging Face Hub API instead of hard-coding it.
    - Supports Fal AI through Hugging Face routing.
    - Accepts both raw image responses and JSON image-URL responses.
    """

    name = "huggingface"

    HF_HUB_BASE_URL = "https://huggingface.co/api"
    HF_ROUTER_BASE_URL = "https://router.huggingface.co"

    DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell"
    DEFAULT_PROVIDER = "fal-ai"

    def __init__(self, env):
        self.env = env

        self.api_key = getattr(
            env,
            "HUGGINGFACE_API_KEY",
            None,
        )

        self.model = getattr(
            env,
            "HUGGINGFACE_IMAGE_MODEL",
            self.DEFAULT_MODEL,
        )

        self.provider = getattr(
            env,
            "HUGGINGFACE_IMAGE_PROVIDER",
            self.DEFAULT_PROVIDER,
        )

    def _get_image_size(self, aspect_ratio):
        if aspect_ratio == "16:9":
            return 1344, 768

        if aspect_ratio == "1:1":
            return 1024, 1024

        # Default for Miko Shorts: vertical 9:16.
        return 768, 1344

    async def _resolve_provider_mapping(self):
        """
        Ask Hugging Face which provider-specific model ID is currently
        active for the selected model/provider.

        This avoids assuming that a provider model ID will remain
        permanently identical to today's value.
        """

        encoded_model = quote(
            self.model,
            safe="/",
        )

        url = (
            f"{self.HF_HUB_BASE_URL}/models/"
            f"{encoded_model}"
            "?expand[]=inferenceProviderMapping"
        )

        response = await fetch(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
            },
        )

        if not response.ok:
            error_text = await response.text()

            raise RuntimeError(
                "Hugging Face model mapping error "
                f"{response.status}: {error_text}"
            )

        try:
            data = await response.json()
        except Exception:
            raw_text = await response.text()

            raise RuntimeError(
                "Hugging Face returned an invalid model "
                f"mapping response: {raw_text}"
            )

        mapping = data.get("inferenceProviderMapping")

        if not isinstance(mapping, dict):
            raise RuntimeError(
                "Hugging Face model response does not contain "
                "inferenceProviderMapping."
            )

        provider_data = mapping.get(self.provider)

        if not isinstance(provider_data, dict):
            available = ", ".join(
                sorted(str(key) for key in mapping.keys())
            )

            raise RuntimeError(
                f"Provider '{self.provider}' is not available "
                f"for model '{self.model}'. "
                f"Available providers: {available or 'none'}"
            )

        status = provider_data.get("status")

        if status and status != "live":
            raise RuntimeError(
                f"Provider '{self.provider}' for model "
                f"'{self.model}' is not live "
                f"(status: {status})."
            )

        provider_model = provider_data.get("providerId")

        if not provider_model:
            raise RuntimeError(
                f"Hugging Face did not return a provider model ID "
                f"for provider '{self.provider}'."
            )

        return str(provider_model)

    def _build_payload(
        self,
        prompt,
        width,
        height,
    ):
        """
        Build the request body expected by the selected provider.

        Fal AI uses:
            prompt
            image_size

        The HF native provider uses the generic:
            inputs
            parameters
        """

        if self.provider == "fal-ai":
            return {
                "prompt": str(prompt),
                "image_size": {
                    "width": width,
                    "height": height,
                },
                "num_inference_steps": 4,
            }

        return {
            "inputs": str(prompt),
            "parameters": {
                "width": width,
                "height": height,
                "num_inference_steps": 4,
            },
        }

    async def _download_image_url(self, image_url):
        image_response = await fetch(
            image_url,
            method="GET",
            headers={
                "Accept": "image/*",
            },
        )

        if not image_response.ok:
            error_text = await image_response.text()

            raise RuntimeError(
                "Failed to download generated image "
                f"{image_response.status}: {error_text}"
            )

        image_buffer = await image_response.arrayBuffer()

        if not image_buffer:
            raise RuntimeError(
                "Generated image is empty."
            )

        mime_type = (
            image_response.headers.get("content-type")
            or "image/png"
        )

        mime_type = mime_type.split(
            ";",
            1,
        )[0].strip()

        image_data = base64.b64encode(
            bytes(image_buffer)
        ).decode("ascii")

        return image_data, mime_type

    async def _parse_response(
        self,
        response,
    ):
        """
        Handle both response styles:
        1. Raw image bytes.
        2. JSON containing an image URL, as used by Fal.
        """

        content_type = (
            response.headers.get("content-type")
            or ""
        ).lower()

        if content_type.startswith("image/"):
            image_buffer = await response.arrayBuffer()

            if not image_buffer:
                raise RuntimeError(
                    "Generated image response is empty."
                )

            mime_type = content_type.split(
                ";",
                1,
            )[0].strip()

            image_data = base64.b64encode(
                bytes(image_buffer)
            ).decode("ascii")

            return image_data, mime_type

        try:
            result = await response.json()
        except Exception:
            raw_text = await response.text()

            raise RuntimeError(
                "Hugging Face provider returned an "
                f"unexpected response: {raw_text}"
            )

        if not isinstance(result, dict):
            raise RuntimeError(
                "Hugging Face provider returned an "
                "unexpected JSON response."
            )

        images = result.get("images")

        if isinstance(images, list) and images:
            first_image = images[0]

            if isinstance(first_image, dict):
                image_url = first_image.get("url")

                if image_url:
                    return await self._download_image_url(
                        image_url
                    )

        # Some provider responses may return a single image URL.
        image_url = result.get("image_url")

        if image_url:
            return await self._download_image_url(
                image_url
            )

        # Preserve the actual provider response for debugging.
        raise RuntimeError(
            "Hugging Face provider returned JSON but "
            "no generated image was found. "
            f"Response: {json.dumps(result, ensure_ascii=False)}"
        )

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

        provider_model = (
            await self._resolve_provider_mapping()
        )

        # Hugging Face routes provider calls using:
        # /{provider}/{provider-specific-model-id}
        #
        # The provider-specific model ID is resolved dynamically
        # from the Hub API above.
        url = (
            f"{self.HF_ROUTER_BASE_URL}/"
            f"{self.provider}/"
            f"{provider_model}"
        )

        payload = self._build_payload(
            prompt=prompt,
            width=width,
            height=height,
        )

        response = await fetch(
            url,
            method="POST",
            headers={
                "Authorization": (
                    f"Bearer {self.api_key}"
                ),
                "Content-Type": "application/json",
                "Accept": "image/*, application/json",
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
                f"{response.status}: {error_text}"
            )

        image_data, mime_type = (
            await self._parse_response(response)
        )

        return {
            "provider": self.name,
            "provider_backend": self.provider,
            "model": self.model,
            "provider_model": provider_model,
            "mime_type": mime_type,
            "aspect_ratio": aspect_ratio,
            "image_size": f"{width}x{height}",
            "data": image_data,
        }
