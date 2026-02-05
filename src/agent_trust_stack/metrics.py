"""Trust metrics placeholders (PDR, DI, MDR, ChainScore)."""

from dataclasses import dataclass


@dataclass
class TrustMetrics:
    pdr: float | None = None
    dependency_impact: float | None = None
    mdr: float | None = None
    chain_score: float | None = None

    def compute(self) -> "TrustMetrics":
        """Placeholder compute method."""
        return self
