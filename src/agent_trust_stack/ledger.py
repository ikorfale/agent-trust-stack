"""
Agent Trust Stack - Ledger Module

Implements email-native ledger schema with event tracking
and canonical chain construction.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union


class EventType(str, Enum):
    """Types of events tracked in the ledger."""
    PROMISE = "promise"
    DELIVERY = "delivery"
    RECOURSE = "recourse"
    DEPENDENCY = "dependency"
    MEMORY_DISTORTION = "memory_distortion"


class DeliveryOutcome(str, Enum):
    """Possible outcomes for delivery events."""
    DELIVERED = "delivered"
    FAILED = "failed"
    PARTIAL = "partial"


class ImpactTier(str, Enum):
    """Impact tiers for promises."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DistortionType(str, Enum):
    """Types of memory distortions."""
    HALLUCINATION = "hallucination"
    CONFABULATION = "confabulation"
    TEMPORAL_DRIFT = "temporal_drift"
    ATTRIBUTE_MIXUP = "attribute_mixup"
    CONTEXT_LOSS = "context_loss"


class CorrectionStatus(str, Enum):
    """Status of distortion corrections."""
    UNCORRECTED = "uncorrected"
    CORRECTED = "corrected"
    PARTIALLY_CORRECTED = "partially_corrected"


@dataclass
class EmailLedgerEntry:
    """
    Canonical email ledger entry (email-native provenance).

    Required fields per SPEC v0.1.0:
    - message_id: Unique email message ID
    - in_reply_to: ID of message this replies to (thread chain)
    - references: All message IDs in the thread
    - from_addr: Sender email address
    - to_addr: Recipient email address
    - timestamp: Message timestamp
    - signer: DKIM selector+domain
    - body_hash: SHA-256 of canonicalized body
    - headers_hash: SHA-256 of canonicalized headers
    - signature_chain: Chain of message signatures
    """

    message_id: str
    from_addr: str
    to_addr: str
    timestamp: datetime
    signer: str
    body_hash: str
    headers_hash: str
    in_reply_to: Optional[str] = None
    references: List[str] = field(default_factory=list)
    signature_chain: List[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        message_id: str,
        from_addr: str,
        to_addr: str,
        timestamp: Union[datetime, str],
        signer: str,
        body: str,
        headers: Dict[str, str],
        in_reply_to: Optional[str] = None,
        references: Optional[List[str]] = None,
    ) -> "EmailLedgerEntry":
        """
        Create a new ledger entry with automatic hash calculation.

        Args:
            message_id: Unique email message ID
            from_addr: Sender email address
            to_addr: Recipient email address
            timestamp: Message timestamp (datetime or ISO string)
            signer: DKIM selector+domain
            body: Email body content
            headers: Email headers as dict
            in_reply_to: ID of message this replies to
            references: All message IDs in the thread

        Returns:
            EmailLedgerEntry
        """
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        # Canonicalize and hash body
        canonical_body = cls._canonicalize_body(body)
        body_hash = hashlib.sha256(canonical_body.encode()).hexdigest()

        # Canonicalize and hash headers
        canonical_headers = cls._canonicalize_headers(headers)
        headers_hash = hashlib.sha256(canonical_headers.encode()).hexdigest()

        # Build references list
        if references is None:
            references = []
        if in_reply_to and in_reply_to not in references:
            references.insert(0, in_reply_to)

        return cls(
            message_id=message_id,
            from_addr=from_addr,
            to_addr=to_addr,
            timestamp=timestamp,
            signer=signer,
            body_hash=body_hash,
            headers_hash=headers_hash,
            in_reply_to=in_reply_to,
            references=references,
            signature_chain=[],
        )

    @staticmethod
    def _canonicalize_body(body: str) -> str:
        """
        Canonicalize email body for hashing.

        Strip leading/trailing whitespace, normalize line endings,
        and remove trailing whitespace from each line.
        """
        lines = body.strip().split('\n')
        canonical_lines = [line.rstrip() for line in lines]
        return '\n'.join(canonical_lines)

    @staticmethod
    def _canonicalize_headers(headers: Dict[str, str]) -> str:
        """
        Canonicalize email headers for hashing.

        Sort headers alphabetically, lowercase keys, trim values.
        """
        sorted_headers = sorted(headers.items())
        canonical = '\n'.join(f"{k.lower().strip()}:{v.strip()}" for k, v in sorted_headers)
        return canonical

    def verify_integrity(self, body: str, headers: Dict[str, str]) -> bool:
        """
        Verify that body and headers match stored hashes.

        Args:
            body: Email body content
            headers: Email headers as dict

        Returns:
            True if hashes match, False otherwise
        """
        body_hash = hashlib.sha256(self._canonicalize_body(body).encode()).hexdigest()
        headers_hash = hashlib.sha256(self._canonicalize_headers(headers).encode()).hexdigest()

        return body_hash == self.body_hash and headers_hash == self.headers_hash

    def extend_chain(self, signature: str) -> None:
        """
        Extend the signature chain with a new signature.

        Args:
            signature: New signature to add
        """
        self.signature_chain.append(signature)

    def to_dict(self) -> Dict:
        """Convert ledger entry to dictionary."""
        return {
            "message_id": self.message_id,
            "in_reply_to": self.in_reply_to,
            "references": self.references,
            "from": self.from_addr,
            "to": self.to_addr,
            "timestamp": self.timestamp.isoformat(),
            "signer": self.signer,
            "body_hash": self.body_hash,
            "headers_hash": self.headers_hash,
            "signature_chain": self.signature_chain,
        }


