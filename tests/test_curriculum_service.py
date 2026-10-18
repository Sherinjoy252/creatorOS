
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from services.curriculum_service import CurriculumService


class TestCurriculumService(unittest.TestCase):

    def test_create_roadmap_saves_markdown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ai_service = Mock()
            ai_service.generate_text.return_value = (
                "# Spring Boot\n\n"
                "## Lesson 1: Introduction\n"
            )

            service = CurriculumService(ai_service)
            service._roadmap_directory = Path(temp_dir)

            roadmap = service.create_roadmap("Spring Boot")

            saved_file = Path(temp_dir) / "spring_boot.md"

            self.assertIn("Lesson 1", roadmap)
            self.assertTrue(saved_file.exists())
            self.assertEqual(
                saved_file.read_text(encoding="utf-8"),
                roadmap.strip() + "\n",
            )
            ai_service.generate_text.assert_called_once()


if __name__ == "__main__":
    unittest.main()
