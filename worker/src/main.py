import json
from urllib.parse import urlparse

from workers import WorkerEntrypoint, Response

from engine.story_engine import StoryEngine
from engine.scene_engine import SceneEngine
from providers.gemini import GeminiProvider
from providers.image.gemini_image import GeminiImageProvider
from providers.image.huggingface_image import HuggingFaceImageProvider


class Default(WorkerEntrypoint):

    CORS_HEADERS = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Max-Age": "86400",
    }

    VERSION = "0.4.0"

    def json_response(self, data, status=200):
        return Response.json(
            data,
            status=status,
            headers=self.CORS_HEADERS
        )

    async def load_json_asset(self, path):
        url = f"https://assets.local/{path}"
        response = await self.env.ASSETS.fetch(url)

        if not response.ok:
            raise RuntimeError(
                f"Failed to load asset: {path}"
            )

        return await response.json()

    async def generate_story(self, data):
        project_id = data.get(
            "project_id",
            "MIKO-0001"
        )

        idea = data.get("idea")

        language = data.get(
            "language",
            "id-ID"
        )

        duration = data.get(
            "duration",
            45
        )

        if not idea:
            raise ValueError(
                "Field 'idea' is required."
            )

        bible = await self.load_json_asset(
            "MIKO_MASTER_BIBLE_V1.json"
        )

        story_rules = await self.load_json_asset(
            "MIKO_STORY_RULES_V1.json"
        )

        provider = GeminiProvider(self.env)

        engine = StoryEngine(
            provider=provider,
            bible=bible,
            story_rules=story_rules
        )

        story = await engine.generate(
            idea=idea,
            project_id=project_id,
            language=language,
            duration=duration
        )

        return story

    async def process_scenes(self, story):
        if not isinstance(story, dict):
            raise ValueError(
                "Field 'story' must be a JSON object."
            )

        engine = SceneEngine(story)

        return engine.process()

    def get_image_provider(self, provider_name):
        if provider_name == "gemini":
            return GeminiImageProvider(self.env)

        if provider_name == "huggingface":
            return HuggingFaceImageProvider(self.env)

        raise ValueError(
            f"Unsupported image provider: {provider_name}"
        )

    async def generate_image(self, data):
        project_id = data.get(
            "project_id",
            "MIKO-0001"
        )

        scene_id = data.get(
            "scene_id",
            "SCENE-01"
        )

        prompt = data.get("prompt")

        aspect_ratio = data.get(
            "aspect_ratio",
            "9:16"
        )

        reference_images = data.get(
            "reference_images",
            []
        )

        if not prompt:
            raise ValueError(
                "Field 'prompt' is required."
            )

        provider_name = data.get(
            "provider",
            "huggingface"
        )

        provider = self.get_image_provider(
            provider_name
        )

        result = await provider.generate(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            reference_images=reference_images
        )

        return {
            "project_id": project_id,
            "scene_id": scene_id,
            "status": "IMAGE_GENERATED",
            "provider": result["provider"],
            "model": result["model"],
            "mime_type": result["mime_type"],
            "aspect_ratio": result["aspect_ratio"],
            "image_size": result["image_size"],
            "image_data": result["data"]
        }

    async def generate_scene_image(self, data):
        """
        Generate one image directly from a processed Scene Engine scene.

        Input:
        {
          "story": { ... },
          "scene_id": "SCENE-01",
          "provider": "huggingface"
        }

        The endpoint processes the story through SceneEngine,
        selects exactly one scene, and sends that scene's
        image_prompt_v1 to the existing Image Engine.

        Only one image is generated per request so the response
        remains manageable and each scene can be QC'd independently.
        """

        story = data.get("story")

        if not isinstance(story, dict):
            raise ValueError(
                "Field 'story' must be a JSON object."
            )

        requested_scene_id = data.get(
            "scene_id",
            "SCENE-01"
        )

        provider_name = data.get(
            "provider",
            "huggingface"
        )

        aspect_ratio = data.get(
            "aspect_ratio",
            "9:16"
        )

        scene_data = await self.process_scenes(
            story
        )

        scenes = scene_data.get(
            "scenes",
            []
        )

        selected_scene = None

        for scene in scenes:
            if scene.get("scene_id") == requested_scene_id:
                selected_scene = scene
                break

        if selected_scene is None:
            available_scene_ids = [
                scene.get("scene_id")
                for scene in scenes
                if scene.get("scene_id")
            ]

            raise ValueError(
                f"Scene '{requested_scene_id}' was not found. "
                f"Available scenes: {available_scene_ids}"
            )

        image_prompt = selected_scene.get(
            "image_prompt_v1"
        )

        if not image_prompt:
            raise ValueError(
                f"Scene '{requested_scene_id}' does not "
                "contain image_prompt_v1."
            )

        image_result = await self.generate_image({
            "project_id": scene_data.get(
                "project_id",
                story.get("project_id", "MIKO-0001")
            ),
            "scene_id": requested_scene_id,
            "prompt": image_prompt,
            "aspect_ratio": aspect_ratio,
            "provider": provider_name,
            "reference_images": selected_scene.get(
                "reference_assets",
                []
            )
        })

        return {
            "project_id": scene_data.get(
                "project_id"
            ),
            "title": scene_data.get(
                "title"
            ),
            "scene_id": requested_scene_id,
            "scene_sequence": selected_scene.get(
                "sequence"
            ),
            "scene_duration": selected_scene.get(
                "duration"
            ),
            "scene": selected_scene,
            "image": image_result
        }

    async def fetch(self, request):
        url = urlparse(request.url)
        path = url.path
        method = request.method

        if method == "OPTIONS":
            return Response(
                "",
                status=204,
                headers=self.CORS_HEADERS
            )

        if path == "/health":
            return self.json_response({
                "status": "ok",
                "service": "miko-ai-factory",
                "version": self.VERSION
            })

        if path == "/":
            return self.json_response({
                "name": "Miko AI Factory",
                "status": "foundation",
                "version": self.VERSION,
                "endpoints": {
                    "health": "/health",
                    "story": "POST /api/story/generate",
                    "scene": "POST /api/scene/process",
                    "image": "POST /api/image/generate",
                    "scene_image": "POST /api/image/scene"
                }
            })

        if path == "/api/story/generate":
            if method != "POST":
                return self.json_response(
                    {
                        "success": False,
                        "error": "method_not_allowed",
                        "message": "Use POST."
                    },
                    status=405
                )

            try:
                data = await request.json()

                story = await self.generate_story(
                    data
                )

                return self.json_response({
                    "success": True,
                    "project_id": story.get(
                        "project_id"
                    ),
                    "story": story
                })

            except ValueError as error:
                return self.json_response(
                    {
                        "success": False,
                        "error": "validation_error",
                        "message": str(error)
                    },
                    status=400
                )

            except Exception as error:
                return self.json_response(
                    {
                        "success": False,
                        "error": "story_generation_failed",
                        "message": str(error)
                    },
                    status=500
                )

        if path == "/api/scene/process":
            if method != "POST":
                return self.json_response(
                    {
                        "success": False,
                        "error": "method_not_allowed",
                        "message": "Use POST."
                    },
                    status=405
                )

            try:
                data = await request.json()

                story = data.get("story")

                if not story:
                    raise ValueError(
                        "Field 'story' is required."
                    )

                scenes = await self.process_scenes(
                    story
                )

                return self.json_response({
                    "success": True,
                    "project_id": scenes.get(
                        "project_id"
                    ),
                    "scene_data": scenes
                })

            except ValueError as error:
                return self.json_response(
                    {
                        "success": False,
                        "error": "validation_error",
                        "message": str(error)
                    },
                    status=400
                )

            except Exception as error:
                return self.json_response(
                    {
                        "success": False,
                        "error": "scene_processing_failed",
                        "message": str(error)
                    },
                    status=500
                )

        if path == "/api/image/generate":
            if method != "POST":
                return self.json_response(
                    {
                        "success": False,
                        "error": "method_not_allowed",
                        "message": "Use POST."
                    },
                    status=405
                )

            try:
                data = await request.json()

                image = await self.generate_image(
                    data
                )

                return self.json_response({
                    "success": True,
                    "image": image
                })

            except ValueError as error:
                return self.json_response(
                    {
                        "success": False,
                        "error": "validation_error",
                        "message": str(error)
                    },
                    status=400
                )

            except Exception as error:
                return self.json_response(
                    {
                        "success": False,
                        "error": "image_generation_failed",
                        "message": str(error)
                    },
                    status=500
                )

        if path == "/api/image/scene":
            if method != "POST":
                return self.json_response(
                    {
                        "success": False,
                        "error": "method_not_allowed",
                        "message": "Use POST."
                    },
                    status=405
                )

            try:
                data = await request.json()

                result = await self.generate_scene_image(
                    data
                )

                # The response intentionally contains one image only.
                return self.json_response({
                    "success": True,
                    "project_id": result.get(
                        "project_id"
                    ),
                    "scene_id": result.get(
                        "scene_id"
                    ),
                    "scene": result.get(
                        "scene"
                    ),
                    "image": result.get(
                        "image"
                    )
                })

            except ValueError as error:
                return self.json_response(
                    {
                        "success": False,
                        "error": "validation_error",
                        "message": str(error)
                    },
                    status=400
                )

            except Exception as error:
                return self.json_response(
                    {
                        "success": False,
                        "error": "scene_image_generation_failed",
                        "message": str(error)
                    },
                    status=500
                )

        return self.json_response(
            {
                "success": False,
                "error": "not_found",
                "path": path
            },
            status=404
        )
