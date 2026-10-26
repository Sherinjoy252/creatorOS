
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import BrandVoice
from services.ai_service import AIService


class BrandVoiceService:
    def __init__(self, ai_service: AIService | None = None):
        self.ai_service = ai_service or AIService()

    def learn_voice(self, sample_posts: list[str]) -> str:
        posts = [
            post.strip()
            for post in sample_posts
            if post and post.strip()
        ]

        if len(posts) < 3:
            raise ValueError(
                "Please provide at least 3 non-empty sample posts."
            )

        samples = "\n\n--- SAMPLE POST ---\n\n".join(
            f"Sample {index}:\n{post}"
            for index, post in enumerate(posts, start=1)
        )

        prompt = f"""You are a brand voice analyst.
Analyse these existing posts and create a reusable writing profile.
Infer patterns from the samples instead of inventing preferences.

Identify:
- Tone and personality
- Sentence length and complexity
- Vocabulary and technical depth
- Formatting and paragraph structure
- Emoji and hashtag usage
- Common writing habits to preserve
- Writing habits to avoid

Do not copy entire sentences from the samples.
Return a concise, actionable profile that another writing agent can follow.

EXISTING POSTS:
{samples}
"""

        profile = self.ai_service.generate_text(prompt).strip()

        if not profile:
            raise RuntimeError(
                "Could not generate a brand voice profile."
            )

        return profile

    def save_voice(
        self,
        db: Session,
        user_id: UUID,
        profile: str,
        sample_posts: list[str],
    ) -> BrandVoice:
        if not profile or not profile.strip():
            raise ValueError("Brand voice profile cannot be empty.")

        posts = [
            post.strip()
            for post in sample_posts
            if post and post.strip()
        ]

        if len(posts) < 3:
            raise ValueError(
                "Please provide at least 3 non-empty sample posts."
            )

        voice = db.scalar(
            select(BrandVoice).where(
                BrandVoice.user_id == user_id
            )
        )

        if voice is None:
            voice = BrandVoice(
                user_id=user_id,
                profile=profile.strip(),
                sample_posts=posts,
            )
            db.add(voice)
        else:
            voice.profile = profile.strip()
            voice.sample_posts = posts

        db.commit()
        db.refresh(voice)

        return voice

    def load_voice(
        self,
        db: Session,
        user_id: UUID,
    ) -> BrandVoice | None:
        return db.scalar(
            select(BrandVoice).where(
                BrandVoice.user_id == user_id
            )
        )
