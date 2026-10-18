
from pathlib import Path

from services.ai_service import AIService


class CurriculumService:
    """Creates and saves learning roadmaps for a given topic."""

    def __init__(self, ai_service: AIService):
        self._ai_service = ai_service
        self._roadmap_directory = (
            Path(__file__).resolve().parent.parent
            / "data"
            / "roadmaps"
        )
        self._roadmap_directory.mkdir(parents=True, exist_ok=True)

    def create_roadmap(self, topic: str) -> str:
        """Generate a sequential learning roadmap for a topic."""

        if not topic or not topic.strip():
            raise ValueError("Topic cannot be empty.")

        prompt = f"""
        You are an expert curriculum designer.

        Create a comprehensive, dynamically sized learning roadmap for:
        {topic}

        Requirements:
        1. Start with prerequisites and beginner concepts.
        2. Progress logically to intermediate and advanced concepts.
        3. Include practical examples, exercises, and a final project.
        4. Cover the important subtopics without unnecessary repetition.
        5. Choose the number of lessons based on the complexity of the topic.
        6. Give every lesson a unique number and title.
        7. Include learning objectives for every lesson.
        8. Identify the key concepts that learners should understand by the end.
        9. Return readable Markdown only.
        """

        roadmap = self._ai_service.generate_text(prompt)
        self.save_roadmap(topic, roadmap)

        return roadmap

    def save_roadmap(self, topic: str, roadmap: str) -> Path:
        """Save a generated roadmap to a Markdown file."""

        if not roadmap or not roadmap.strip():
            raise ValueError("Roadmap cannot be empty.")

        filename = self._create_filename(topic)
        file_path = self._roadmap_directory / filename
        file_path.write_text(roadmap.strip() + "\n", encoding="utf-8")

        return file_path

    @staticmethod
    def _create_filename(topic: str) -> str:
        """Convert a topic into a safe, readable filename."""

        import re

        filename = re.sub(r"[^a-zA-Z0-9]+", "_", topic.strip()).strip("_")
        if not filename:
            raise ValueError("Topic must contain letters or numbers.")

        return f"{filename.lower()}.md"
