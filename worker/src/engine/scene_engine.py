import copy


class SceneEngine:
    """
    Miko Scene Engine V1

    Responsibilities:
    - Receive generated Story JSON
    - Convert story scenes into production-ready scene data
    - Lock Miko's visual identity
    - Lock the visual style
    - Generate consistent image prompts
    - Generate consistent video prompts

    Scene Engine does NOT generate images or videos.
    It only prepares production instructions.
    """

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

    def build_image_prompt(self, scene):
        location = scene.get("location", "")
        action = scene.get("action", "")
        characters = ", ".join(scene.get("characters", []))

        prompt = f"""
CHARACTER LOCK:
{self.build_character_lock()}

VISUAL STYLE:
{self.build_visual_style_lock()}

SCENE:
Location: {location}
Characters: {characters}
Action: {action}

IMAGE REQUIREMENTS:
Create one clear vertical 9:16 production frame.

Show the exact action described in the scene.

Keep Miko's character identity consistent with the
Character Lock above.

Use a clear foreground, middle ground, and background
when appropriate.

Use a simple composition that is easy to understand
for children.

Do not introduce unnecessary characters,
objects, locations, or visual events.

Do not redesign Miko.

Do not add text, subtitles, logos, watermark,
or UI elements.

The image should be suitable as the starting frame
for image-to-video generation.
"""

        return self.clean_prompt(prompt)

    def build_video_prompt(self, scene):
        action = scene.get("action", "")
        video_prompt = scene.get("video_prompt", "")

        prompt = f"""
CHARACTER CONSISTENCY:
Keep Miko exactly consistent with the established
Miko Character Lock.

SCENE ACTION:
{action}

CAMERA / MOVEMENT:
{video_prompt}

VIDEO REQUIREMENTS:
Create subtle, natural animation suitable for
a children's 3D animated short.

Preserve the composition and character identity
from the source image.

Use gentle character movement and simple camera motion.

Do not redesign Miko.

Do not change clothing, fur color, face,
body proportions, or accessories.

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

        processed["character_lock"] = self.build_character_lock()
        processed["visual_style"] = self.build_visual_style_lock()

        processed["source_image_prompt"] = scene.get(
            "image_prompt",
            ""
        )

        processed["source_video_prompt"] = scene.get(
            "video_prompt",
            ""
        )

        processed["image_prompt_v1"] = self.build_image_prompt(
            scene
        )

        processed["video_prompt_v1"] = self.build_video_prompt(
            scene
        )

        processed["image_status"] = scene.get(
            "image_status",
            "PENDING"
        )

        processed["video_status"] = scene.get(
            "video_status",
            "PENDING"
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
            "duration_target": self.story.get(
                "duration_target"
            ),
            "scene_count": len(processed_scenes),
            "status": "SCENE_READY",
            "character_lock": self.build_character_lock(),
            "visual_style": self.build_visual_style_lock(),
            "scenes": processed_scenes
        }

        return result
