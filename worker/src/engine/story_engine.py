import json


class StoryEngine:
    """
    Miko Story Engine V1.1

    Main goals:
    - Preserve the user's original story idea.
    - Keep the main event and main object consistent.
    - Make SCENE-01 introduce the main event.
    - Prevent generic/filler scenes.
    - Produce scenes that are visually actionable for image generation.
    - Keep output compatible with the existing V0.4.0 API.
    """

    VERSION = "1.1"

    def __init__(self, provider, bible, story_rules):
        self.provider = provider
        self.bible = bible
        self.story_rules = story_rules

    def build_prompt(self, idea, language="id-ID", duration=45):
        prompt = f"""
You are Miko Story Engine V1.1.

Your task is to create one short children's story
for the character Miko.

========================
MIKO MASTER BIBLE
========================

{json.dumps(self.bible, ensure_ascii=False, indent=2)}

========================
MIKO STORY RULES
========================

{json.dumps(self.story_rules, ensure_ascii=False, indent=2)}

========================
USER STORY IDEA
========================

{idea}

========================
CORE STORY FIDELITY RULE
========================

The USER STORY IDEA is the primary narrative source of truth.

The generated story MUST preserve the original meaning,
main event, main object, main problem, and intended action
from the user's idea.

Do NOT replace the user's main event with a generic activity.

Do NOT replace the user's main object with another object.

Do NOT turn the story into a generic character portrait,
generic walking scene, generic playing scene,
or unrelated activity.

Additional objects, actions, or details are allowed only
when they directly support the original story idea.

Example:

USER IDEA:
"Miko menemukan bunga kecil yang hampir layu
di taman dan mencoba menolongnya."

The story MUST remain about:
- Miko
- a small wilted flower
- discovering/noticing the flower
- trying to help the flower

A watering can or small water bottle may be introduced
because it supports the helping action.

However, the watering can or bottle MUST NOT become
the main story object.

========================
STORY STRUCTURE
========================

Create one simple short-form children's story.

The story should generally follow:

DISCOVER
→ TRY
→ PROBLEM
→ SOLUTION
→ HAPPY ENDING / LESSON

The structure does not need to use every stage literally,
but the story must have a clear beginning, understandable
problem, simple solution, and positive ending.

========================
SCENE FIDELITY RULES
========================

Every scene must contribute directly to the original
story idea.

SCENE-01 is especially important.

SCENE-01 MUST visually introduce:
1. the main location,
2. Miko,
3. the main story object,
4. the beginning of the main event.

Do not make SCENE-01 a generic walking,
standing, smiling, or character introduction scene
if that activity is not the main event.

For the example idea about a wilted flower,
SCENE-01 should show Miko noticing or discovering
the small wilted flower in the garden.

Each later scene must logically continue from the
previous scene.

Do not jump to an unrelated activity.

Do not introduce unnecessary characters.

Do not introduce unnecessary locations.

Do not introduce unnecessary major objects.

========================
VISUAL STORY REQUIREMENTS
========================

Every scene must be visually understandable
without relying only on narration.

The "action" field must describe what is visibly happening.

The "location" field must identify the actual story location.

The "characters" field must contain the characters
visibly present in that scene.

The "image_prompt" must describe the actual visual
composition of the scene.

The "video_prompt" must describe movement and camera
behavior for the scene.

IMPORTANT:

The image_prompt MUST NOT contradict:
- location
- characters
- action
- main event
- main story object

The video_prompt MUST NOT introduce a new story event.

========================
MAIN STORY OBJECT LOCK
========================

Identify the main story object from the user's idea.

The main story object must remain consistent
throughout the story whenever it is relevant.

If a supporting object is introduced, clearly keep it
as a supporting object.

Do not accidentally replace the main story object.

========================
MAIN EVENT LOCK
========================

Identify the main event from the user's idea.

Every scene must either:
- introduce,
- develop,
- solve,
- or conclude
the main event.

A scene that does not contribute to the main event
should be rewritten or removed.

========================
CHARACTER RULES
========================

1. Keep Miko as the protagonist.
2. Follow the Miko Master Bible.
3. Keep Miko's appearance consistent.
4. Do not redesign Miko.
5. Keep dialogue short and natural.
6. Avoid unnecessary characters.
7. Do not let supporting characters take over
   the main event.

========================
SAFETY RULES
========================

Target audience:
Children aged 3-8.

The story MUST be:
- safe
- age-appropriate
- positive
- easy to understand
- visually suitable for children's animation

Avoid:
- violence
- horror
- adult themes
- sexual content
- hate
- profanity
- disturbing imagery
- dangerous imitation
- dangerous challenges
- weapons

========================
SHORT-FORM REQUIREMENTS
========================

Language:
{language}

Target duration:
{duration} seconds

Target audience:
Children aged 3-8.

One video =
one main idea
+
one main event
+
one simple message/value.

Use approximately 4-6 scenes.

Keep each scene visually simple.

Avoid excessive simultaneous actions.

Prefer one clear primary action per scene.

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
  "main_event": "",
  "main_object": "",
  "characters": [],
  "locations": [],
  "scenes": [],
  "status": "DRAFT"
}}

The "main_value" MUST contain one primary value only.

The "main_event" MUST describe the central event
derived from the user's story idea.

The "main_object" MUST identify the main story object
derived from the user's story idea.

Each scene must contain:

{{
  "scene_id": "SCENE-01",
  "sequence": 1,
  "duration": 5,
  "location": "",
  "characters": [],
  "main_object": "",
  "action": "",
  "dialogue": "",
  "narration": "",
  "image_prompt": "",
  "video_prompt": "",
  "reference_assets": [],
  "image_status": "PENDING",
  "video_status": "PENDING"
}}

========================
FINAL STORY FIDELITY CHECK
========================

Before returning the JSON, silently validate the story.

CHECK 1:
Does the story preserve the original user's main event?

CHECK 2:
Does the story preserve the original user's main object?

CHECK 3:
Does SCENE-01 introduce the main event and main object?

CHECK 4:
Does every scene contribute directly to the main event?

CHECK 5:
Did any generic activity replace the main event?

CHECK 6:
Did any supporting object accidentally replace
the main story object?

CHECK 7:
Are location, characters, action, image_prompt,
and video_prompt consistent with each other?

CHECK 8:
Is there only one primary value?

CHECK 9:
Are the scenes visually clear and suitable for
image-to-video generation?

If ANY check fails, rewrite the relevant scene/story
before returning the JSON.

Return JSON only.
"""
        return prompt

    async def generate(self, idea, project_id, language="id-ID", duration=45):
        if not isinstance(idea, str) or not idea.strip():
            raise ValueError("Story idea must be a non-empty string.")

        prompt = self.build_prompt(
            idea=idea.strip(),
            language=language,
            duration=duration
        )

        story = await self.provider.generate_json(prompt)

        if not isinstance(story, dict):
            raise RuntimeError(
                "Story Engine received invalid JSON object."
            )

        # Preserve the API contract.
        story["project_id"] = project_id

        # Ensure version metadata is available for history/QC.
        story["story_engine_version"] = self.VERSION

        # Defensive normalization for important fields.
        story.setdefault("main_event", "")
        story.setdefault("main_object", "")
        story.setdefault("main_value", "")
        story.setdefault("characters", [])
        story.setdefault("locations", [])
        story.setdefault("scenes", [])
        story.setdefault("status", "DRAFT")

        if not isinstance(story["scenes"], list):
            raise RuntimeError(
                "Story Engine received invalid 'scenes' array."
            )

        # Ensure scene status fields remain compatible with
        # Scene Engine and the existing image pipeline.
        for index, scene in enumerate(story["scenes"]):
            if not isinstance(scene, dict):
                raise RuntimeError(
                    f"Story Engine received invalid scene at index {index}."
                )

            scene.setdefault(
                "scene_id",
                f"SCENE-{index + 1:02d}"
            )
            scene.setdefault("sequence", index + 1)
            scene.setdefault("duration", 5)
            scene.setdefault("location", "")
            scene.setdefault("characters", [])
            scene.setdefault("main_object", story.get("main_object", ""))
            scene.setdefault("action", "")
            scene.setdefault("dialogue", "")
            scene.setdefault("narration", "")
            scene.setdefault("image_prompt", "")
            scene.setdefault("video_prompt", "")
            scene.setdefault("reference_assets", [])
            scene.setdefault("image_status", "PENDING")
            scene.setdefault("video_status", "PENDING")

        return story
