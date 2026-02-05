"""
Agent Trust Stack - Provenance Module

Provides high-level provenance tracking and verification
using the email-native ledger.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .ledger import (
    EmailLedgerEntry,
    Ledger,
    PromiseEvent,
    DeliveryEvent,
)


class ProvenanceTracker:
    """
    Track provenance of trust events and verify chains.
    """

    def __init__(self, ledger: Ledger):
        """
        Initialize provenance tracker.

        Args:
            ledger: Ledger containing event data
        """
        self.ledger = ledger

    def get_provenance_for_promise(
        self,
        promise_id: str,
    ) -> Dict[str, any]:
        """
        Get complete provenance for a promise.

        Includes:
        - The original promise
        - All delivery events
        - All recourse events
        - Associated email entries

        Args:
            promise_id: ID of the promise

        Returns:
            Dictionary with provenance information
        """
        # Get the promise
        promise = self.ledger._promises.get(promise_id)
        if not promise:
            return {
                "promise_id": promise_id,
                "found": False,
                "error": "Promise not found",
            }

        # Get deliveries
        deliveries = self.ledger.get_deliveries_for_promise(promise_id)

        # Get recourses
        recourses = self.ledger.get_recourses_for_promise(promise_id)

        # Determine final status
        if not deliveries:
            status = "pending"
            outcome = None
        else:
            latest_delivery = max(deliveries, key=lambda d: d.timestamp)
            status = "completed"
            outcome = latest_delivery.outcome.value

        return {
            "promise_id": promise_id,
            "found": True,
            "promise": {
                "id": promise.id,
                "agent_id": promise.agent_id,
                "text": promise.promise_text,
                "impact_tier": promise.impact_tier.value,
                "timestamp": promise.timestamp.isoformat(),
            },
            "status": status,
            "outcome": outcome,
            "deliveries": [
                {
                    "id": d.id,
                    "outcome": d.outcome.value,
                    "timestamp": d.timestamp.isoformat(),
                }
                for d in deliveries
            ],
            "recourses": [
                {
                    "id": r.id,
                    "action": r.action,
                    "resolution": r.resolution,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in recourses
            ],
            "delivery_count": len(deliveries),
            "recourse_count": len(recourses),
        }

    def trace_agent_promises(
        self,
        agent_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, any]]:
        """
        Trace all promises made by an agent in a time range.

        Args:
            agent_id: DID of the agent
            start_time: Optional start of time range
            end_time: Optional end of time range

        Returns:
            List of provenance dictionaries for each promise
        """
        promises = self.ledger.get_promises_for_agent(agent_id)

        # Filter by time range if provided
        if start_time or end_time:
            filtered = []
            for promise in promises:
                if start_time and promise.timestamp < start_time:
                    continue
                if end_time and promise.timestamp > end_time:
                    continue
                filtered.append(promise)
            promises = filtered

        # Get provenance for each promise
        return [
            self.get_provenance_for_promise(promise.id)
            for promise in promises
        ]

    def verify_email_chain(
        self,
        message_id: str,
    ) -> Dict[str, any]:
        """
        Verify an email chain's integrity.

        Checks:
        - Chain is complete (no gaps)
        - References are valid
        - Signatures are consistent
        - Timestamps are in order

        Args:
            message_id: Message ID to verify chain from

        Returns:
            Dictionary with verification results
        """
        chain = self.ledger.get_email_chain(message_id)

        if not chain:
            return {
                "message_id": message_id,
                "verified": False,
                "error": "Chain not found",
                "chain_length": 0,
            }

        # Check for gaps in references
        gaps = []
        for i in range(1, len(chain)):
            current = chain[i]
            previous = chain[i - 1]

            if current.in_reply_to != previous.message_id:
                gaps.append({
                    "position": i,
                    "expected": previous.message_id,
                    "found": current.in_reply_to,
                })

        # Check signature chain continuity
        signature_gaps = []
        for i, entry in enumerate(chain):
            if i > 0 and not entry.signature_chain:
                signature_gaps.append({
                    "position": i,
                    "message_id": entry.message_id,
                })

        # Check timestamp consistency
        timestamp_issues = []
        for i in range(1, len(chain)):
            current = chain[i]
            previous = chain[i - 1]

            if current.timestamp <= previous.timestamp:
                timestamp_issues.append({
                    "position": i,
                    "current": current.timestamp.isoformat(),
                    "previous": previous.timestamp.isoformat(),
                })

        # Determine overall verification status
        verified = (
            len(gaps) == 0
            and len(signature_gaps) == 0
            and len(timestamp_issues) == 0
        )

        return {
            "message_id": message_id,
            "verified": verified,
            "chain_length": len(chain),
            "issues": {
                "gaps": gaps,
                "signature_gaps": signature_gaps,
                "timestamp_issues": timestamp_issues,
            },
            "total_issues": len(gaps) + len(signature_gaps) + len(timestamp_issues),
        }

    def get_timeline(
        self,
        agent_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, any]]:
        """
        Get a chronological timeline of events for an agent.

        Args:
            agent_id: DID of the agent
            start_time: Optional start of time range
            end_time: Optional end of time range

        Returns:
            List of events in chronological order
        """
        events = []

        # Add promises
        for promise in self.ledger._promises.values():
            if promise.agent_id == agent_id:
                if start_time and promise.timestamp < start_time:
                    continue
                if end_time and promise.timestamp > end_time:
                    continue

                events.append({
                    "type": "promise",
                    "id": promise.id,
                    "timestamp": promise.timestamp,
                    "data": promise.to_dict(),
                })

        # Add deliveries
        for delivery in self.ledger._deliveries.values():
            # Get the promise to check agent_id
            promise = self.ledger._promises.get(delivery.promise_id)
            if promise and promise.agent_id == agent_id:
                if start_time and delivery.timestamp < start_time:
                    continue
                if end_time and delivery.timestamp > end_time:
                    continue

                events.append({
                    "type": "delivery",
                    "id": delivery.id,
                    "timestamp": delivery.timestamp,
                    "data": delivery.to_dict(),
                })

        # Add recourses
        for recourse in self.ledger._recourses.values():
            promise = self.ledger._promises.get(recourse.promise_id)
            if promise and promise.agent_id == agent_id:
                if start_time and recourse.timestamp < start_time:
                    continue
                if end_time and recourse.timestamp > end_time:
                    continue

                events.append({
                    "type": "recourse",
                    "id": recourse.id,
                    "timestamp": recourse.timestamp,
                    "data": recourse.to_dict(),
                })

        # Sort by timestamp
        events.sort(key=lambda e: e["timestamp"])

        return events

    def get_statistics(
        self,
        agent_id: str,
        time_window_days: int = 90,
    ) -> Dict[str, any]:
        """
        Get summary statistics for an agent.

        Args:
            agent_id: DID of the agent
            time_window_days: Time window in days

        Returns:
            Dictionary with summary statistics
        """
        now = datetime.utcnow()
        start_time = now - timedelta(days=time_window_days)

        promises = [
            p for p in self.ledger._promises.values()
            if p.agent_id == agent_id and start_time <= p.timestamp <= now
        ]

        deliveries = []
        for promise in promises:
            promise_deliveries = self.ledger.get_deliveries_for_promise(promise.id)
            deliveries.extend(promise_deliveries)

        recourses = []
        for promise in promises:
            promise_recourses = self.ledger.get_recourses_for_promise(promise.id)
            recourses.extend(promise_recourses)

        # Count outcomes
        delivered = sum(
            1 for d in deliveries
            if d.outcome.value == "delivered"
        )
        failed = sum(
            1 for d in deliveries
            if d.outcome.value == "failed"
        )
        partial = sum(
            1 for d in deliveries
            if d.outcome.value == "partial"
        )

        return {
            "agent_id": agent_id,
            "time_window_days": time_window_days,
            "period": {
                "start": start_time.isoformat(),
                "end": now.isoformat(),
            },
            "promises": {
                "total": len(promises),
                "with_delivery": len(deliveries),
                "with_recourse": len(recourses),
            },
            "deliveries": {
                "delivered": delivered,
                "failed": failed,
                "partial": partial,
                "total": len(deliveries),
            },
            "recourses": {
                "total": len(recourses),
            },
            "delivery_rate": delivered / len(deliveries) if deliveries else 0.0,
        }
