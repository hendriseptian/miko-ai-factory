class StoryEngine:
    def __init__(self):
        self.name = "Miko Story Engine"
        self.version = "1.0"

    def build_prompt(self, idea, language="id-ID", duration=45):
        return {
            "idea": idea,
            "language": language,
            "duration": duration
        }
