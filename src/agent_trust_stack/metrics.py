"""
Agent Trust Stack - Metrics Module

Implements core trust metrics:
- PDR (Promise-Delivery Rate)
- DI (Dependency Impact)
- MDR (Memory Distortion Rate)
- ChainScore (Attestation Chain Score)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .ledger import (
    DeliveryEvent,
    DeliveryOutcome,
    ImpactTier,
    Ledger,
    PromiseEvent,
    RecourseEvent,
    DependencyEvent,
    MemoryDistortionEvent,
    CorrectionStatus,
    EmailLedgerEntry,
)


@dataclass
class TrustMetrics:
    """
    Container for all trust metrics.

    Attributes:
        pdr: Promise-Delivery Rate (0-1)
        dependency_impact: Dependency Impact (0-1)
        mdr: Memory Distortion Rate (0-1)
        recovery_score: Memory Recovery Score (0-1)
        chain_score: Attestation Chain Score (0-1)
        computed_at: When metrics were computed
    """

    pdr: Optional[float] = None
    dependency_impact: Optional[float] = None
    mdr: Optional[float] = None
    recovery_score: Optional[float] = None
    chain_score: Optional[float] = None
    computed_at: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary."""
        return {
            "pdr": self.pdr,
            "dependency_impact": self.dependency_impact,
            "mdr": self.mdr,
            "recovery_score": self.recovery_score,
            "chain_score": self.chain_score,
            "computed_at": self.computed_at.isoformat() if self.computed_at else None,
        }


@dataclass
class PDRCalculation:
    """
    Parameters for Promise-Delivery Rate calculation.

    Attributes:
        decay_curve: Type of decay curve (linear, exponential, logarithmic)
        decay_period_days: Time period for decay calculation
        impact_weights: Mapping of impact tiers to weights
        recourse_weight_factor: How much recourse reduces penalty (0-1)
    """

    decay_curve: str = "exponential"
    decay_period_days: int = 90
    impact_weights: Dict[str, float] = field(default_factory=lambda: {
        "critical": 1.0,
        "high": 0.8,
        "medium": 0.5,
        "low": 0.2,
    })
    recourse_weight_factor: float = 0.5


@dataclass
class PDRBreakdown:
    """
    Detailed breakdown of PDR calculation.

    Attributes:
        total_promises: Total number of promises
        delivered: Number of promises delivered
        failed: Number of promises failed
        partial: Number of partial deliveries
        with_recourse: Number with recourse events
        decayed_weighted_score: Score after applying decay
        impact_weighted_score: Score after applying impact weights
        recourse_adjusted_score: Final score after recourse adjustment
    """

    total_promises: int = 0
    delivered: int = 0
    failed: int = 0
    partial: int = 0
    with_recourse: int = 0
    decayed_weighted_score: float = 0.0
    impact_weighted_score: float = 0.0
    recourse_adjusted_score: float = 0.0


