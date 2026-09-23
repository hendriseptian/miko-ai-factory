import copy


class SceneEngine:
    """
    Miko Scene Engine V1.2

    Converts Story Engine scenes into production-ready image/video prompts.
    Keeps the existing constructor and process() interface compatible with
    the Miko AI Factory V0.4.x main.py.
    """

    VERSION = "1.2"

    MIKO_CHARACTER_LOCK = """
Miko is a young male orange-and-white kitten, visual age 4-6 years old.
He has large expressive dark brown eyes, a pink nose, a round relatively
large head, a small rounded body, short legs, and soft orange-and-white fur.
He wears a bright blue hoodie with white drawstrings and a paw-shaped pendant.
He does not wear shoes.
Keep Miko's appearance consistent across all scenes.
Do not redesign, recolor, age, replace, or duplicate Miko.
"""

    VISUAL_STYLE_LOCK = """
Polished stylized 3D children's animation.
Colorful, warm, cheerful, safe, playful.
Soft rounded shapes, expressive character design,
soft cinematic lighting, clean readable composition.
Child-friendly environment.
Vertical 9:16 composition.
"""

    SAFETY_LOCK = """
No text, subtitles, logos, watermark, UI, horror, violence,
weapons, adult themes, disturbing imagery, dangerous behavior,
extra limbs, duplicated characters, or distorted anatomy.
"""

    def __init__(self, story):
        if not isinstance(story, dict):
            raise ValueError("Story must be a JSON object.")
        self.story = copy.deepcopy(story)

    def build_character_lock(self):
        return self.MIKO_CHARACTER_LOCK.strip()

    def build_visual_style_lock(self):
        return self.VISUAL_STYLE_LOCK.strip()

    def build_safety_lock(self):
        return self.SAFETY_LOCK.strip()

    def get_main_object(self, scene):
        scene_object = scene.get("main_object")
        if isinstance(scene_object, str) and scene_object.strip():
            return scene_object.strip()

        story_object = self.story.get("main_object")
        if isinstance(story_object, str) and story_object.strip():
            return story_object.strip()

        return ""

    def get_main_event(self, scene):
        scene_event = scene.get("main_event")
        if isinstance(scene_event, str) and scene_event.strip():
            return scene_event.strip()

        story_event = self.story.get("main_event")
        if isinstance(story_event, str) and story_event.strip():
            return story_event.strip()

        return ""

    def get_characters(self, scene):
        characters = scene.get("characters", [])
        if not isinstance(characters, list):
            return []

        return [
            str(item).strip()
            for item in characters
            if str(item).strip()
        ]

    def build_scene_composition(self, scene):
        main_object = self.get_main_object(scene)
        action = str(scene.get("action", "")).strip()

        if main_object:
            object_instruction = f"""
MAIN STORY OBJECT:
{main_object}

The main story object is a required visual element.
Make it clearly visible and recognizable.
It must be large enough to identify easily.
Do not hide, crop, obscure, replace, or minimize it
into an insignificant background detail.
Show Miko and the main story object together
in the same readable frame.
"""
        else:
            object_instruction = """
There is no explicit main story object.
Do not invent a new major story object.
Focus on the exact scene action.
"""

        return f"""
SHOT TYPE:
Story-focused medium-wide production shot, not a portrait.

CAMERA:
Use a camera distance wide enough to show Miko's body,
the actual environment, and the main story object.

COMPOSITION:
Miko and the main story object must both be readable
in the same frame and visibly related to the action.
Keep enough space around them to understand the scene.
Do not fill the frame with Miko's face.
Do not use an extreme close-up.
Do not crop the main story object.

ENVIRONMENT:
Show enough of the stated location to make the location
immediately understandable.

ACTION MOMENT:
Show ONE clear visual moment from this action:
{action}

{object_instruction}
""".strip()

    def build_image_prompt(self, scene):
        location = str(scene.get("location", "")).strip()
        action = str(scene.get("action", "")).strip()
        characters = ", ".join(self.get_characters(scene))
        main_object = self.get_main_object(scene)
        main_event = self.get_main_event(scene)

        source_image_prompt = str(
            scene.get("image_prompt", "")
        ).strip()

        sections = [
            "VERTICAL STORY FRAME — 9:16.",
            "",
            "STORY CONTEXT:",
            f"Main event: {main_event or 'Follow the exact scene action.'}",
            f"Main story object: {main_object or 'None specified.'}",
            "",
            "SCENE:",
            f"Location: {location or 'Use the scene location.'}",
            f"Characters: {characters or 'Miko'}",
            f"Action: {action or 'Show the exact scene action.'}",
            "",
            self.build_scene_composition(scene),
            "",
            "MIKO CHARACTER:",
            self.build_character_lock(),
            "",
            "VISUAL STYLE:",
            self.build_visual_style_lock(),
            "",
            "STORY FIDELITY:",
            """
This must look like a scene from a children's animated story,
not a character showcase.

The image must communicate the story event visually.
Miko must be visibly performing or reacting to the exact
scene action.

If a main story object exists, it must be clearly visible
in the same frame as Miko.

Do not replace the main story object with another object.
Do not remove the main story object.
Do not turn the scene into a generic standing, walking,
smiling, or character showcase image.

Use one clear visual moment.
Do not depict multiple sequential actions in one frame.
""".strip(),
            "",
            "SAFETY / NEGATIVE CONSTRAINTS:",
            self.build_safety_lock(),
        ]

        if source_image_prompt:
            sections.extend([
                "",
                "SOURCE STORY DESCRIPTION:",
                """
Use this only as additional narrative context.
The SCENE, ACTION, MAIN STORY OBJECT, and COMPOSITION
rules above have priority.
""".strip(),
                source_image_prompt,
            ])

        return self.clean_prompt("\n".join(sections))

    def build_video_prompt(self, scene):
        action = str(scene.get("action", "")).strip()
        video_prompt = str(scene.get("video_prompt", "")).strip()
        main_object = self.get_main_object(scene)

        prompt = f"""
VERTICAL VIDEO SCENE — 9:16.

CHARACTER CONSISTENCY:
{self.build_character_lock()}

MAIN STORY OBJECT:
{main_object or "No explicit main story object."}

SCENE ACTION:
{action or "Follow the source scene exactly."}

SOURCE CAMERA / MOVEMENT:
{video_prompt or "Use subtle natural movement and gentle camera motion."}

VIDEO DIRECTION:
Animate the exact action from the source scene.
Preserve the source image composition.

Keep Miko and the main story object clearly visible
when both are present in the source image.

Do not invent a new story event.
Do not replace or remove the main story object.
Do not redesign Miko.
Do not change Miko's clothing, fur, face,
body proportions, or pendant.

Use gentle children's animation movement.
Avoid sudden camera movements, flickering,
object duplication, extra limbs, facial distortion,
or unnatural deformation.

Maintain vertical 9:16 composition.

{self.build_safety_lock()}
"""
        return self.clean_prompt(prompt)

    def clean_prompt(self, prompt):
        lines = [line.rstrip() for line in prompt.strip().splitlines()]
        cleaned = []
        previous_blank = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                if not previous_blank:
                    cleaned.append("")
                previous_blank = True
                continue

            cleaned.append(stripped)
            previous_blank = False

        return "\n".join(cleaned).strip()

    def process_scene(self, scene):
        processed = copy.deepcopy(scene)

        processed["scene_engine_version"] = self.VERSION
        processed["main_event"] = self.get_main_event(scene)
        processed["main_object"] = self.get_main_object(scene)

        processed["character_lock"] = self.build_character_lock()
        processed["visual_style"] = self.build_visual_style_lock()

        processed["source_image_prompt"] = scene.get(
            "image_prompt", ""
        )
        processed["source_video_prompt"] = scene.get(
            "video_prompt", ""
        )

        processed["image_prompt_v1"] = self.build_image_prompt(scene)
        processed["video_prompt_v1"] = self.build_video_prompt(scene)

        processed["image_status"] = scene.get(
            "image_status", "PENDING"
        )
        processed["video_status"] = scene.get(
            "video_status", "PENDING"
        )

        return processed

    def process(self):
        scenes = self.story.get("scenes", [])

        if not isinstance(scenes, list):
            raise ValueError("Story field 'scenes' must be an array.")

        processed_scenes = []

        for index, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                raise ValueError(
                    f"Scene at index {index} is invalid."
                )

            processed_scenes.append(self.process_scene(scene))

        return {
            "project_id": self.story.get("project_id"),
            "title": self.story.get("title"),
            "language": self.story.get("language"),
            "duration_target": self.story.get("duration_target"),
            "main_event": self.story.get("main_event", ""),
            "main_object": self.story.get("main_object", ""),
            "scene_engine_version": self.VERSION,
            "scene_count": len(processed_scenes),
            "status": "SCENE_READY",
            "character_lock": self.build_character_lock(),
            "visual_style": self.build_visual_style_lock(),
            "scenes": processed_scenes,
        }
