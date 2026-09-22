# Miko Story Generator V1

Generate one short Indonesian children's story for Miko.

## Hard constraints
- Follow `bible/MIKO_MASTER_BIBLE_V1.json`.
- Follow `bible/MIKO_STORY_RULES_V1.json`.
- Target age: 3-8.
- Duration: 30-60 seconds, default 45 seconds.
- One main idea, one main event, one simple message.
- Miko is always the protagonist.
- Use a positive, safe ending.

## Output
Return valid JSON only, matching `schemas/story.schema.json`.

The scenes must be visually actionable and suitable for image-to-video generation.