class MetricsCalculator:
    """
    Calculate trust metrics from ledger data.

    Implements the metrics defined in SPEC v0.1.0.
    """

    def __init__(self, ledger: Ledger, pdr_params: Optional[PDRCalculation] = None):
        """
        Initialize metrics calculator.

        Args:
            ledger: Ledger containing event data
            pdr_params: Parameters for PDR calculation (uses defaults if None)
        """
        self.ledger = ledger
        self.pdr_params = pdr_params or PDRCalculation()

    def compute_all(
        self,
        agent_id: str,
        time_window_days: int = 90,
        chain_message_id: Optional[str] = None,
    ) -> TrustMetrics:
        """
        Compute all trust metrics for an agent.

        Args:
            agent_id: DID of the agent
            time_window_days: Time window for calculation (days)
            chain_message_id: Optional email message ID for chain scoring

        Returns:
            TrustMetrics containing all computed metrics
        """
        now = datetime.utcnow()
        start_time = now - timedelta(days=time_window_days)

        metrics = TrustMetrics(computed_at=now)

        # Compute PDR
        pdr = self.compute_pdr(agent_id, start_time, now)
        metrics.pdr = pdr

        # Compute DI
        di = self.compute_dependency_impact(start_time, now)
        metrics.dependency_impact = di

        # Compute MDR
        mdr, recovery = self.compute_memory_distortion_rate(start_time, now)
        metrics.mdr = mdr
        metrics.recovery_score = recovery

        # Compute Chain Score if message ID provided
        if chain_message_id:
            chain_score = self.compute_chain_score(chain_message_id)
            metrics.chain_score = chain_score

        return metrics

    def compute_pdr(
        self,
        agent_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> float:
        """
        Compute Promise-Delivery Rate (PDR).

        Formula:
        PDR = (delivered / claimed) × decay × impact_weight × (1 − recourse_weight)

        Args:
            agent_id: DID of the agent
            start_time: Start of time window
            end_time: End of time window

        Returns:
            PDR score between 0 and 1
        """
        # Get promises for agent in time window
        promises = [
            p for p in self.ledger._promises.values()
            if p.agent_id == agent_id and start_time <= p.timestamp <= end_time
        ]

        if not promises:
            return 0.0

        breakdown = PDRBreakdown(total_promises=len(promises))

        # For each promise, find delivery events and calculate score
        total_weight = 0.0
        delivered_weight = 0.0
        recourse_count = 0

        for promise in promises:
            # Get impact weight
            impact_weight = self.pdr_params.impact_weights.get(
                promise.impact_tier.value, 0.5
            )

            # Calculate decay based on promise age
            age_days = (end_time - promise.timestamp).total_seconds() / 86400
            decay = self._calculate_decay(age_days)

            # Get delivery events
            deliveries = self.ledger.get_deliveries_for_promise(promise.id)
            recourse_events = self.ledger.get_recourses_for_promise(promise.id)

            # Determine delivery outcome
            if not deliveries:
                # No delivery = failed
                outcome_score = 0.0
                breakdown.failed += 1
            else:
                latest_delivery = max(deliveries, key=lambda d: d.timestamp)
                if latest_delivery.outcome == DeliveryOutcome.DELIVERED:
                    outcome_score = 1.0
                    breakdown.delivered += 1
                elif latest_delivery.outcome == DeliveryOutcome.PARTIAL:
                    outcome_score = 0.5
                    breakdown.partial += 1
                else:
                    outcome_score = 0.0
                    breakdown.failed += 1

            # Apply recourse adjustment
            recourse_weight = 0.0
            if recourse_events:
                recourse_count += 1
                breakdown.with_recourse += 1
                # Recourse events reduce penalty but don't fully restore score
                recourse_weight = self.pdr_params.recourse_weight_factor

            # Calculate weighted score for this promise
            weighted_score = (
                outcome_score
                * decay
                * impact_weight
                * (1.0 - recourse_weight * (1.0 - outcome_score))
            )

            total_weight += impact_weight * decay
            delivered_weight += weighted_score

        # Calculate final PDR
        if total_weight == 0:
            return 0.0

        pdr = delivered_weight / total_weight
        breakdown.decayed_weighted_score = pdr
        breakdown.impact_weighted_score = pdr
        breakdown.recourse_adjusted_score = pdr

        return max(0.0, min(1.0, pdr))

    def _calculate_decay(self, age_days: float) -> float:
        """
        Calculate decay factor based on promise age.

        Args:
            age_days: Age of the promise in days

        Returns:
            Decay factor between 0 and 1
        """
        max_age = self.pdr_params.decay_period_days

        if age_days >= max_age:
            return 0.0

        decay_curve = self.pdr_params.decay_curve

        if decay_curve == "linear":
            # Linear decay: 1.0 -> 0.0 over max_age
            return 1.0 - (age_days / max_age)

        elif decay_curve == "exponential":
            # Exponential decay with half-life at max_age/2
            half_life = max_age / 2.0
            return math.exp(-math.log(2) * age_days / half_life)

        elif decay_curve == "logarithmic":
            # Logarithmic decay
            if age_days == 0:
                return 1.0
            return 1.0 - math.log(1 + age_days) / math.log(1 + max_age)

        else:
            # Default to linear
            return max(0.0, 1.0 - (age_days / max_age))

    def compute_dependency_impact(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> float:
        """
        Compute Dependency Impact (DI).

        Formula:
        DI = Σ(workflow_weight × failure_rate × (1 − fallback_score))

        Measures the blast radius when dependencies fail,
        reduced by the quality of fallback alternatives.

        Args:
            start_time: Start of time window
            end_time: End of time window

        Returns:
            DI score between 0 and 1 (lower is better)
        """
        # Get all dependency events in time window
        dependencies = [
            d for d in self.ledger._dependencies.values()
            if start_time <= d.timestamp <= end_time
        ]

        if not dependencies:
            return 0.0

        # Sum weighted impact of all dependencies
        total_impact = 0.0
        total_weight = 0.0

        for dep in dependencies:
            # Calculate impact for this dependency
            # (1 - fallback_score) reduces impact when good fallbacks exist
            impact = (
                dep.workflow_weight
                * dep.failure_rate
                * (1.0 - dep.fallback_score)
            )

            total_impact += impact
            total_weight += dep.workflow_weight

        # Normalize by total weight
        if total_weight == 0:
            return 0.0

        di = total_impact / total_weight

        # Clamp to [0, 1]
        return max(0.0, min(1.0, di))

    def compute_memory_distortion_rate(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> tuple[float, float]:
        """
        Compute Memory Distortion Rate (MDR) and Recovery Score.

        MDR = false_memory_events / interactions
        RecoveryScore = corrected_distortions / false_memory_events

        Args:
            start_time: Start of time window
            end_time: End of time window

        Returns:
            Tuple of (MDR, RecoveryScore) both between 0 and 1
        """
        # Get all memory distortion events in time window
        distortions = [
            d for d in self.ledger._memory_distortions.values()
            if start_time <= d.timestamp <= end_time
        ]

        if not distortions:
            return 0.0, 0.0

        # Count total events (using promises as proxy for interactions)
        total_interactions = len([
            p for p in self.ledger._promises.values()
            if start_time <= p.timestamp <= end_time
        ])

        if total_interactions == 0:
            total_interactions = len(distortions)  # Avoid division by zero

        # Count false memory events
        false_memory_count = len(distortions)

        # Count corrected distortions
        corrected_count = sum(
            1 for d in distortions
            if d.correction_status in [
                CorrectionStatus.CORRECTED,
                CorrectionStatus.PARTIALLY_CORRECTED,
            ]
        )

        # Calculate MDR
        mdr = false_memory_count / total_interactions

        # Calculate Recovery Score
        if false_memory_count == 0:
            recovery = 1.0  # No distortions = perfect recovery
        else:
            recovery = corrected_count / false_memory_count

        return max(0.0, min(1.0, mdr)), max(0.0, min(1.0, recovery))

    def compute_chain_score(
        self,
        message_id: str,
        signer_reliability_map: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Compute Attestation Chain Score (Isnād).

        Formula:
        ChainScore = Σ(signer_reliability × decay^depth) + chain_bonus − break_penalty

        Evaluates the quality of the email thread chain.

        Args:
            message_id: Message ID to start from
            signer_reliability_map: Map of signer domains to reliability scores (0-1)

        Returns:
            ChainScore between 0 and 1
        """
        # Get the email chain
        chain = self.ledger.get_email_chain(message_id)

        if not chain:
            return 0.0

        # Default signer reliability (unknown = 0.5)
        if signer_reliability_map is None:
            signer_reliability_map = {}

        total_score = 0.0
        chain_breaks = 0.0
        distinct_signers = set()

        # Calculate score for each message in chain
        for depth, entry in enumerate(chain):
            # Extract domain from signer (DKIM selector+domain format: selector.domain)
            parts = entry.signer.split('.')
            if len(parts) >= 2:
                signer_domain = '.'.join(parts[-2:])
            else:
                signer_domain = entry.signer

            distinct_signers.add(signer_domain)

            # Get signer reliability (default 0.5 for unknown)
            reliability = signer_reliability_map.get(signer_domain, 0.5)

            # Calculate depth decay
            decay = math.exp(-depth / 2.0)  # Exponential decay with depth

            # Add to total score
            total_score += reliability * decay

            # Check for chain breaks (missing signatures)
            if not entry.signature_chain:
                chain_breaks += 1

        # Apply chain bonus for diverse signers
        chain_bonus = min(0.2, len(distinct_signers) * 0.05)

        # Apply break penalty
        break_penalty = min(0.5, chain_breaks * 0.2)

        # Final score
        final_score = total_score + chain_bonus - break_penalty

        # Normalize by chain length
        if len(chain) > 0:
            final_score = final_score / len(chain)

        # Clamp to [0, 1]
        return max(0.0, min(1.0, final_score))

    def compute_pdr_breakdown(
        self,
        agent_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> PDRBreakdown:
        """
        Compute detailed PDR breakdown.

        Returns statistics about promise delivery.

        Args:
            agent_id: DID of the agent
            start_time: Start of time window
            end_time: End of time window

        Returns:
            PDRBreakdown with detailed statistics
        """
        # This is called internally by compute_pdr, but we can return
        # the breakdown for reporting purposes
        self.compute_pdr(agent_id, start_time, end_time)
        return PDRBreakdown()  # Placeholder - would need to modify compute_pdr