@dataclass
class PromiseEvent:
    """
    Promise event: agent commits to deliver something.

    Attributes:
        id: Unique event identifier
        agent_id: DID of the agent making the promise
        promise_text: Text description of the promise
        impact_tier: Criticality tier of the promise
        timestamp: When the promise was made
        metadata: Additional event metadata
    """

    id: str
    agent_id: str
    promise_text: str
    impact_tier: ImpactTier
    timestamp: datetime
    metadata: Dict[str, any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        agent_id: str,
        promise_text: str,
        impact_tier: ImpactTier,
        metadata: Optional[Dict[str, any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> "PromiseEvent":
        """Create a new promise event."""
        return cls(
            id=f"promise-{uuid.uuid4().hex[:16]}",
            agent_id=agent_id,
            promise_text=promise_text,
            impact_tier=impact_tier,
            timestamp=timestamp or datetime.utcnow(),
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": EventType.PROMISE.value,
            "agent_id": self.agent_id,
            "promise_text": self.promise_text,
            "impact_tier": self.impact_tier.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class DeliveryEvent:
    """
    Delivery event: records outcome of a promise.

    Attributes:
        id: Unique event identifier
        promise_id: ID of the promise being delivered
        outcome: Delivery outcome
        timestamp: When delivery occurred
        delivered_amount: Amount delivered (for partial outcomes)
        expected_amount: Expected amount
        metadata: Additional event metadata
    """

    id: str
    promise_id: str
    outcome: DeliveryOutcome
    timestamp: datetime
    delivered_amount: Optional[float] = None
    expected_amount: Optional[float] = None
    metadata: Dict[str, any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        promise_id: str,
        outcome: DeliveryOutcome,
        delivered_amount: Optional[float] = None,
        expected_amount: Optional[float] = None,
        metadata: Optional[Dict[str, any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> "DeliveryEvent":
        """Create a new delivery event."""
        return cls(
            id=f"delivery-{uuid.uuid4().hex[:16]}",
            promise_id=promise_id,
            outcome=outcome,
            timestamp=timestamp or datetime.utcnow(),
            delivered_amount=delivered_amount,
            expected_amount=expected_amount,
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": EventType.DELIVERY.value,
            "promise_id": self.promise_id,
            "outcome": self.outcome.value,
            "timestamp": self.timestamp.isoformat(),
            "delivered_amount": self.delivered_amount,
            "expected_amount": self.expected_amount,
            "metadata": self.metadata,
        }


@dataclass
class RecourseEvent:
    """
    Recourse event: tracks repair/correction actions.

    Attributes:
        id: Unique event identifier
        promise_id: ID of the related promise
        action: Type of recourse action taken
        resolution: Resolution status
        timestamp: When recourse was taken
        metadata: Additional event metadata
    """

    id: str
    promise_id: str
    action: str
    resolution: str
    timestamp: datetime
    metadata: Dict[str, any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        promise_id: str,
        action: str,
        resolution: str,
        metadata: Optional[Dict[str, any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> "RecourseEvent":
        """Create a new recourse event."""
        return cls(
            id=f"recourse-{uuid.uuid4().hex[:16]}",
            promise_id=promise_id,
            action=action,
            resolution=resolution,
            timestamp=timestamp or datetime.utcnow(),
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": EventType.RECOURSE.value,
            "promise_id": self.promise_id,
            "action": self.action,
            "resolution": self.resolution,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class DependencyEvent:
    """
    Dependency event: tracks workflow dependencies and fallbacks.

    Attributes:
        id: Unique event identifier
        workflow_id: ID of the workflow
        dependency_id: ID of the dependency
        workflow_weight: Weight of this workflow in overall system
        failure_rate: Historical failure rate of the dependency
        fallback_score: Score of fallback alternatives (0-1)
        timestamp: When the dependency was registered
        metadata: Additional event metadata
    """

    id: str
    workflow_id: str
    dependency_id: str
    workflow_weight: float
    failure_rate: float
    fallback_score: float
    timestamp: datetime
    metadata: Dict[str, any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        workflow_id: str,
        dependency_id: str,
        workflow_weight: float,
        failure_rate: float,
        fallback_score: float,
        metadata: Optional[Dict[str, any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> "DependencyEvent":
        """Create a new dependency event."""
        return cls(
            id=f"dep-{uuid.uuid4().hex[:16]}",
            workflow_id=workflow_id,
            dependency_id=dependency_id,
            workflow_weight=workflow_weight,
            failure_rate=failure_rate,
            fallback_score=fallback_score,
            timestamp=timestamp or datetime.utcnow(),
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": EventType.DEPENDENCY.value,
            "workflow_id": self.workflow_id,
            "dependency_id": self.dependency_id,
            "workflow_weight": self.workflow_weight,
            "failure_rate": self.failure_rate,
            "fallback_score": self.fallback_score,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class MemoryDistortionEvent:
    """
    Memory distortion event: tracks false memory or correction events.

    Attributes:
        id: Unique event identifier
        session_id: ID of the session where distortion occurred
        distortion_type: Type of memory distortion
        correction_status: Whether/how it was corrected
        timestamp: When the distortion was detected
        metadata: Additional event metadata
    """

    id: str
    session_id: str
    distortion_type: DistortionType
    correction_status: CorrectionStatus
    timestamp: datetime
    metadata: Dict[str, any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        session_id: str,
        distortion_type: DistortionType,
        correction_status: CorrectionStatus,
        metadata: Optional[Dict[str, any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> "MemoryDistortionEvent":
        """Create a new memory distortion event."""
        return cls(
            id=f"mem-{uuid.uuid4().hex[:16]}",
            session_id=session_id,
            distortion_type=distortion_type,
            correction_status=correction_status,
            timestamp=timestamp or datetime.utcnow(),
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": EventType.MEMORY_DISTORTION.value,
            "session_id": self.session_id,
            "distortion_type": self.distortion_type.value,
            "correction_status": self.correction_status.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


# Union type for all events
Event = Union[
    PromiseEvent,
    DeliveryEvent,
    RecourseEvent,
    DependencyEvent,
    MemoryDistortionEvent,
]


class Ledger:
    """
    Main ledger for storing and querying trust events.

    Provides in-memory storage with methods for:
    - Adding events
    - Querying by agent, time range, event type
    - Computing metrics
    """

    def __init__(self):
        """Initialize empty ledger."""
        self._promises: Dict[str, PromiseEvent] = {}
        self._deliveries: Dict[str, DeliveryEvent] = {}
        self._recourses: Dict[str, RecourseEvent] = {}
        self._dependencies: Dict[str, DependencyEvent] = {}
        self._memory_distortions: Dict[str, MemoryDistortionEvent] = {}
        self._email_entries: Dict[str, EmailLedgerEntry] = {}

    def add_promise(self, promise: PromiseEvent) -> None:
        """Add a promise event to the ledger."""
        self._promises[promise.id] = promise

    def add_delivery(self, delivery: DeliveryEvent) -> None:
        """Add a delivery event to the ledger."""
        self._deliveries[delivery.id] = delivery

    def add_recourse(self, recourse: RecourseEvent) -> None:
        """Add a recourse event to the ledger."""
        self._recourses[recourse.id] = recourse

    def add_dependency(self, dependency: DependencyEvent) -> None:
        """Add a dependency event to the ledger."""
        self._dependencies[dependency.id] = dependency

    def add_memory_distortion(self, distortion: MemoryDistortionEvent) -> None:
        """Add a memory distortion event to the ledger."""
        self._memory_distortions[distortion.id] = distortion

    def add_email_entry(self, entry: EmailLedgerEntry) -> None:
        """Add an email ledger entry."""
        self._email_entries[entry.message_id] = entry

    def get_promises_for_agent(self, agent_id: str) -> List[PromiseEvent]:
        """Get all promises for a specific agent."""
        return [p for p in self._promises.values() if p.agent_id == agent_id]

    def get_deliveries_for_promise(self, promise_id: str) -> List[DeliveryEvent]:
        """Get all delivery events for a specific promise."""
        return [d for d in self._deliveries.values() if d.promise_id == promise_id]

    def get_recourses_for_promise(self, promise_id: str) -> List[RecourseEvent]:
        """Get all recourse events for a specific promise."""
        return [r for r in self._recourses.values() if r.promise_id == promise_id]

    def get_dependencies_for_workflow(self, workflow_id: str) -> List[DependencyEvent]:
        """Get all dependency events for a specific workflow."""
        return [d for d in self._dependencies.values() if d.workflow_id == workflow_id]

    def get_email_chain(self, message_id: str) -> List[EmailLedgerEntry]:
        """
        Get the full email chain for a message.

        Follows references back to the root message.
        """
        chain = []
        current = self._email_entries.get(message_id)

        while current:
            chain.insert(0, current)
            if current.in_reply_to:
                current = self._email_entries.get(current.in_reply_to)
            else:
                break

        return chain

    def get_events_in_range(
        self,
        start: datetime,
        end: datetime,
    ) -> List[Event]:
        """Get all events within a time range."""
        events = []

        for promise in self._promises.values():
            if start <= promise.timestamp <= end:
                events.append(promise)

        for delivery in self._deliveries.values():
            if start <= delivery.timestamp <= end:
                events.append(delivery)

        for recourse in self._recourses.values():
            if start <= recourse.timestamp <= end:
                events.append(recourse)

        return events

    def to_dict(self) -> Dict:
        """Convert entire ledger to dictionary."""
        return {
            "promises": [p.to_dict() for p in self._promises.values()],
            "deliveries": [d.to_dict() for d in self._deliveries.values()],
            "recourses": [r.to_dict() for r in self._recourses.values()],
            "dependencies": [d.to_dict() for d in self._dependencies.values()],
            "memory_distortions": [m.to_dict() for m in self._memory_distortions.values()],
            "email_entries": [e.to_dict() for e in self._email_entries.values()],
        }
