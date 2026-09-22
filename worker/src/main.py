import json
from urllib.parse import urlparse

from workers import WorkerEntrypoint, Response

from engine.story_engine import StoryEngine
from providers.gemini import GeminiProvider


class Default(WorkerEntrypoint):

    async def load_json_asset(self, path):
        """
        Load a JSON file from the Worker ASSETS binding.
        """

        url = f"https://assets.local/{path}"

        response = await self.env.ASSETS.fetch(url)

        if not response.ok:
            raise RuntimeError(
                f"Failed to load asset: {path}"
            )

        return await response.json()

    async def generate_story(self, data):
        """
        Generate a Miko story using StoryEngine + Gemini.
        """

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

        # Load Miko rules from GitHub assets
        bible = await self.load_json_asset(
            "MIKO_MASTER_BIBLE_V1.json"
        )

        story_rules = await self.load_json_asset(
            "MIKO_STORY_RULES_V1.json"
        )

        # Create Gemini provider
        provider = GeminiProvider(
            self.env
        )

        # Create Story Engine
        engine = StoryEngine(
            provider=provider,
            bible=bible,
            story_rules=story_rules
        )

        # Generate story
        story = await engine.generate(
            idea=idea,
            project_id=project_id,
            language=language,
            duration=duration
        )

        return story

    async def fetch(self, request):

        url = urlparse(request.url)

        path = url.path
        method = request.method

        # ========================================
        # HEALTH CHECK
        # ========================================

        if path == "/health":

            return Response.json({
                "status": "ok",
                "service": "miko-ai-factory",
                "version": "0.1.0"
            })

        # ========================================
        # ROOT
        # ========================================

        if path == "/":

            return Response.json({
                "name": "Miko AI Factory",
                "status": "foundation",
                "version": "0.1.0",
                "endpoints": {
                    "health": "/health",
                    "story": "POST /api/story/generate"
                }
            })

        # ========================================
        # STORY GENERATION
        # ========================================

        if path == "/api/story/generate":

            if method != "POST":

                return Response.json(
                    {
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

                return Response.json({
                    "success": True,
                    "project_id": story.get(
                        "project_id"
                    ),
                    "story": story
                })

            except ValueError as error:

                return Response.json(
                    {
                        "success": False,
                        "error": "validation_error",
                        "message": str(error)
                    },
                    status=400
                )

            except Exception as error:

                return Response.json(
                    {
                        "success": False,
                        "error": "story_generation_failed",
                        "message": str(error)
                    },
                    status=500
                )

        # ========================================
        # 404
        # ========================================

        return Response.json(
            {
                "success": False,
                "error": "not_found",
                "path": path
            },
            status=404
        )
