from typing import TypedDict, NotRequired, Any


class CreatorState(TypedDict):
    tenant_id: str
    topic: str
    brand_voice: str
    approved_lessons: list[str]
    strategist_angle: str
    strategy_reason: str
    draft: str
    critique: str
    revision_count: int
    max_revisions: int
    approved: bool
    audit_trail: list[str]
    initial_evaluation: NotRequired[dict[str, Any]]
    revision_priorities: NotRequired[list[str]]
    final_evaluation: NotRequired[dict[str, Any]]
    evaluation_score_delta: NotRequired[int]
