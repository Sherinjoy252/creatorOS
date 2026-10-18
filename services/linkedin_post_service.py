
from pathlib import Path

from services.ai_service import AIService


class LinkedInPostService:
    """Generates and saves educational LinkedIn post drafts."""

    def __init__(self, ai_service: AIService):
        self._ai_service = ai_service
        self._draft_directory = (
            Path(__file__).resolve().parent.parent / "drafts"
        )
        self._draft_directory.mkdir(parents=True, exist_ok=True)

    def create_post(self, topic: str, lesson: str) -> str:
        """Generate an educational LinkedIn post for one lesson."""

        if not topic or not topic.strip():
            raise ValueError("Topic cannot be empty.")

        if not lesson or not lesson.strip():
            raise ValueError("Lesson cannot be empty.")

        prompt = f"""
        You are an educational content creator writing for LinkedIn.

        Overall topic: {topic}

        Lesson to teach:
        {lesson}

        Write one educational LinkedIn post.

        Requirements:
        1. Start with a clear, engaging hook.
        2. Teach one main concept in simple, accurate language.
        3. Include a practical example when relevant.
        4. Explain why the concept matters.
        5. End with a takeaway and a question for readers.
        6. Add 3-5 relevant hashtags.
        7. Do not invent personal experiences or achievements.
        8. Avoid unsupported claims and unnecessary promotional language.
        9. Return only the post in readable Markdown.
        """

        return self._ai_service.generate_text(prompt)

    def save_draft(self, topic: str, lesson_number: int, post: str) -> Path:
        """Save a generated post as a Markdown draft."""

        if lesson_number < 1:
            raise ValueError("Lesson number must be at least 1.")

        if not post or not post.strip():
            raise ValueError("Post cannot be empty.")

        safe_topic = self._create_filename(topic)
        filename = f"{safe_topic}_lesson_{lesson_number:02d}.md"
        file_path = self._draft_directory / filename

        file_path.write_text(post.strip() + "\n", encoding="utf-8")
        return file_path

    @staticmethod
    def _create_filename(topic: str) -> str:
        import re

        filename = re.sub(
            r"[^a-zA-Z0-9]+", "_", topic.strip()
        ).strip("_")

        if not filename:
            raise ValueError("Topic must contain letters or numbers.")

        return filename.lower()
