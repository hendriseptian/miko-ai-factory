import base64
import json

from workers import fetch

from .base import ImageProvider


class GeminiImageProvider(ImageProvider):
    """
    Gemini Image Generation Provider.

    Uses Gemini 3.1 Flash Image.
    """

    name = "gemini"

    def __init__(self, env):
        self.env = env

        self.api_key = getattr(
            env,
            "GEMINI_API_KEY",
            None
        )

        self.model = getattr(
            env,
            "GEMINI_IMAGE_MODEL",
            "gemini-3.1-flash-image"
        )

        self.base_url = (
            "https://generativelanguage.googleapis.com"
            "/v1beta/interactions"
        )

    async def generate(
        self,
        prompt,
        aspect_ratio="9:16",
        reference_images=None
    ):
        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        if not prompt:
            raise ValueError(
                "Image prompt is required."
            )

        # Build Gemini input
        inputs = []

        # Reference images
        if reference_images:
            for image in reference_images:

                if not isinstance(image, dict):
                    continue

                image_data = image.get("data")
                mime_type = image.get(
                    "mime_type",
                    "image/png"
                )

                if not image_data:
                    continue

                # Remove data URL prefix if present
                if image_data.startswith("data:"):
                    image_data = image_data.split(
                        ",",
                        1
                    )[1]

                inputs.append({
                    "type": "image",
                    "mime_type": mime_type,
                    "data": image_data
                })

        # Main prompt
        inputs.append({
            "type": "text",
            "text": prompt
        })

        payload = {
            "model": self.model,
            "input": inputs,
            "response_format": {
                "type": "image",
                "mime_type": "image/jpeg",
                "aspect_ratio": aspect_ratio,
                "image_size": "1K"
            }
        }

        response = await fetch(
            self.base_url,
            method="POST",
            headers={
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json"
            },
            body=json.dumps(payload)
        )

        if not response.ok:
            error_text = await response.text()

            raise RuntimeError(
                f"Gemini Image API error "
                f"{response.status}: "
                f"{error_text}"
            )

        data = await response.json()

        # Find generated image
        image_data = None
        mime_type = "image/jpeg"

        # Convenience property
        output_image = data.get(
            "output_image"
        )

        if isinstance(output_image, dict):
            image_data = output_image.get(
                "data"
            )
            mime_type = output_image.get(
                "mime_type",
                mime_type
            )

        # Fallback: inspect steps
        if not image_data:

            for step in data.get(
                "steps",
                []
            ):

                if step.get("type") != "model_output":
                    continue

                for content in step.get(
                    "content",
                    []
                ):

                    if content.get(
                        "type"
                    ) == "image":

                        image_data = content.get(
                            "data"
                        )

                        mime_type = content.get(
                            "mime_type",
                            mime_type
                        )

                        break

                if image_data:
                    break

        if not image_data:
            raise RuntimeError(
                "Gemini did not return "
                "a generated image."
            )

        return {
            "provider": self.name,
            "model": self.model,
            "mime_type": mime_type,
            "aspect_ratio": aspect_ratio,
            "image_size": "1K",
            "data": image_data
        }
