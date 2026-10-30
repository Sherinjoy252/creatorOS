from pathlib import Path
from typing import Any
from uuid import UUID


class ImageStorageService:
    """Local image storage behind an interface that can later support cloud storage."""

    def __init__(self, root_dir: str | Path | None = None):
        # This file lives in server/services; the default is server/generated_content.
        self.root_dir = (
            Path(root_dir).resolve()
            if root_dir is not None
            else Path(__file__).resolve().parents[1] / "generated_content"
        )

    def store_generated_image(
        self,
        user_id: UUID,
        content_id: UUID,
        generator: Any,
        prompt: str,
        size: str = "1024x1024",
    ) -> tuple[str, dict]:
        """Generate an image into the authenticated user's private directory."""
        relative_path = Path(str(user_id)) / f"{content_id}.png"
        output_path = self._safe_resolve(relative_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result = generator.generate_image(
            prompt=prompt,
            output_path=output_path,
            size=size,
        )
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise RuntimeError("Image generation did not produce a valid file.")

        return relative_path.as_posix(), result

    def resolve_path(self, relative_path: str) -> Path:
        """Resolve a database storage key while preventing path traversal."""
        return self._safe_resolve(Path(relative_path))

    def exists(self, relative_path: str) -> bool:
        return self.resolve_path(relative_path).is_file()

    def _safe_resolve(self, relative_path: Path) -> Path:
        candidate = (self.root_dir / relative_path).resolve()
        try:
            candidate.relative_to(self.root_dir)
        except ValueError as exc:
            raise ValueError("Invalid image storage path.") from exc
        return candidate
