import copy


class SceneEngine:
    """
    Miko Scene Engine V1.1

    Focus:
    - Preserve story fidelity from Story Engine V1.1.
    - Convert each scene into production-ready image/video prompts.
    - Make the main story object clearly visible.
    - Prefer story shots over character portraits.
    - Keep image and video responsibilities separate.
    """

    VERSION = "1.1"

    MIKO_CHARACTER_LOCK = """
Miko is a young male orange-and-white kitten,
visual age approximately 4-6 years old,
with large expressive dark brown eyes,
a pink nose,
a round relatively large head,
a small rounded body,
short legs,
and soft orange-and-white fur.

Miko wears a bright blue hoodie with white drawstrings
and a paw-shaped pendant.

Miko does not wear shoes.

Miko has a cheerful, curious, kind, playful,
friendly, brave, slightly clumsy,
and helpful personality.

Keep Miko's appearance identical across all scenes.
Do not redesign, recolor, age, or replace Miko.
"""

    VISUAL_STYLE_LOCK = """
Polished stylized 3D children's animation.

Colorful, warm, cheerful, safe, playful,
soft rounded shapes, expressive character design,
soft cinematic lighting, clean composition,
high visual clarity, child-friendly environment.

Target audience: children aged 3-8.

Vertical composition, 9:16 aspect ratio.

Avoid realistic human appearance.
Avoid horror, darkness, violence, disturbing imagery,
adult themes, weapons, or dangerous behavior.
"""

    def __init__(self, story):
        if not isinstance(story, dict):
            raise ValueError("Story must be a JSON object.")
        self.story = copy.deepcopy(story)

    def build_character_lock(self):
        return self.MIKO_CHARACTER_LOCK.strip()

    def build_visual_style_lock(self):
        return self.VISUAL_STYLE_LOCK.strip()

    def get_main_object(self, scene):
        """
        Prefer the scene-level main_object introduced by
        Story Engine V1.1. Fall back to the story-level object.
        """
        scene_object = scene.get("main_object")
        if isinstance(scene_object, str) and scene_object.strip():
            return scene_object.strip()

        story_object = self.story.get("main_object")
        if isinstance(story_object, str) and story_object.strip():
            return story_object.strip()

        return ""

    def build_image_prompt(self, scene):
        location = str(scene.get("location", "")).strip()
        action = str(scene.get("action", "")).strip()
        characters = ", ".join(
            str(item).strip()
            for item in scene.get("characters", [])
            if str(item).strip()
        )
        main_object = self.get_main_object(scene)

        prompt = f"""
CHARACTER LOCK:
{self.build_character_lock()}

VISUAL STYLE:
{self.build_visual_style_lock()}

STORY OBJECT PRIORITY:
Main story object:
{main_object}

The main story object is essential to this scene.

Make the main story object clearly visible,
recognizable, and visually relevant.

Do not hide, crop, obscure, or replace the main story object.

The main story object must not become a vague background detail.

SCENE:
Location: {location}
Characters: {characters}
Action: {action}

SHOT TYPE:
Create a story-focused production shot,
not a character portrait.

Prefer a medium-wide or wide composition when needed
to show Miko together with the main story object.

Miko should not fill the entire frame.

Show enough of the environment to clearly establish
the story location.

If the main story object is small, place it in the
foreground or middle ground so it remains clearly visible.

Miko should visually interact with, notice, look toward,
approach, or act toward the main story object according
to the exact scene action.

COMPOSITION:
Use clear foreground, middle ground, and background.

Place Miko and the main story object in the same
readable composition whenever the story action allows it.

The camera should prioritize the relationship between
Miko and the main story object.

Do not use an extreme close-up of Miko's face unless
the scene explicitly requires a facial reaction.

Do not create a character reference sheet,
character turnaround, fashion portrait, or isolated
character portrait.

IMAGE REQUIREMENTS:
Create one clear vertical 9:16 production frame.

Show one specific visual moment from the scene.

The image must visually communicate:
1. where the scene happens,
2. what Miko is doing,
3. what the main story object is,
4. how Miko relates to the main story object.

Keep Miko's character identity consistent with the
Character Lock above.

Keep the main story object consistent with the
Story Object Priority above.

Do not introduce unnecessary characters,
objects, locations, or visual events.

Do not redesign Miko.

Do not add text, subtitles, logos, watermark,
or UI elements.

The image should be suitable as the starting frame
for image-to-video generation.

Do not add a new story event that is not present
in the scene action.
"""
        return self.clean_prompt(prompt)

    def build_video_prompt(self, scene):
        action = str(scene.get("action", "")).strip()
        video_prompt = str(scene.get("video_prompt", "")).strip()
        main_object = self.get_main_object(scene)

        prompt = f"""
CHARACTER CONSISTENCY:
Keep Miko exactly consistent with the established
Miko Character Lock.

MAIN STORY OBJECT:
{main_object}

SCENE ACTION:
{action}

CAMERA / MOVEMENT:
{video_prompt}

VIDEO REQUIREMENTS:
Create subtle, natural animation suitable for
a children's 3D animated short.

Preserve the composition and character identity
from the source image.

Keep the main story object clearly visible
during the important part of the action.

Animate the exact scene action rather than inventing
a different story event.

Use gentle character movement and simple camera motion.

Do not redesign Miko.

Do not change clothing, fur color, face,
body proportions, or accessories.

Do not replace, remove, or transform the main story object.

Do not introduce new characters or locations.

Avoid sudden camera movements, distortion,
extra limbs, duplicated objects, flickering,
or unnatural deformation.

Maintain a clean vertical 9:16 composition.
"""
        return self.clean_prompt(prompt)

    def clean_prompt(self, prompt):
        lines = [
            line.strip()
            for line in prompt.strip().splitlines()
            if line.strip()
        ]
        return "\n".join(lines)

    def process_scene(self, scene):
        processed = copy.deepcopy(scene)

        main_object = self.get_main_object(scene)

        processed["scene_engine_version"] = self.VERSION
        processed["main_object"] = main_object

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
            raise ValueError(
                "Story field 'scenes' must be an array."
            )

        processed_scenes = []

        for index, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                raise ValueError(
                    f"Scene at index {index} is invalid."
                )

            processed_scenes.append(
                self.process_scene(scene)
            )

        result = {
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
            "scenes": processed_scenes
        }

        return result
