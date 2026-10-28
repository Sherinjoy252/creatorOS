
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.ai_service import AIService
from models import GeneratedContent, PostPerformance


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

        performance_data = [
            {
                "impressions": item.impressions,
                "likes": item.likes,
                "comments": item.comments,
                "reposts": item.reposts,
                "data_source": item.data_source,
                "recorded_at": (
                    item.recorded_at.isoformat()
                    if item.recorded_at
                    else None
                ),
            }
            for item in snapshots
        ]

        prompt = f"""
You are the performance-learning analyst for CreatorOS.

Analyze this LinkedIn post and its performance history.

Topic: {content.topic}
Post:
{content.draft}

Performance snapshots (oldest first):
{json.dumps(performance_data, indent=2)}

Data notice:
{data_notice}

Instructions:
1. Treat snapshots as cumulative observations of one post, not independent posts.
2. Do not claim that the metrics prove causation.
3. If there is only one snapshot, say that trend evidence is limited.
4. Consider impressions, likes, comments, and reposts.
5. Do not invent missing metrics or audience demographics.
6. Produce 1 to 3 concise, specific lessons.
7. Return ONLY valid JSON in this format:
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

        if not isinstance(lessons, list) or not lessons:
            raise RuntimeError("The AI did not return any lessons.")

        cleaned_lessons = [
            lesson.strip()
            for lesson in lessons
            if isinstance(lesson, str) and lesson.strip()
        ]

        if not cleaned_lessons:
            raise RuntimeError("The AI returned no usable lessons.")

        return cleaned_lessons[:3]
