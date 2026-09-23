import json
from workers import fetch

class GeminiProvider:
    """
    Gemini API provider for Miko AI Factory.

    This class is responsible only for communicating
    with the Gemini API.

    Story logic belongs to StoryEngine.
    """

    def __init__(self, env):
        self.env = env

        self.api_key = getattr(env, "GEMINI_API_KEY", None)

        self.model = getattr(
            env,
            "GEMINI_MODEL",
            "gemini-3.6-flash"
        )

        self.base_url = (
            "https://generativelanguage.googleapis.com/v1beta/models"
        )

    async def generate_json(self, prompt):
        """
        Send a prompt to Gemini and return parsed JSON.
        """

        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        url = (
            f"{self.base_url}/"
            f"{self.model}:generateContent"
            f"?key={self.api_key}"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "responseMimeType": "application/json"
            }
        }

        response = await fetch(
            url,
            method="POST",
            headers={
                "Content-Type": "application/json"
            },
            body=json.dumps(payload)
        )

        if not response.ok:
            error_text = await response.text()

            raise RuntimeError(
                f"Gemini API error "
                f"{response.status}: "
                f"{error_text}"
            )

        data = await response.json()

        try:
            text = (
                data["candidates"][0]
                ["content"]["parts"][0]
                ["text"]
            )
        except (KeyError, IndexError, TypeError):
            raise RuntimeError(
                "Gemini returned an unexpected response."
            )

        try:
            return json.loads(text)

        except json.JSONDecodeError:
            raise RuntimeError(
                "Gemini returned invalid JSON."
            )
