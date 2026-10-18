
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from services.linkedin_post_service import LinkedInPostService


class TestLinkedInPostService(unittest.TestCase):

    def test_create_post_uses_ai_service(self):
        ai_service = Mock()
        ai_service.generate_text.return_value = (
            "What is Spring Boot?\n\nIt simplifies Spring development."
        )

        service = LinkedInPostService(ai_service)
        post = service.create_post(
            "Spring Boot",
            "Lesson 1: Introduction to Spring Boot",
        )

        self.assertIn("Spring Boot", post)
        ai_service.generate_text.assert_called_once()

    def test_save_draft_creates_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ai_service = Mock()
            service = LinkedInPostService(ai_service)
            service._draft_directory = Path(temp_dir)

            path = service.save_draft(
                "Spring Boot",
                1,
                "A sample educational post.",
            )

            self.assertTrue(path.exists())
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "A sample educational post.\n",
            )


if __name__ == "__main__":
    unittest.main()
