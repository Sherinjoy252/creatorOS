
from graph.creator_graph import build_creator_graph
from services.ai_service import AIService
from services.linkedin_post_service import LinkedInPostService


def main():
    topic = input("Enter the LinkedIn post topic: ").strip()

    if not topic:
        print("Topic cannot be empty.")
        return

    brand_voice = input(
        "Describe the brand voice: "
    ).strip()

    if not brand_voice:
        brand_voice = "Clear, practical, educational and friendly"

    try:
        graph = build_creator_graph()

        initial_state = {
            "topic": topic,
            "brand_voice": brand_voice,
            "strategist_angle": "",
            "strategy_reason": "",
            "draft": "",
            "critique": "",
            "revision_count": 0,
            "max_revisions": 2,
            "approved": False,
            "audit_trail": [],
        }

        print("\nRunning CreatorOS...")
        result = graph.invoke(initial_state)

        post_service = LinkedInPostService(AIService())
        draft_path = post_service.save_draft(
            topic, 1, result["draft"]
        )

        print("\n=== CreatorOS Result ===")
        print(f"Angle: {result['strategist_angle']}")
        print(f"Reason: {result['strategy_reason']}")
        print(f"Approved: {result['approved']}")
        print(f"Revisions: {result['revision_count']}")
        print(f"\nDraft:\n{result['draft']}")

        print("\nAudit trail:")
        for event in result["audit_trail"]:
            print(f"- {event}")

        print(f"\nDraft saved to: {draft_path}")
        print("Nothing has been published to LinkedIn.")

    except Exception as exc:
        print(f"\nCreatorOS failed: {exc}")


if __name__ == "__main__":
    main()
