"""
Example: Using the Agent Trust Stack

This example demonstrates how to:
1. Create and populate a ledger
2. Calculate trust metrics
3. Validate data with hygiene gates
4. Track provenance
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
    MemoryDistortionEvent,
    DistortionType,
    CorrectionStatus,
    MetricsCalculator,
    HygieneGates,
    ProvenanceTracker,
)


def main():
    """Run the example."""
    print("=" * 60)
    print("Agent Trust Stack - Example Usage")
    print("=" * 60)
    print()

    # 1. Initialize components
    print("1. Initializing components...")
    ledger = Ledger()
    hygiene_gates = HygieneGates()
    metrics_calculator = MetricsCalculator(ledger)
    provenance = ProvenanceTracker(ledger)
    print("   ✓ Ledger, HygieneGates, MetricsCalculator, ProvenanceTracker initialized")
    print()

    # 2. Create some promises
    print("2. Creating promises for agent...")
    agent_id = "did:ats:agent-001"

    promise1 = PromiseEvent.create(
        agent_id=agent_id,
        promise_text="Generate weekly report by Friday 5pm",
        impact_tier=ImpactTier.HIGH,
    )

    promise2 = PromiseEvent.create(
        agent_id=agent_id,
        promise_text="Send email notification to team",
        impact_tier=ImpactTier.MEDIUM,
    )

    promise3 = PromiseEvent.create(
        agent_id=agent_id,
        promise_text="Update database record",
        impact_tier=ImpactTier.LOW,
    )

    ledger.add_promise(promise1)
    ledger.add_promise(promise2)
    ledger.add_promise(promise3)

    print(f"   ✓ Created 3 promises for {agent_id}")
    print()

    # 3. Create deliveries (some successful, some failed)
    print("3. Creating delivery events...")
    delivery1 = DeliveryEvent.create(
        promise_id=promise1.id,
        outcome=DeliveryOutcome.DELIVERED,
    )

    delivery2 = DeliveryEvent.create(
        promise_id=promise2.id,
        outcome=DeliveryOutcome.FAILED,
    )

    delivery3 = DeliveryEvent.create(
        promise_id=promise3.id,
        outcome=DeliveryOutcome.DELIVERED,
    )

    ledger.add_delivery(delivery1)
    ledger.add_delivery(delivery2)
    ledger.add_delivery(delivery3)

    print("   ✓ Promise 1: DELIVERED")
    print("   ✓ Promise 2: FAILED")
    print("   ✓ Promise 3: DELIVERED")
    print()

    # 4. Add a recourse event (repair)
    print("4. Creating recourse event (repair)...")
    recourse = RecourseEvent.create(
        promise_id=promise2.id,
        action="retry_delivery",
        resolution="resolved_after_retry",
    )
    ledger.add_recourse(recourse)
    print("   ✓ Recourse added for Promise 2")
    print()

    # 5. Add dependency events
    print("5. Creating dependency events...")
    dependency = DependencyEvent.create(
        workflow_id="workflow-weekly-report",
        dependency_id="api-external-data",
        workflow_weight=0.8,
        failure_rate=0.1,
        fallback_score=0.9,
    )
    ledger.add_dependency(dependency)
    print("   ✓ Dependency event added")
    print()

    # 6. Add memory distortion events
    print("6. Creating memory distortion events...")
    distortion = MemoryDistortionEvent.create(
        session_id="session-2025-02-05-001",
        distortion_type=DistortionType.HALLUCINATION,
        correction_status=CorrectionStatus.CORRECTED,
    )
    ledger.add_memory_distortion(distortion)
    print("   ✓ Memory distortion event added")
    print()

    # 7. Validate with hygiene gates
    print("7. Running hygiene checks...")
    validation_result = hygiene_gates.validate_all(promise1)
    if validation_result.is_valid:
        print("   ✓ Promise 1 passed validation")
    else:
        print(f"   ✗ Promise 1 failed validation: {len(validation_result.get_errors())} errors")
    print()

    # 8. Calculate metrics
    print("8. Calculating trust metrics...")
    now = datetime.utcnow()
    start_time = now - timedelta(days=30)

    metrics = metrics_calculator.compute_all(
        agent_id=agent_id,
        time_window_days=30,
    )

    print(f"   PDR (Promise-Delivery Rate):      {metrics.pdr:.3f}")
    print(f"   Dependency Impact:                {metrics.dependency_impact:.3f}")
    print(f"   MDR (Memory Distortion Rate):     {metrics.mdr:.3f}")
    print(f"   Recovery Score:                   {metrics.recovery_score:.3f}")
    print()

    # 9. Get provenance for a promise
    print("9. Getting provenance for Promise 1...")
    prov = provenance.get_provenance_for_promise(promise1.id)
    print(f"   Status: {prov['status']}")
    print(f"   Outcome: {prov['outcome']}")
    print(f"   Delivery count: {prov['delivery_count']}")
    print(f"   Recourse count: {prov['recourse_count']}")
    print()

    # 10. Get statistics
    print("10. Getting agent statistics...")
    stats = provenance.get_statistics(agent_id, time_window_days=30)
    print(f"    Total promises: {stats['promises']['total']}")
    print(f"    Delivered: {stats['deliveries']['delivered']}")
    print(f"    Failed: {stats['deliveries']['failed']}")
    print(f"    Partial: {stats['deliveries']['partial']}")
    print(f"    Delivery rate: {stats['delivery_rate']:.2%}")
    print()

    print("=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
