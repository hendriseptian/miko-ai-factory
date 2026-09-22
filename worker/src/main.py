import json
from urllib.parse import urlparse

from workers import WorkerEntrypoint, Response

from engine.story_engine import StoryEngine
from providers.gemini import GeminiProvider


class Default(WorkerEntrypoint):

    CORS_HEADERS = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Max-Age": "86400",
    }

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
            raise RuntimeError(f"Failed to load asset: {path}")

        return await response.json()

    async def generate_story(self, data):
        project_id = data.get("project_id", "MIKO-0001")
        idea = data.get("idea")
        language = data.get("language", "id-ID")
        duration = data.get("duration", 45)

        if not idea:
            raise ValueError("Field 'idea' is required.")

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

    async def fetch(self, request):

        url = urlparse(request.url)

        path = url.path
        method = request.method

        # =========================
        # CORS PREFLIGHT
        # =========================

        if method == "OPTIONS":
            return Response(
                "",
                status=204,
                headers=self.CORS_HEADERS
            )

        # =========================
        # HEALTH
        # =========================

        if path == "/health":

            return self.json_response({
                "status": "ok",
                "service": "miko-ai-factory",
                "version": "0.1.0"
            })

        # =========================
        # ROOT
        # =========================

        if path == "/":

            return self.json_response({
                "name": "Miko AI Factory",
                "status": "foundation",
                "version": "0.1.0",
                "endpoints": {
                    "health": "/health",
                    "story": "POST /api/story/generate"
                }
            })

        # =========================
        # STORY GENERATION
        # =========================

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

                story = await self.generate_story(data)

                return self.json_response({
                    "success": True,
                    "project_id": story.get("project_id"),
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

        # =========================
        # NOT FOUND
        # =========================

        return self.json_response(
            {
                "success": False,
                "error": "not_found",
                "path": path
            },
            status=404
        )
