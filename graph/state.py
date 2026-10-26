
from typing import TypedDict


class CreatorState(TypedDict):
    tenant_id: str
    topic: str
    brand_voice: str
    strategist_angle: str
    strategy_reason: str
    draft: str
    critique: str
    revision_count: int
    max_revisions: int
    approved: bool
    audit_trail: list[str]
