"""
Unit tests for Metrics module.
"""

import pytest
from datetime import datetime, timedelta

from agent_trust_stack.metrics import (
    TrustMetrics,
    PDRCalculation,
    MetricsCalculator,
)
from agent_trust_stack.ledger import (
    Ledger,
    PromiseEvent,
    DeliveryEvent,
    DeliveryOutcome,
    ImpactTier,
    RecourseEvent,
    DependencyEvent,
    MemoryDistortionEvent,
    DistortionType,
    CorrectionStatus,
)


class TestPDRCalculation:
    """Tests for PDRCalculation."""

    def test_default_params(self):
        """Test default PDR calculation parameters."""
        params = PDRCalculation()

        assert params.decay_curve == "exponential"
        assert params.decay_period_days == 90
        assert params.impact_weights["critical"] == 1.0
        assert params.impact_weights["high"] == 0.8
        assert params.impact_weights["medium"] == 0.5
        assert params.impact_weights["low"] == 0.2
        assert params.recourse_weight_factor == 0.5

    def test_custom_params(self):
        """Test custom PDR calculation parameters."""
        custom_weights = {
            "critical": 1.0,
            "high": 0.9,
            "medium": 0.7,
            "low": 0.4,
        }

        params = PDRCalculation(
            decay_curve="linear",
            decay_period_days=60,
            impact_weights=custom_weights,
            recourse_weight_factor=0.7,
        )

        assert params.decay_curve == "linear"
        assert params.decay_period_days == 60
        assert params.impact_weights == custom_weights
        assert params.recourse_weight_factor == 0.7


