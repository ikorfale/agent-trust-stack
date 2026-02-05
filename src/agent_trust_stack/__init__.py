"""
Agent Trust Stack v0 (metrics + provenance)

Post-quantum secure trust framework for AI agents with observable reliability
and email-native provenance.
"""

__version__ = "0.1.0-alpha"

# Core models
from .ledger import (
    Ledger,
    EmailLedgerEntry,
    PromiseEvent,
    DeliveryEvent,
    RecourseEvent,
    DependencyEvent,
    MemoryDistortionEvent,
    Event,
    EventType,
    DeliveryOutcome,
    ImpactTier,
    DistortionType,
    CorrectionStatus,
)

# Metrics
from .metrics import (
    TrustMetrics,
    PDRCalculation,
    PDRBreakdown,
    MetricsCalculator,
)

# Hygiene gates
from .hygiene import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    HygieneGate,
    EmailValidator,
    HashValidator,
    TimestampValidator,
    MetricsValidator,
    EventValidator,
    IntegrityChecker,
    HygieneGates,
)

# Policy-Driven Recourse
from .pdr import (
    RecourseAction,
    SeverityLevel,
    ImpactAssessment,
    RemediationAction,
    IncidentRecord,
    RecourseProcedure,
)

# Exports
__all__ = [
    # Core models
    "Ledger",
    "EmailLedgerEntry",
    "PromiseEvent",
    "DeliveryEvent",
    "RecourseEvent",
    "DependencyEvent",
    "MemoryDistortionEvent",
    "Event",
    "EventType",
    "DeliveryOutcome",
    "ImpactTier",
    "DistortionType",
    "CorrectionStatus",
    # Metrics
    "TrustMetrics",
    "PDRCalculation",
    "PDRBreakdown",
    "MetricsCalculator",
    # Hygiene
    "ValidationIssue",
    "ValidationResult",
    "ValidationSeverity",
    "HygieneGate",
    "EmailValidator",
    "HashValidator",
    "TimestampValidator",
    "MetricsValidator",
    "EventValidator",
    "IntegrityChecker",
    "HygieneGates",
    # Policy-Driven Recourse
    "RecourseAction",
    "SeverityLevel",
    "ImpactAssessment",
    "RemediationAction",
    "IncidentRecord",
    "RecourseProcedure",
]
