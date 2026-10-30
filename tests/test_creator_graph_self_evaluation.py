1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
import unittest
from unittest.mock import Mock, patch

from graph.creator_graph import build_creator_graph


def evaluation_json(score=80):
    import json
    weights = {"technical_accuracy":25,"practical_value":20,"brand_voice_alignment":15,"readability":15,"conciseness":10,"topic_relevance":10,"engagement_potential":5}
    return json.dumps({"criteria": {k: {"score": round(v * score / 100, 2), "feedback": "Checked."} for k,v in weights.items()}, "strengths": ["Clear example"], "improvements": ["Add detail"], "summary": "Good educational post."})


class TestCreatorGraphSelfEvaluation(unittest.TestCase):
    @patch("agents.strategist.AIService")
    @patch("agents.writer.AIService")
    @patch("agents.editor.AIService")
    @patch("agents.evaluator.AIService")
    def test_initial_and_final_scores_are_recorded(self, evaluator_service, editor_service, writer_service, strategist_service):
        strategist_service.return_value.generate_text.return_value = "ANGLE: Practical example\nREASON: Makes it clear."
        writer_service.return_value.generate_text.side_effect = ["Initial draft.", "Revised draft with example."]
        editor_service.return_value.generate_text.side_effect = ["VERDICT: REVISE\nFEEDBACK: Add a practical example.", "VERDICT: APPROVE\nFEEDBACK: Meets requirements."]
        evaluator_service.return_value.generate_text.side_effect = [evaluation_json(60), evaluation_json(90)]

        result = build_creator_graph().invoke({
            "tenant_id":"test", "topic":"Java Streams", "brand_voice":"Clear and practical",
            "approved_lessons":[], "strategist_angle":"", "strategy_reason":"", "draft":"",
            "critique":"", "revision_count":0, "max_revisions":2, "approved":False, "audit_trail":[]
        })
        self.assertEqual(result["initial_evaluation"]["score"], 60)
        self.assertEqual(result["final_evaluation"]["score"], 90)
        self.assertEqual(result["evaluation_score_delta"], 30)
        self.assertEqual(evaluator_service.return_value.generate_text.call_count, 2)
        self.assertTrue(result["approved"])

    def test_evaluation_parser_rejects_invalid_scores(self):
        from agents.evaluator import _parse_evaluation
        import json
        payload = json.loads(evaluation_json())
        payload["criteria"]["technical_accuracy"]["score"] = 26
        with self.assertRaises(ValueError):
            _parse_evaluation(json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
