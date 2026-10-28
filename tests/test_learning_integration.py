
from agents import strategist, writer


def test_strategist_receives_approved_lessons(monkeypatch):
    captured = {}

    class FakeAIService:
        def generate_text(self, prompt):
            captured["prompt"] = prompt
            return (
                "ANGLE: Practical JVM example\n"
                "REASON: Apply the approved feedback"
            )

    monkeypatch.setattr(strategist, "AIService", FakeAIService)

    state = {
        "topic": "Java garbage collection",
        "brand_voice": "Clear and practical",
        "approved_lessons": [
            "Use practical examples and concise explanations."
        ],
        "audit_trail": [],
    }

    result = strategist.strategist_node(state)

    assert "Use practical examples and concise explanations." in captured["prompt"]
    assert result["strategist_angle"] == "Practical JVM example"
    assert any(
        "considered 1 approved learning lessons" in entry
        for entry in result["audit_trail"]
    )


def test_writer_receives_approved_lessons(monkeypatch):
    captured = {}

    class FakeAIService:
        def generate_text(self, prompt):
            captured["prompt"] = prompt
            return "A concise educational post with a practical example."

    monkeypatch.setattr(writer, "AIService", FakeAIService)

    state = {
        "topic": "Java garbage collection",
        "brand_voice": "Clear and practical",
        "approved_lessons": [
            "Use practical examples and concise explanations."
        ],
        "strategist_angle": "Explain garbage collection practically",
        "strategy_reason": "Make the topic easier to understand",
        "draft": "",
        "critique": "",
        "revision_count": 0,
        "audit_trail": [],
    }

    result = writer.writer_node(state)

    assert "Use practical examples and concise explanations." in captured["prompt"]
    assert result["draft"]
    assert any(
        "considered 1 approved learning lessons" in entry
        for entry in result["audit_trail"]
    )
