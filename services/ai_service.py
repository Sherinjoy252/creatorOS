
from openai import OpenAI, APIError

from config import (
    MESH_API_KEY,
    MESH_BASE_URL,
    MESH_MODEL,
    REQUEST_TIMEOUT_SECONDS,
)


class AIService:
    """Generate text through the Mesh API."""

    def __init__(self):
        if not MESH_API_KEY:
            raise RuntimeError(
                "MESH_API_KEY is missing. Add it to your .env file."
            )

        if not MESH_MODEL:
            raise RuntimeError(
                "MESH_MODEL is missing. Check your config.py and .env."
            )

        self._client = OpenAI(
            api_key=MESH_API_KEY,
            base_url=MESH_BASE_URL,
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=2,
        )

    def generate_text(self, prompt: str) -> str:
        """Generate text from a non-empty prompt."""

        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        try:
            response = self._client.chat.completions.create(
                model=MESH_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
            )
        except APIError as exc:
            raise RuntimeError(
                f"Mesh API request failed: {exc}"
            ) from exc

        result = response.choices[0].message.content

        if not result or not result.strip():
            raise RuntimeError(
                "Mesh API returned an empty response."
            )

        return result.strip()