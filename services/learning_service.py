
import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.ai_service import AIService
from models import GeneratedContent, LearningLesson, PostPerformance


class LearningService:
    def __init__(self):
        self.ai = AIService()

    
    def propose_lessons(
        self,
        db: Session,
        content: GeneratedContent,
        user_id,
    ) -> list[str]:

        snapshots = db.scalars(
            select(PostPerformance)
            .where(PostPerformance.content_id == content.id)
            .order_by(PostPerformance.recorded_at.asc())
        ).all()

        if not snapshots:
            raise ValueError(
                "Add at least one performance snapshot before teaching CreatorOS."
            )

        sources = {snapshot.data_source for snapshot in snapshots}

        if sources == {"simulated"}:
            data_notice = (
                "All snapshots are simulated. Do not present these results "
                "as real audience evidence. Lessons must be labelled as "
                "demo-only and should not be used as approved real-performance "
                "lessons."
            )
        elif "simulated" in sources:
            data_notice = (
                "These snapshots mix manual and simulated data. Clearly "
                "separate the evidence and do not draw real-performance "
                "conclusions from simulated values."
            )
        else:
            data_notice = "These snapshots were entered manually."

        # Include every existing decision so the AI does not recreate an
        # approved, rejected, or still-pending insight on every snapshot.
        existing_lessons = db.scalars(
            select(LearningLesson)
            .where(
                LearningLesson.content_id == content.id,
                LearningLesson.user_id == user_id,
            )
            .order_by(LearningLesson.created_at.asc())
        ).all()

        existing_lesson_context = [
            {
                "lesson": item.lesson,
                "status": item.status,
            }
            for item in existing_lessons
            if getattr(item, "lesson", None)
        ]

        performance_data = [
            {
                "impressions": item.impressions,
                "likes": item.likes,
                "comments_count": item.comments,
                "reposts": item.reposts,
                "audience_comments": item.audience_comments or [],
                "data_source": item.data_source,
                "recorded_at": (
                    item.recorded_at.isoformat()
                    if item.recorded_at
                    else None
                ),
            }
            for item in snapshots
        ]

        all_audience_comments = [
            comment
            for item in snapshots
            for comment in (item.audience_comments or [])
        ]

        prompt = f"""
    You are the performance-learning analyst for CreatorOS.

    Analyze this LinkedIn post and its performance history.

    Topic: {content.topic}

    Post:
    {content.draft}

    Performance snapshots (oldest first):
    {json.dumps(performance_data, indent=2)}

    Audience comments collected:
    {json.dumps(all_audience_comments, indent=2)}

    Existing lessons and their decisions:
    {json.dumps(existing_lesson_context, indent=2)}

    Data notice:
    {data_notice}

    Instructions:

    1. Treat snapshots as cumulative observations of one post,
    not independent posts.
    2. Do not claim that the metrics prove causation.
    3. If there is only one snapshot, say that trend evidence is limited.
    4. Consider impressions, likes, comments count, and reposts.
    5. Analyse actual audience comments for questions, positive feedback,
    confusion, requests for examples, and recurring themes.
    6. Use audience comments as qualitative evidence, not as
    representative feedback from the entire audience.
    7. Do not invent missing metrics, audience demographics,
    or comments.
    8. If no audience comments are available, rely on the metrics
    and explicitly acknowledge the limited qualitative evidence.
    9. Compare every possible insight against ALL existing lessons above.
       Treat paraphrases and semantically equivalent statements as duplicates,
       even if their wording differs.
    10. Do not recreate an existing lesson regardless of whether its status
        is proposed, approved, or rejected. Never try to reverse a user's
        previous decision by proposing the same insight again.
    11. Return only genuinely new insights supported by meaningful evidence.
        If the new snapshot adds no materially new insight, return an empty
        lessons array. Do not invent a new wording just to produce a lesson.
    12. Produce at most ONE concise, specific, actionable new lesson.
        If several observations point to the same theme, combine them into
        one lesson. Do not split one insight into multiple paraphrases.
    13. Return ONLY valid JSON in this format:

    {{
    "lessons": [
        "A concise lesson grounded in the supplied data"
    ]
    }}
    """

        result = self.ai.generate_text(prompt)

        try:
            parsed = json.loads(result)
            lessons = parsed.get("lessons", [])
        except (json.JSONDecodeError, AttributeError):
            raise RuntimeError(
                "The AI returned an invalid lesson format. Please try again."
            )

        if not isinstance(lessons, list):
            raise RuntimeError("The AI returned an invalid lessons list.")

        # An empty list is valid: it means this analysis found no new insight.
        cleaned_lessons = []
        seen_normalized = set()

        for lesson in lessons:
            if not isinstance(lesson, str) or not lesson.strip():
                continue

            cleaned = lesson.strip()
            normalized = " ".join(
                re.sub(r"[^a-z0-9]+", " ", cleaned.lower()).split()
            )
            if normalized and normalized not in seen_normalized:
                seen_normalized.add(normalized)
                cleaned_lessons.append(cleaned)

        return cleaned_lessons[:1]
