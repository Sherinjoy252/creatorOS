
import unittest
from unittest.mock import Mock, patch

from services.ai_service import AIService


class TestAIService(unittest.TestCase):

    @patch("services.ai_service.OpenAI")
    def test_generate_text_returns_response(self, mock_openai):
        mock_client = Mock()
        mock_openai.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    content="Spring Boot simplifies Spring development."
                )
            )
        ]

        mock_client.chat.completions.create.return_value = mock_response

        service = AIService()
        result = service.generate_text(
            "Explain Spring Boot in one sentence."
        )

        self.assertEqual(
            result,
            "Spring Boot simplifies Spring development."
        )

        mock_client.chat.completions.create.assert_called_once_with(
            model=service._client.chat.completions.create.call_args.kwargs["model"],
            messages=[
                {
                    "role": "user",
                    "content": "Explain Spring Boot in one sentence.",
                }
            ],
        )
