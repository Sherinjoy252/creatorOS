
from services.ai_service import AIService
from services.curriculum_service import CurriculumService
from services.linkedin_post_service import LinkedInPostService


def main():
    topic = input("Enter a topic to learn: ").strip()

    if not topic:
        print("Topic cannot be empty.")
        return

    ai_service = AIService()
    curriculum_service = CurriculumService(ai_service)
    post_service = LinkedInPostService(ai_service)

    try:
        print(f"\nGenerating a learning roadmap for: {topic}")

        roadmap = curriculum_service.create_roadmap(topic)

        print("\nRoadmap generated and saved.")
        print(roadmap)

        print("\nGenerating the first LinkedIn post...")

        # Initial version: generate the first lesson from the roadmap.
        lesson = roadmap.split("\n## Lesson 2:", 1)[0]

        post = post_service.create_post(topic, lesson)
        draft_path = post_service.save_draft(topic, 1, post)

        print("\n" + "=" * 50)
        print("LINKEDIN POST DRAFT")
        print("=" * 50)
        print(post)
        print("=" * 50)
        print(f"\nDraft saved to: {draft_path}")
        print("\nNothing has been published to LinkedIn.")

    except Exception as exc:
        print(f"\nThe workflow failed: {exc}")


if __name__ == "__main__":
    main()
