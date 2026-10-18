
import requests

from config import OLLAMA_GENERATE_URL, OLLAMA_MODEL, REQUEST_TIMEOUT_SECONDS


class AIService:
    """Handles communication with the local Ollama model."""

    def __init__(self):
        self._session = requests.Session()

    def generate_text(self, prompt: str) -> str:
        """Generate text using Ollama and return the model response."""

        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        }

        try:
            response = self._session.post(
                OLLAMA_GENERATE_URL,
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(
                f"Could not generate text using Ollama: {exc}"
            ) from exc

        result = response.json().get("response", "").strip()

        if not result:
            raise RuntimeError("Ollama returned an empty response.")

        return result
