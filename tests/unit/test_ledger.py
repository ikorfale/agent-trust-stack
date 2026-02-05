"""
Unit tests for Ledger module.
"""

import pytest
from datetime import datetime, timedelta

from agent_trust_stack.ledger import (
    Ledger,
    EmailLedgerEntry,
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


class TestEmailLedgerEntry:
    """Tests for EmailLedgerEntry."""

    def test_create_entry(self):
        """Test creating an email ledger entry."""
        entry = EmailLedgerEntry.create(
            message_id="test@example.com",
            from_addr="sender@example.com",
            to_addr="recipient@example.com",
            timestamp=datetime.utcnow(),
            signer="selector1.example.com",
            body="Test email body",
            headers={"Subject": "Test", "Message-ID": "test@example.com"},
        )

        assert entry.message_id == "test@example.com"
        assert entry.from_addr == "sender@example.com"
        assert entry.to_addr == "recipient@example.com"
        assert entry.signer == "selector1.example.com"
        assert len(entry.body_hash) == 64  # SHA-256 hex
        assert len(entry.headers_hash) == 64  # SHA-256 hex

    def test_create_with_thread(self):
        """Test creating an entry with thread information."""
        entry = EmailLedgerEntry.create(
            message_id="msg2@example.com",
            from_addr="sender@example.com",
            to_addr="recipient@example.com",
            timestamp=datetime.utcnow(),
            signer="selector1.example.com",
            body="Reply body",
            headers={"Subject": "Re: Test"},
            in_reply_to="msg1@example.com",
            references=["msg1@example.com"],
        )

        assert entry.in_reply_to == "msg1@example.com"
        assert "msg1@example.com" in entry.references

    def test_verify_integrity_valid(self):
        """Test verifying integrity with valid data."""
        body = "Test body"
        headers = {"Subject": "Test"}

        entry = EmailLedgerEntry.create(
            message_id="test@example.com",
            from_addr="sender@example.com",
            to_addr="recipient@example.com",
            timestamp=datetime.utcnow(),
            signer="selector1.example.com",
            body=body,
            headers=headers,
        )

        assert entry.verify_integrity(body, headers) is True

    def test_verify_integrity_invalid_body(self):
        """Test verifying integrity with invalid body."""
        body = "Test body"
        headers = {"Subject": "Test"}

        entry = EmailLedgerEntry.create(
            message_id="test@example.com",
            from_addr="sender@example.com",
            to_addr="recipient@example.com",
            timestamp=datetime.utcnow(),
            signer="selector1.example.com",
            body=body,
            headers=headers,
        )

        assert entry.verify_integrity("Wrong body", headers) is False

    def test_extend_chain(self):
        """Test extending signature chain."""
        entry = EmailLedgerEntry.create(
            message_id="test@example.com",
            from_addr="sender@example.com",
            to_addr="recipient@example.com",
            timestamp=datetime.utcnow(),
            signer="selector1.example.com",
            body="Test",
            headers={"Subject": "Test"},
        )

        assert len(entry.signature_chain) == 0

        entry.extend_chain("sig1")
        entry.extend_chain("sig2")

        assert len(entry.signature_chain) == 2
        assert entry.signature_chain[0] == "sig1"
        assert entry.signature_chain[1] == "sig2"


class TestPromiseEvent:
    """Tests for PromiseEvent."""

    def test_create_promise(self):
        """Test creating a promise event."""
        promise = PromiseEvent.create(
            agent_id="did:ats:agent123",
            promise_text="I will deliver the report",
            impact_tier=ImpactTier.HIGH,
        )

        assert promise.agent_id == "did:ats:agent123"
        assert promise.promise_text == "I will deliver the report"
        assert promise.impact_tier == ImpactTier.HIGH
        assert promise.id.startswith("promise-")

    def test_to_dict(self):
        """Test converting promise to dictionary."""
        promise = PromiseEvent.create(
            agent_id="did:ats:agent123",
            promise_text="Test promise",
            impact_tier=ImpactTier.MEDIUM,
        )

        data = promise.to_dict()

        assert data["agent_id"] == "did:ats:agent123"
        assert data["promise_text"] == "Test promise"
        assert data["impact_tier"] == "medium"
        assert data["type"] == "promise"


class TestDeliveryEvent:
    """Tests for DeliveryEvent."""

    def test_create_delivery(self):
        """Test creating a delivery event."""
        delivery = DeliveryEvent.create(
            promise_id="promise-abc123",
            outcome=DeliveryOutcome.DELIVERED,
        )

        assert delivery.promise_id == "promise-abc123"
        assert delivery.outcome == DeliveryOutcome.DELIVERED
        assert delivery.id.startswith("delivery-")

    def test_create_partial_delivery(self):
        """Test creating a partial delivery event."""
        delivery = DeliveryEvent.create(
            promise_id="promise-abc123",
            outcome=DeliveryOutcome.PARTIAL,
            delivered_amount=50.0,
            expected_amount=100.0,
        )

        assert delivery.outcome == DeliveryOutcome.PARTIAL
        assert delivery.delivered_amount == 50.0
        assert delivery.expected_amount == 100.0


class TestRecourseEvent:
    """Tests for RecourseEvent."""

    def test_create_recourse(self):
        """Test creating a recourse event."""
        recourse = RecourseEvent.create(
            promise_id="promise-abc123",
            action="rollback",
            resolution="resolved",
        )

        assert recourse.promise_id == "promise-abc123"
        assert recourse.action == "rollback"
        assert recourse.resolution == "resolved"
        assert recourse.id.startswith("recourse-")


class TestDependencyEvent:
    """Tests for DependencyEvent."""

    def test_create_dependency(self):
        """Test creating a dependency event."""
        dependency = DependencyEvent.create(
            workflow_id="workflow-1",
            dependency_id="dep-1",
            workflow_weight=0.8,
            failure_rate=0.1,
            fallback_score=0.9,
        )

        assert dependency.workflow_id == "workflow-1"
        assert dependency.dependency_id == "dep-1"
        assert dependency.workflow_weight == 0.8
        assert dependency.failure_rate == 0.1
        assert dependency.fallback_score == 0.9


class TestMemoryDistortionEvent:
    """Tests for MemoryDistortionEvent."""

    def test_create_distortion(self):
        """Test creating a memory distortion event."""
        distortion = MemoryDistortionEvent.create(
            session_id="session-1",
            distortion_type=DistortionType.HALLUCINATION,
            correction_status=CorrectionStatus.CORRECTED,
        )

        assert distortion.session_id == "session-1"
        assert distortion.distortion_type == DistortionType.HALLUCINATION
        assert distortion.correction_status == CorrectionStatus.CORRECTED
        assert distortion.id.startswith("mem-")


class TestLedger:
    """Tests for Ledger."""

    def test_ledger_initialization(self):
        """Test ledger initialization."""
        ledger = Ledger()

        assert len(ledger._promises) == 0
        assert len(ledger._deliveries) == 0
        assert len(ledger._recourses) == 0
        assert len(ledger._dependencies) == 0
        assert len(ledger._memory_distortions) == 0

    def test_add_and_get_promises(self):
        """Test adding and retrieving promises."""
        ledger = Ledger()

        promise1 = PromiseEvent.create(
            agent_id="did:ats:agent1",
            promise_text="Promise 1",
            impact_tier=ImpactTier.HIGH,
        )

        promise2 = PromiseEvent.create(
            agent_id="did:ats:agent2",
            promise_text="Promise 2",
            impact_tier=ImpactTier.LOW,
        )

        ledger.add_promise(promise1)
        ledger.add_promise(promise2)

        agent1_promises = ledger.get_promises_for_agent("did:ats:agent1")
        assert len(agent1_promises) == 1
        assert agent1_promises[0].id == promise1.id

        agent2_promises = ledger.get_promises_for_agent("did:ats:agent2")
        assert len(agent2_promises) == 1
        assert agent2_promises[0].id == promise2.id

    def test_deliveries_for_promise(self):
        """Test getting deliveries for a promise."""
        ledger = Ledger()

        promise = PromiseEvent.create(
            agent_id="did:ats:agent1",
            promise_text="Test",
            impact_tier=ImpactTier.HIGH,
        )

        delivery1 = DeliveryEvent.create(
            promise_id=promise.id,
            outcome=DeliveryOutcome.FAILED,
        )

        delivery2 = DeliveryEvent.create(
            promise_id=promise.id,
            outcome=DeliveryOutcome.DELIVERED,
        )

        ledger.add_promise(promise)
        ledger.add_delivery(delivery1)
        ledger.add_delivery(delivery2)

        promise_deliveries = ledger.get_deliveries_for_promise(promise.id)
        assert len(promise_deliveries) == 2

    def test_email_chain(self):
        """Test building email chain."""
        ledger = Ledger()

        # Create a chain of 3 messages
        entry1 = EmailLedgerEntry.create(
            message_id="msg1@example.com",
            from_addr="a@example.com",
            to_addr="b@example.com",
            timestamp=datetime.utcnow() - timedelta(hours=2),
            signer="sel1.example.com",
            body="Message 1",
            headers={"Subject": "Thread"},
        )

        entry2 = EmailLedgerEntry.create(
            message_id="msg2@example.com",
            from_addr="b@example.com",
            to_addr="a@example.com",
            timestamp=datetime.utcnow() - timedelta(hours=1),
            signer="sel2.example.com",
            body="Message 2",
            headers={"Subject": "Re: Thread"},
            in_reply_to="msg1@example.com",
            references=["msg1@example.com"],
        )

        entry3 = EmailLedgerEntry.create(
            message_id="msg3@example.com",
            from_addr="a@example.com",
            to_addr="b@example.com",
            timestamp=datetime.utcnow(),
            signer="sel1.example.com",
            body="Message 3",
            headers={"Subject": "Re: Thread"},
            in_reply_to="msg2@example.com",
            references=["msg1@example.com", "msg2@example.com"],
        )

        ledger.add_email_entry(entry1)
        ledger.add_email_entry(entry2)
        ledger.add_email_entry(entry3)

        chain = ledger.get_email_chain("msg3@example.com")

        assert len(chain) == 3
        assert chain[0].message_id == "msg1@example.com"
        assert chain[1].message_id == "msg2@example.com"
        assert chain[2].message_id == "msg3@example.com"

    def test_get_events_in_range(self):
        """Test getting events within a time range."""
        ledger = Ledger()

        now = datetime.utcnow()

        # Create events at different times
        old_promise = PromiseEvent.create(
            agent_id="did:ats:agent1",
            promise_text="Old promise",
            impact_tier=ImpactTier.HIGH,
            timestamp=now - timedelta(days=10),
        )

        recent_promise = PromiseEvent.create(
            agent_id="did:ats:agent1",
            promise_text="Recent promise",
            impact_tier=ImpactTier.HIGH,
            timestamp=now - timedelta(days=2),
        )

        ledger.add_promise(old_promise)
        ledger.add_promise(recent_promise)

        # Get events from last 5 days
        start = now - timedelta(days=5)
        end = now

        events = ledger.get_events_in_range(start, end)

        assert len(events) == 1
        assert events[0].id == recent_promise.id
