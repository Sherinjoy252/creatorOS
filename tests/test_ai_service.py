
import unittest
from unittest.mock import patch, Mock

from services.ai_service import AIService


class TestAIService(unittest.TestCase):

    def test_generate_text_returns_response(self):
        service = AIService()

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "response": "Spring Boot simplifies Spring development."
        }

        with patch.object(
            service._session, "post", return_value=mock_response
        ) as mock_post:
            result = service.generate_text("Explain Spring Boot")

        self.assertEqual(
            result, "Spring Boot simplifies Spring development."
        )
        mock_post.assert_called_once()


if __name__ == "__main__":
    unittest.main()
