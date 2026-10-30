import base64
from pathlib import Path
from urllib.request import urlopen

from openai import OpenAI, APIError

from config import (
    MESH_API_KEY,
    MESH_BASE_URL,
    MESH_IMAGE_MODEL,
    REQUEST_TIMEOUT_SECONDS,
)


class ImageGenerationService:
    """Generate images through Mesh API's OpenAI-compatible Images endpoint."""

    def __init__(self):
        if not MESH_API_KEY:
            raise RuntimeError(
                "MESH_API_KEY is missing. Add it to your .env file."
            )

        if not MESH_IMAGE_MODEL:
            raise RuntimeError(
                "MESH_IMAGE_MODEL is missing. Check config.py and .env."
            )

        self._client = OpenAI(
            api_key=MESH_API_KEY,
            base_url=MESH_BASE_URL,
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=2,
        )

    def generate_image(
        self,
        prompt: str,
        output_path: str | Path,
        size: str = "1024x1024",
    ) -> dict:
        """Generate one image and save it locally.

        Returns the model name, output path, and hosted URL when provided.
        """

        if not prompt or not prompt.strip():
            raise ValueError("Image prompt cannot be empty.")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            response = self._client.images.generate(
                model=MESH_IMAGE_MODEL,
                prompt=prompt.strip(),
                size=size,
                n=1,
            )
        except APIError as exc:
            raise RuntimeError(
                f"Mesh image-generation request failed: {exc}"
            ) from exc

        if not response.data:
            raise RuntimeError("Mesh API returned no image data.")

        image_result = response.data[0]
        image_url = getattr(image_result, "url", None)
        image_base64 = getattr(image_result, "b64_json", None)

        if image_url:
            # Download the generated image while its hosted URL is available.
            with urlopen(image_url, timeout=REQUEST_TIMEOUT_SECONDS) as result:
                output_path.write_bytes(result.read())
        elif image_base64:
            output_path.write_bytes(base64.b64decode(image_base64))
        else:
            raise RuntimeError(
                "Mesh API returned neither an image URL nor base64 image data."
            )

        return {
            "model": MESH_IMAGE_MODEL,
            "image_url": image_url,
            "output_path": str(output_path),
        }