class TestMetricsCalculator:
    """Tests for MetricsCalculator."""

    def test_calculate_pdr_perfect(self):
        """Test PDR calculation with perfect delivery."""
        ledger = Ledger()
        calculator = MetricsCalculator(ledger)

        now = datetime.utcnow()

        # Create promises
        promise1 = PromiseEvent.create(
            agent_id="did:ats:agent1",
            promise_text="Promise 1",
            impact_tier=ImpactTier.HIGH,
            timestamp=now - timedelta(days=1),
        )

        promise2 = PromiseEvent.create(
            agent_id="did:ats:agent1",
            promise_text="Promise 2",
            impact_tier=ImpactTier.MEDIUM,
            timestamp=now - timedelta(days=2),
        )

        # Create successful deliveries
        delivery1 = DeliveryEvent.create(
            promise_id=promise1.id,
            outcome=DeliveryOutcome.DELIVERED,
            timestamp=now - timedelta(hours=20),
        )

        delivery2 = DeliveryEvent.create(
            promise_id=promise2.id,
            outcome=DeliveryOutcome.DELIVERED,
            timestamp=now - timedelta(days=1, hours=20),
        )

        ledger.add_promise(promise1)
        ledger.add_promise(promise2)
        ledger.add_delivery(delivery1)
        ledger.add_delivery(delivery2)

        # Calculate PDR
        start = now - timedelta(days=30)
        end = now
        pdr = calculator.compute_pdr("did:ats:agent1", start, end)

        # Should be 1.0 (perfect delivery)
        assert pdr == pytest.approx(1.0, abs=0.01)

    def test_calculate_pdr_mixed(self):
        """Test PDR calculation with mixed outcomes."""
        ledger = Ledger()
        calculator = MetricsCalculator(ledger)

        now = datetime.utcnow()

        # Create promises
        promise1 = PromiseEvent.create(
            agent_id="did:ats:agent1",
            promise_text="Promise 1",
            impact_tier=ImpactTier.HIGH,
            timestamp=now - timedelta(days=1),
        )

        promise2 = PromiseEvent.create(
            agent_id="did:ats:agent1",
            promise_text="Promise 2",
            impact_tier=ImpactTier.HIGH,
            timestamp=now - timedelta(days=1),
        )

        # Mixed outcomes
        delivery1 = DeliveryEvent.create(
            promise_id=promise1.id,
            outcome=DeliveryOutcome.DELIVERED,
            timestamp=now - timedelta(hours=20),
        )

        delivery2 = DeliveryEvent.create(
            promise_id=promise2.id,
            outcome=DeliveryOutcome.FAILED,
            timestamp=now - timedelta(hours=20),
        )

        ledger.add_promise(promise1)
        ledger.add_promise(promise2)
        ledger.add_delivery(delivery1)
        ledger.add_delivery(delivery2)

        # Calculate PDR
        start = now - timedelta(days=30)
        end = now
        pdr = calculator.compute_pdr("did:ats:agent1", start, end)

        # Should be 0.5 (50% delivery rate)
        assert pdr == pytest.approx(0.5, abs=0.01)

    def test_calculate_pdr_with_recourse(self):
        """Test PDR calculation with recourse events."""
        ledger = Ledger()
        calculator = MetricsCalculator(ledger)

        now = datetime.utcnow()

        # Create promise
        promise = PromiseEvent.create(
            agent_id="did:ats:agent1",
            promise_text="Promise 1",
            impact_tier=ImpactTier.HIGH,
            timestamp=now - timedelta(days=1),
        )

        # Failed delivery
        delivery = DeliveryEvent.create(
            promise_id=promise.id,
            outcome=DeliveryOutcome.FAILED,
            timestamp=now - timedelta(hours=20),
        )

        # Recourse event (repair)
        recourse = RecourseEvent.create(
            promise_id=promise.id,
            action="repair",
            resolution="partially_resolved",
        )

        ledger.add_promise(promise)
        ledger.add_delivery(delivery)
        ledger.add_recourse(recourse)

        # Calculate PDR
        start = now - timedelta(days=30)
        end = now
        pdr = calculator.compute_pdr("did:ats:agent1", start, end)

        # Recourse should reduce but not eliminate the penalty
        # Without recourse: 0.0
        # With recourse: should be > 0 but < 0.5
        assert 0.0 < pdr < 0.5

    def test_calculate_pdr_with_impact_tiers(self):
        """Test PDR calculation with different impact tiers."""
        ledger = Ledger()
        calculator = MetricsCalculator(ledger)

        now = datetime.utcnow()

        # Critical promise delivered
        critical_promise = PromiseEvent.create(
            agent_id="did:ats:agent1",
            promise_text="Critical promise",
            impact_tier=ImpactTier.CRITICAL,
            timestamp=now - timedelta(days=1),
        )

        critical_delivery = DeliveryEvent.create(
            promise_id=critical_promise.id,
            outcome=DeliveryOutcome.DELIVERED,
        )

        # Low promise failed
        low_promise = PromiseEvent.create(
            agent_id="did:ats:agent1",
            promise_text="Low priority promise",
            impact_tier=ImpactTier.LOW,
            timestamp=now - timedelta(days=1),
        )

        low_delivery = DeliveryEvent.create(
            promise_id=low_promise.id,
            outcome=DeliveryOutcome.FAILED,
        )

        ledger.add_promise(critical_promise)
        ledger.add_promise(low_promise)
        ledger.add_delivery(critical_delivery)
        ledger.add_delivery(low_delivery)

        # Calculate PDR
        start = now - timedelta(days=30)
        end = now
        pdr = calculator.compute_pdr("did:ats:agent1", start, end)

        # Should be > 0.5 because critical was delivered (higher weight)
        assert pdr > 0.5

    def test_calculate_dependency_impact(self):
        """Test dependency impact calculation."""
        ledger = Ledger()
        calculator = MetricsCalculator(ledger)

        now = datetime.utcnow()

        # Add dependency events
        dep1 = DependencyEvent.create(
            workflow_id="workflow-1",
            dependency_id="dep-1",
            workflow_weight=0.8,
            failure_rate=0.2,
            fallback_score=0.9,  # Good fallback
        )

        dep2 = DependencyEvent.create(
            workflow_id="workflow-1",
            dependency_id="dep-2",
            workflow_weight=0.6,
            failure_rate=0.5,
            fallback_score=0.1,  # Poor fallback
        )

        ledger.add_dependency(dep1)
        ledger.add_dependency(dep2)

        # Calculate DI
        start = now - timedelta(days=30)
        end = now
        di = calculator.compute_dependency_impact(start, end)

        # DI should reflect impact of both dependencies
        # dep1: 0.8 * 0.2 * (1 - 0.9) = 0.8 * 0.2 * 0.1 = 0.016
        # dep2: 0.6 * 0.5 * (1 - 0.1) = 0.6 * 0.5 * 0.9 = 0.27
        # Total weight: 0.8 + 0.6 = 1.4
        # DI: (0.016 + 0.27) / 1.4 = 0.286 / 1.4 = 0.204

        assert 0.19 < di < 0.21

    def test_calculate_memory_distortion_rate(self):
        """Test memory distortion rate calculation."""
        ledger = Ledger()
        calculator = MetricsCalculator(ledger)

        now = datetime.utcnow()

        # Add promises (interactions)
        for i in range(10):
            promise = PromiseEvent.create(
                agent_id="did:ats:agent1",
                promise_text=f"Promise {i}",
                impact_tier=ImpactTier.MEDIUM,
                timestamp=now - timedelta(days=i),
            )
            ledger.add_promise(promise)

        # Add some distortions
        distortion1 = MemoryDistortionEvent.create(
            session_id="session-1",
            distortion_type=DistortionType.HALLUCINATION,
            correction_status=CorrectionStatus.CORRECTED,
        )

        distortion2 = MemoryDistortionEvent.create(
            session_id="session-2",
            distortion_type=DistortionType.CONFABULATION,
            correction_status=CorrectionStatus.UNCORRECTED,
        )

        ledger.add_memory_distortion(distortion1)
        ledger.add_memory_distortion(distortion2)

        # Calculate MDR
        start = now - timedelta(days=30)
        end = now
        mdr, recovery = calculator.compute_memory_distortion_rate(start, end)

        # MDR = 2 distortions / 10 interactions = 0.2
        assert mdr == pytest.approx(0.2, abs=0.01)

        # Recovery = 1 corrected / 2 total = 0.5
        assert recovery == pytest.approx(0.5, abs=0.01)

    def test_compute_all_metrics(self):
        """Test computing all metrics together."""
        ledger = Ledger()
        calculator = MetricsCalculator(ledger)

        now = datetime.utcnow()

        # Add some sample data
        promise = PromiseEvent.create(
            agent_id="did:ats:agent1",
            promise_text="Test promise",
            impact_tier=ImpactTier.HIGH,
        )

        delivery = DeliveryEvent.create(
            promise_id=promise.id,
            outcome=DeliveryOutcome.DELIVERED,
        )

        dependency = DependencyEvent.create(
            workflow_id="workflow-1",
            dependency_id="dep-1",
            workflow_weight=0.5,
            failure_rate=0.1,
            fallback_score=0.8,
        )

        ledger.add_promise(promise)
        ledger.add_delivery(delivery)
        ledger.add_dependency(dependency)

        # Compute all metrics
        metrics = calculator.compute_all(
            agent_id="did:ats:agent1",
            time_window_days=30,
        )

        # Check that all metrics are set
        assert metrics.pdr is not None
        assert metrics.dependency_impact is not None
        assert metrics.mdr is not None
        assert metrics.recovery_score is not None
        assert metrics.computed_at is not None

        # Check ranges
        assert 0.0 <= metrics.pdr <= 1.0
        assert 0.0 <= metrics.dependency_impact <= 1.0
        assert 0.0 <= metrics.mdr <= 1.0
        assert 0.0 <= metrics.recovery_score <= 1.0

    def test_chain_score(self):
        """Test attestation chain score calculation."""
        ledger = Ledger()
        calculator = MetricsCalculator(ledger)

        now = datetime.utcnow()

        # Create email chain
        entry1 = EmailLedgerEntry.create(
            message_id="msg1@example.com",
            from_addr="a@trusted.com",
            to_addr="b@example.com",
            timestamp=now - timedelta(hours=2),
            signer="sel1.trusted.com",
            body="Message 1",
            headers={"Subject": "Test"},
        )

        entry2 = EmailLedgerEntry.create(
            message_id="msg2@example.com",
            from_addr="b@example.com",
            to_addr="a@trusted.com",
            timestamp=now - timedelta(hours=1),
            signer="sel2.example.com",
            body="Message 2",
            headers={"Subject": "Re: Test"},
            in_reply_to="msg1@example.com",
            references=["msg1@example.com"],
        )

        ledger.add_email_entry(entry1)
        ledger.add_email_entry(entry2)

        # Calculate chain score
        score = calculator.compute_chain_score("msg2@example.com")

        # Score should be between 0 and 1
        assert 0.0 <= score <= 1.0

        # With a trusted signer, score should be reasonable
        assert score > 0.3


# Import EmailLedgerEntry for chain score test
from agent_trust_stack.ledger import EmailLedgerEntry
