#!/usr/bin/env python3
"""
Quick test of Agent Trust Stack core functionality.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timedelta

from agent_trust_stack import (
    Ledger,
    PromiseEvent,
    DeliveryEvent,
    DeliveryOutcome,
    ImpactTier,
    RecourseEvent,
    DependencyEvent,
    MetricsCalculator,
    HygieneGates,
    EmailLedgerEntry,
)


def test_ledger():
    """Test basic ledger operations."""
    print("Testing Ledger...")
    ledger = Ledger()

    # Create and add promise
    promise = PromiseEvent.create(
        agent_id="did:ats:test-agent",
        promise_text="Complete the task",
        impact_tier=ImpactTier.HIGH,
    )
    ledger.add_promise(promise)

    # Create and add delivery
    delivery = DeliveryEvent.create(
        promise_id=promise.id,
        outcome=DeliveryOutcome.DELIVERED,
    )
    ledger.add_delivery(delivery)

    # Verify
    promises = ledger.get_promises_for_agent("did:ats:test-agent")
    assert len(promises) == 1
    print("  ✓ Ledger operations work")


def test_metrics():
    """Test metrics calculation."""
    print("\nTesting Metrics...")
    ledger = Ledger()
    calculator = MetricsCalculator(ledger)

    # Create test data
    now = datetime.utcnow()

    promise1 = PromiseEvent.create(
        agent_id="did:ats:test-agent",
        promise_text="Task 1",
        impact_tier=ImpactTier.HIGH,
        timestamp=now - timedelta(days=1),
    )
    promise2 = PromiseEvent.create(
        agent_id="did:ats:test-agent",
        promise_text="Task 2",
        impact_tier=ImpactTier.HIGH,
        timestamp=now - timedelta(days=1),
    )

    delivery1 = DeliveryEvent.create(
        promise_id=promise1.id,
        outcome=DeliveryOutcome.DELIVERED,
    )
    delivery2 = DeliveryEvent.create(
        promise_id=promise2.id,
        outcome=DeliveryOutcome.FAILED,
    )

    ledger.add_promise(promise1)
    ledger.add_promise(promise2)
    ledger.add_delivery(delivery1)
    ledger.add_delivery(delivery2)

    # Calculate PDR
    start = now - timedelta(days=30)
    end = now
    pdr = calculator.compute_pdr("did:ats:test-agent", start, end)

    # Should be ~0.5 (50% delivery rate)
    assert 0.4 < pdr < 0.6
    print(f"  ✓ PDR calculation works: {pdr:.2f}")

    # Compute all metrics
    metrics = calculator.compute_all("did:ats:test-agent", 30)
    assert metrics.pdr is not None
    assert 0.0 <= metrics.pdr <= 1.0
    print(f"  ✓ All metrics computed: PDR={metrics.pdr:.2f}")


def test_hygiene():
    """Test hygiene gates."""
    print("\nTesting Hygiene Gates...")
    gates = HygieneGates()

    # Validate email
    result = gates.validate_all("user@example.com")
    assert result.is_valid
    print("  ✓ Email validation works")

    # Validate timestamp
    result = gates.validate_all(datetime.utcnow())
    assert result.is_valid
    print("  ✓ Timestamp validation works")

    # Validate promise
    promise = PromiseEvent.create(
        agent_id="did:ats:test",
        promise_text="Test promise",
        impact_tier=ImpactTier.MEDIUM,
    )
    result = gates.validate_all(promise)
    assert result.is_valid
    print("  ✓ Promise validation works")


def test_email_ledger():
    """Test email ledger entry."""
    print("\nTesting Email Ledger...")
    ledger = Ledger()

    entry = EmailLedgerEntry.create(
        message_id="test@example.com",
        from_addr="sender@example.com",
        to_addr="recipient@example.com",
        timestamp=datetime.utcnow(),
        signer="selector.example.com",
        body="Test body",
        headers={"Subject": "Test"},
    )

    # Verify hashes are generated
    assert len(entry.body_hash) == 64  # SHA-256 hex
    assert len(entry.headers_hash) == 64
    print("  ✓ Email ledger entry creation works")

    # Verify integrity check
    assert entry.verify_integrity("Test body", {"Subject": "Test"})
    assert not entry.verify_integrity("Wrong body", {"Subject": "Test"})
    print("  ✓ Email integrity verification works")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Agent Trust Stack - Quick Functionality Test")
    print("=" * 60)

    try:
        test_ledger()
        test_metrics()
        test_hygiene()
        test_email_ledger()

        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
