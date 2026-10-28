
from graph.state import CreatorState
from services.ai_service import AIService


def writer_node(state: CreatorState) -> dict:
    ai = AIService()

    approved_lessons = state.get("approved_lessons", [])

    lessons_context = (
        "\n".join(f"- {lesson}" for lesson in approved_lessons)
        if approved_lessons
        else "No approved performance lessons are available yet."
    )

    common_instructions = f"""
Create an educational LinkedIn post about: {state['topic']}

Chosen angle: {state['strategist_angle']}
Strategic rationale: {state['strategy_reason']}

Brand voice profile:
{state['brand_voice']}

Lessons learned from previous post performance:
{lessons_context}

Use relevant approved lessons to improve the post's structure,
clarity, examples, and engagement potential.

Apply these lessons naturally. Do not force irrelevant advice
into the post or claim that engagement improvements are guaranteed.

Requirements:
- Follow the supplied brand voice instead of generic AI writing habits.
- Explain the topic accurately and use a practical example when useful.
- Prefer 150-300 words unless the topic needs more detail.
- Use clear paragraphs and purposeful Markdown.
- Avoid repetitive explanations, duplicate conclusions, and filler.
- Avoid excessive emojis, clickbait, and generic motivational phrases.
- End with one clear conclusion.
- Return only the LinkedIn post, without commentary about your task.
"""

    if state["critique"]:
        task = f"""
Revise the previous post using the editor's feedback.

Treat each specific correction as a requirement unless it conflicts
with technical accuracy.

Editor feedback:
{state['critique']}

Previous draft:
{state['draft']}

{common_instructions}

Make meaningful improvements. Preserve correct information and useful
examples, but rewrite weak or repetitive sections rather than merely
changing a few words.

Ensure all code examples are technically correct and demonstrate
what the explanation claims. Prefer try-with-resources for Java
resource management when appropriate. Avoid repetitive headings,
multiple conclusions, excessive emojis, and repeated calls to action.
Follow the supplied brand voice rather than using generic
motivational language.

Ensure the content and examples directly address the requested topic.
"""
    else:
        task = common_instructions

    draft = ai.generate_text(task).strip()

    if not draft:
        raise ValueError("Writer returned an empty draft.")

    revision_count = state["revision_count"] + (
        1 if state["critique"] else 0
    )

    action = (
        "revised the draft"
        if state["critique"]
        else "created initial draft"
    )

    return {
        "draft": draft,
        "revision_count": revision_count,
        "audit_trail": state["audit_trail"] + [
            f"Writer {action} ({len(draft)} characters).",
            f"Writer considered {len(approved_lessons)} approved learning lessons.",
        ],
    }
