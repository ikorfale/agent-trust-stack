"""Attestation chain placeholders."""

from dataclasses import dataclass


@dataclass
class Attestation:
    issuer: str
    subject: str
    reliability: float
    depth: int
