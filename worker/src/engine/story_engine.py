import json


class StoryEngine:
    """
    Miko Story Engine V1

    Responsibilities:
    - Receive a story idea
    - Build the Miko-specific story prompt
    - Send the prompt to a configured AI provider
    - Return structured story JSON
    """

    def __init__(self, provider, bible, story_rules):
        self.provider = provider
        self.bible = bible
        self.story_rules = story_rules

    def build_prompt(
        self,
        idea,
        language="id-ID",
        duration=45
    ):
        """
        Build the complete prompt for story generation.
        """

        prompt = f"""
You are Miko Story Engine V1.

Your task is to create one short children's story
for the character Miko.

========================
MIKO MASTER BIBLE
========================

{json.dumps(
    self.bible,
    ensure_ascii=False,
    indent=2
)}

========================
MIKO STORY RULES
========================

{json.dumps(
    self.story_rules,
    ensure_ascii=False,
    indent=2
)}

========================
USER STORY IDEA
========================

{idea}

========================
GENERATION REQUIREMENTS
========================

Language:
{language}

Target duration:
{duration} seconds

Target audience:
Children aged 3-8.

The story MUST:

1. Keep Miko as the protagonist.
2. Follow the Miko Master Bible.
3. Follow the Miko Story Rules.
4. Have one main idea.
5. Have one main event.
6. Have one simple message or value.
7. Have a clear beginning.
8. Have a small understandable problem.
9. Have a simple solution.
10. End positively.
11. Be safe and age-appropriate.
12. Be visually suitable for image-to-video generation.
13. Keep dialogue short and natural.
14. Avoid unnecessary characters.
15. Avoid unnecessary locations.

========================
OUTPUT FORMAT
========================

Return VALID JSON ONLY.

Do not use Markdown.
Do not use ```json.
Do not add explanations outside the JSON.

The JSON must contain:

{{
  "project_id": "",
  "title": "",
  "logline": "",
  "main_value": "",
  "target_age": "3-8",
  "language": "{language}",
  "duration_target": {duration},
  "characters": [],
  "locations": [],
  "scenes": [],
  "status": "DRAFT"
}}

Each scene must contain:

{{
  "scene_id": "SCENE-01",
  "sequence": 1,
  "duration": 5,
  "location": "",
  "characters": [],
  "action": "",
  "dialogue": "",
  "narration": "",
  "image_prompt": "",
  "video_prompt": "",
  "reference_assets": [],
  "image_status": "PENDING",
  "video_status": "PENDING"
}}

IMPORTANT:

The story must be designed for short-form vertical video.

The image_prompt must describe the visual composition
needed to generate the scene image.

The video_prompt must describe movement and camera behavior,
not redesign the character.

The identity of Miko must remain consistent.

Return JSON only.
"""

        return prompt

    async def generate(
        self,
        idea,
        project_id,
        language="id-ID",
        duration=45
    ):
        """
        Generate a complete Miko story.
        """

        prompt = self.build_prompt(
            idea=idea,
            language=language,
            duration=duration
        )

        story = await self.provider.generate_json(prompt)

        if not isinstance(story, dict):
            raise RuntimeError(
                "Story Engine received invalid JSON object."
            )

        story["project_id"] = project_id

        return story
