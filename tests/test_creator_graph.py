
import unittest
from unittest.mock import Mock, patch

from graph.creator_graph import build_creator_graph


class TestCreatorGraph(unittest.TestCase):

    @patch("agents.strategist.AIService")
    @patch("agents.writer.AIService")
    @patch("agents.editor.AIService")
    def test_graph_stops_at_maximum_revisions(
        self,
        mock_editor_service,
        mock_writer_service,
        mock_strategist_service,
    ):
        mock_ai = Mock()

        mock_strategist_service.return_value = mock_ai
        mock_writer_service.return_value = mock_ai
        mock_editor_service.return_value = mock_ai

        mock_ai.generate_text.side_effect = [
            "ANGLE: Java Streams\nREASON: Practical learning.",
            "Initial draft.",
            "VERDICT: REVISE\nFEEDBACK: Add an example.",
            "Revised draft one.",
            "VERDICT: REVISE\nFEEDBACK: Improve the explanation.",
            "Revised draft two.",
            "VERDICT: REVISE\nFEEDBACK: Still needs improvement.",
        ]

        graph = build_creator_graph()

        result = graph.invoke({
            "tenant_id": "test-tenant",
            "topic": "Java Streams",
            "brand_voice": "Simple and practical",
            "strategist_angle": "",
            "strategy_reason": "",
            "draft": "",
            "critique": "",
            "revision_count": 0,
            "max_revisions": 2,
            "approved": False,
            "audit_trail": [],
        })

        self.assertFalse(result["approved"])
        self.assertEqual(result["revision_count"], 2)
        self.assertEqual(mock_ai.generate_text.call_count, 7)
        self.assertIn(
            "Editor verdict: REVISE",
            result["audit_trail"],
        )


    @patch("agents.strategist.AIService")
    @patch("agents.writer.AIService")
    @patch("agents.editor.AIService")
    def test_writer_revises_after_editor_feedback(
        self,
        mock_editor_service,
        mock_writer_service,
        mock_strategist_service,
    ):
        mock_ai = Mock()

        mock_strategist_service.return_value = mock_ai
        mock_writer_service.return_value = mock_ai
        mock_editor_service.return_value = mock_ai

        mock_ai.generate_text.side_effect = [
            (
                "ANGLE: Practical Java Streams\n"
                "REASON: Helps learners process collections clearly."
            ),
            "Initial draft about Java Streams.",
            (
                "VERDICT: REVISE\n"
                "FEEDBACK: Add a practical code example."
            ),
            (
                "Revised post about Java Streams with a practical "
                "code example."
            ),
            (
                "VERDICT: APPROVE\n"
                "FEEDBACK: Clear explanation and useful code example."
            ),
        ]

        graph = build_creator_graph()

        result = graph.invoke({
            "tenant_id": "test-tenant",
            "topic": "Java Streams",
            "brand_voice": "Simple, practical and beginner-friendly",
            "strategist_angle": "",
            "strategy_reason": "",
            "draft": "",
            "critique": "",
            "revision_count": 0,
            "max_revisions": 2,
            "approved": False,
            "audit_trail": [],
        })

        self.assertTrue(result["approved"])
        self.assertEqual(result["revision_count"], 1)
        self.assertIn("practical", result["draft"])
        self.assertIn("Editor verdict: REVISE", result["audit_trail"])
        self.assertIn("Editor verdict: APPROVE", result["audit_trail"])
        self.assertEqual(mock_ai.generate_text.call_count, 5)


if __name__ == "__main__":
    unittest.main()
