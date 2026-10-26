
import unittest
from unittest.mock import MagicMock, Mock
from uuid import uuid4

from services.brand_voice_service import BrandVoiceService


class TestBrandVoiceService(unittest.TestCase):
    def setUp(self):
        self.ai_service = Mock()
        self.service = BrandVoiceService(self.ai_service)
        self.db = MagicMock()
        self.user_id = uuid4()

        self.posts = [
            "Learn Java with small examples.",
            "Keep your code simple and readable.",
            "Practice one concept at a time.",
        ]

    def test_learn_voice_requires_three_posts(self):
        with self.assertRaises(ValueError):
            self.service.learn_voice([
                "First post",
                "Second post",
            ])

        self.ai_service.generate_text.assert_not_called()

    def test_learn_voice_uses_multiple_samples(self):
        self.ai_service.generate_text.return_value = (
            "Simple language, practical examples, friendly tone."
        )

        profile = self.service.learn_voice(self.posts)

        self.assertIn("practical examples", profile)
        prompt = self.ai_service.generate_text.call_args.args[0]

        self.assertIn("Sample 1:", prompt)
        self.assertIn("Sample 2:", prompt)
        self.assertIn("Sample 3:", prompt)

    def test_save_voice_creates_profile(self):
        self.db.scalar.return_value = None

        result = self.service.save_voice(
            db=self.db,
            user_id=self.user_id,
            profile="Friendly and practical.",
            sample_posts=self.posts,
        )

        self.db.add.assert_called_once()
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once_with(result)

        self.assertEqual(result.user_id, self.user_id)
        self.assertEqual(result.profile, "Friendly and practical.")
        self.assertEqual(result.sample_posts, self.posts)

    def test_save_voice_updates_existing_profile(self):
        existing = MagicMock()
        self.db.scalar.return_value = existing

        result = self.service.save_voice(
            db=self.db,
            user_id=self.user_id,
            profile="Formal and concise.",
            sample_posts=self.posts,
        )

        self.assertIs(result, existing)
        self.assertEqual(existing.profile, "Formal and concise.")
        self.assertEqual(existing.sample_posts, self.posts)

        self.db.add.assert_not_called()
        self.db.commit.assert_called_once()

    def test_save_voice_rejects_empty_profile(self):
        with self.assertRaises(ValueError):
            self.service.save_voice(
                db=self.db,
                user_id=self.user_id,
                profile=" ",
                sample_posts=self.posts,
            )

        self.db.commit.assert_not_called()

    def test_save_voice_requires_three_posts(self):
        with self.assertRaises(ValueError):
            self.service.save_voice(
                db=self.db,
                user_id=self.user_id,
                profile="Friendly tone.",
                sample_posts=["Only one post"],
            )

        self.db.commit.assert_not_called()

    def test_load_voice_queries_by_user_id(self):
        expected = MagicMock()
        self.db.scalar.return_value = expected

        result = self.service.load_voice(
            db=self.db,
            user_id=self.user_id,
        )

        self.assertIs(result, expected)
        self.db.scalar.assert_called_once()


if __name__ == "__main__":
    unittest.main()
