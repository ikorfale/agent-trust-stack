"""Identity continuity placeholders (non-crypto)."""

from dataclasses import dataclass


@dataclass
class IdentityContinuity:
    agent_id: str
    continuity_score: float | None = None
    reversal_events: int = 0
