from workers import WorkerEntrypoint, Response


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = request.url

        if url.endswith("/health"):
            return Response.json({
                "status": "ok",
                "service": "miko-ai-factory",
                "version": "0.1.0"
            })

        if url.endswith("/"):
            return Response.json({
                "name": "Miko AI Factory",
                "status": "foundation",
                "message": "Worker is running.",
                "next": [
                    "story generation",
                    "scene generation",
                    "provider routing",
                    "asset metadata",
                    "QC API"
                ]
            })

        return Response.json({
            "error": "not_found"
        }, status=404)
