import base64
import json
from urllib.parse import quote

from workers import fetch

from .base import ImageProvider


class HuggingFaceImageProvider(ImageProvider):
    """
    Hugging Face Inference Providers image provider V4.

    Two modes are supported:

    1. Text-to-image:
       Uses the existing FLUX.1-schnell path.

    2. Reference-image mode:
       When reference_images are supplied, uses an image-to-image
       model so a canonical Miko reference can guide character identity.

    Cloudflare Python Worker compatible:
    - No huggingface_hub dependency.
    - Uses workers.fetch directly.
    """

    name = "huggingface"

    HF_HUB_BASE_URL = "https://huggingface.co/api"
    HF_ROUTER_BASE_URL = "https://router.huggingface.co"

    DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell"
    DEFAULT_PROVIDER = "fal-ai"

    # Hugging Face currently documents Qwen Image Edit through
    # Inference Providers/Fal for image-to-image use.
    DEFAULT_REFERENCE_MODEL = "Qwen/Qwen-Image-Edit"

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

        self.reference_model = getattr(
            env,
            "HUGGINGFACE_REFERENCE_MODEL",
            self.DEFAULT_REFERENCE_MODEL,
        )

    def _get_image_size(self, aspect_ratio):
        if aspect_ratio == "16:9":
            return 1344, 768

        if aspect_ratio == "1:1":
            return 1024, 1024

        return 768, 1344

    async def _resolve_provider_mapping(self, model):
        encoded_model = quote(
            model,
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
                f"for model '{model}'. "
                f"Available providers: {available or 'none'}"
            )

        status = provider_data.get("status")

        if status and status != "live":
            raise RuntimeError(
                f"Provider '{self.provider}' for model "
                f"'{model}' is not live "
                f"(status: {status})."
            )

        provider_model = provider_data.get("providerId")

        if not provider_model:
            raise RuntimeError(
                f"Hugging Face did not return a provider model ID "
                f"for provider '{self.provider}'."
            )

        return str(provider_model)

    def _build_text_payload(
        self,
        prompt,
        width,
        height,
    ):
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

    async def _to_data_url(self, reference):
        """
        Convert a reference item into a data:image/*;base64,... URL.

        Accepted forms:
        - https://... image URL
        - data:image/...;base64,...
        - raw base64 string
        - {"url": "..."}
        - {"data": "...", "mime_type": "image/png"}
        """

        if isinstance(reference, dict):
            if reference.get("url"):
                reference = reference["url"]
            elif reference.get("data"):
                mime_type = (
                    reference.get("mime_type")
                    or "image/png"
                )
                data = str(reference["data"])

                if data.startswith("data:"):
                    return data

                return (
                    f"data:{mime_type};base64,"
                    f"{data}"
                )

        if not isinstance(reference, str):
            raise ValueError(
                "Reference image must be a URL, data URL, "
                "base64 string, or object containing url/data."
            )

        value = reference.strip()

        if not value:
            raise ValueError(
                "Reference image cannot be empty."
            )

        if value.startswith("data:image/"):
            return value

        if value.startswith("http://") or value.startswith(
            "https://"
        ):
            response = await fetch(
                value,
                method="GET",
                headers={
                    "Accept": "image/*",
                },
            )

            if not response.ok:
                error_text = await response.text()

                raise RuntimeError(
                    "Failed to download reference image "
                    f"{response.status}: {error_text}"
                )

            image_bytes = await self._read_response_bytes(
                response
            )

            if not image_bytes:
                raise RuntimeError(
                    "Reference image is empty."
                )

            mime_type = (
                response.headers.get(
                    "content-type"
                )
                or "image/png"
            )

            mime_type = mime_type.split(
                ";",
                1,
            )[0].strip()

            return (
                f"data:{mime_type};base64,"
                f"{base64.b64encode(image_bytes).decode('ascii')}"
            )

        # Raw base64.
        return (
            "data:image/png;base64,"
            + value
        )

    async def _prepare_reference_images(
        self,
        reference_images,
    ):
        if reference_images is None:
            return []

        if not isinstance(reference_images, list):
            reference_images = [reference_images]

        prepared = []

        for reference in reference_images:
            if reference is None:
                continue

            prepared.append(
                await self._to_data_url(reference)
            )

        return prepared

    def _build_reference_payload(
        self,
        prompt,
        reference_images,
        width,
        height,
    ):
        """
        Qwen Image Edit (Fal) uses image_url (singular) for its
        current endpoint. We intentionally use one canonical Miko
        reference image for identity preservation.

        The endpoint accepts a public URL or a Base64 data URI.
        """

        if self.provider == "fal-ai":
            first_image = reference_images[0]

            return {
                "image_url": first_image,
                "prompt": str(prompt),
                "image_size": {
                    "width": width,
                    "height": height,
                },
                "num_inference_steps": 30,
                "guidance_scale": 4.0,
                "num_images": 1,
                "enable_safety_checker": True,
                "output_format": "png",
                "negative_prompt": (
                    "human person, child, human face, "
                    "different animal, different character, "
                    "character redesign, duplicate character, "
                    "extra limbs, distorted anatomy, text, logo, watermark"
                ),
            }

        # Generic fallback. The HF task specification accepts the
        # input image as base64 and prompt/parameters.
        first_image = reference_images[0]

        return {
            "inputs": first_image,
            "parameters": {
                "prompt": str(prompt),
                "num_inference_steps": 30,
            },
        }

    async def _read_response_bytes(self, response):
        body = response.body

        if body is None:
            raise RuntimeError(
                "Response body is empty."
            )

        reader = body.getReader()
        chunks = []

        try:
            while True:
                result = await reader.read()

                if result.done:
                    break

                value = result.value

                if value is not None:
                    chunks.append(
                        value.to_bytes()
                    )
        finally:
            try:
                reader.releaseLock()
            except Exception:
                pass

        if not chunks:
            raise RuntimeError(
                "Response body is empty."
            )

        return b"".join(chunks)

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

        image_buffer = await self._read_response_bytes(
            image_response
        )

        if not image_buffer:
            raise RuntimeError(
                "Generated image is empty."
            )

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

        return (
            base64.b64encode(
                image_buffer
            ).decode("ascii"),
            mime_type,
        )

    async def _parse_response(self, response):
        content_type = (
            response.headers.get(
                "content-type"
            )
            or ""
        ).lower()

        if content_type.startswith("image/"):
            image_buffer = await self._read_response_bytes(
                response
            )

            if not image_buffer:
                raise RuntimeError(
                    "Generated image response is empty."
                )

            mime_type = content_type.split(
                ";",
                1,
            )[0].strip()

            return (
                base64.b64encode(
                    image_buffer
                ).decode("ascii"),
                mime_type,
            )

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

        image_url = result.get("image_url")

        if image_url:
            return await self._download_image_url(
                image_url
            )

        # Some APIs may return a data URL directly.
        output = result.get("image")

        if isinstance(output, str) and output.startswith(
            "data:image/"
        ):
            header, encoded = output.split(
                ",",
                1,
            )

            mime_type = (
                header.split(";", 1)[0]
                .replace("data:", "")
            )

            return encoded, mime_type

        raise RuntimeError(
            "Hugging Face provider returned JSON but "
            "no generated image was found. "
            f"Response: {json.dumps(result, ensure_ascii=False)}"
        )

    async def _generate_text_to_image(
        self,
        prompt,
        aspect_ratio,
    ):
        width, height = self._get_image_size(
            aspect_ratio
        )

        provider_model = (
            await self._resolve_provider_mapping(
                self.model
            )
        )

        url = (
            f"{self.HF_ROUTER_BASE_URL}/"
            f"{self.provider}/"
            f"{provider_model}"
        )

        payload = self._build_text_payload(
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
            "mode": "text-to-image",
            "model": self.model,
            "provider_model": provider_model,
            "mime_type": mime_type,
            "aspect_ratio": aspect_ratio,
            "image_size": f"{width}x{height}",
            "data": image_data,
        }

    async def _generate_with_reference(
        self,
        prompt,
        aspect_ratio,
        reference_images,
    ):
        prepared_references = (
            await self._prepare_reference_images(
                reference_images
            )
        )

        if not prepared_references:
            raise ValueError(
                "Reference image mode was requested, "
                "but no usable reference image was supplied."
            )

        provider_model = (
            await self._resolve_provider_mapping(
                self.reference_model
            )
        )

        url = (
            f"{self.HF_ROUTER_BASE_URL}/"
            f"{self.provider}/"
            f"{provider_model}"
        )

        width, height = self._get_image_size(
            aspect_ratio
        )

        payload = self._build_reference_payload(
            prompt=prompt,
            reference_images=prepared_references,
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
                "Hugging Face Reference Image API error "
                f"{response.status}: {error_text}"
            )

        image_data, mime_type = (
            await self._parse_response(response)
        )

        width, height = self._get_image_size(
            aspect_ratio
        )

        return {
            "provider": self.name,
            "provider_backend": self.provider,
            "mode": "reference-image",
            "model": self.reference_model,
            "provider_model": provider_model,
            "mime_type": mime_type,
            "aspect_ratio": aspect_ratio,
            "image_size": f"{width}x{height}",
            "reference_count": len(prepared_references),
            "data": image_data,
        }

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

        if reference_images:
            return await self._generate_with_reference(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                reference_images=reference_images,
            )

        return await self._generate_text_to_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
        )
