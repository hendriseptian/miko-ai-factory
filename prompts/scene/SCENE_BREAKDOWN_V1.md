# Miko Scene Breakdown V1

Convert an approved Miko story into short production scenes.

For each scene define:
1. scene_id
2. sequence
3. duration
4. location
5. characters
6. action
7. dialogue
8. narration
9. image_prompt
10. video_prompt
11. reference_assets

Rules:
- Preserve Miko identity.
- Keep each scene visually simple.
- Avoid unnecessary location changes.
- Image prompt describes the final frame/composition.
- Video prompt describes motion and camera behavior.
- Use image-to-video logic: reference image = identity, video prompt = motion.
