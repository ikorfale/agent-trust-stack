"""Recourse / promise ledger placeholders."""

from dataclasses import dataclass


@dataclass
class PromiseEvent:
    promise_id: str
    impact_tier: str
    timestamp: str
