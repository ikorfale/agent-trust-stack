"""
Agent Trust Stack - Hygiene Gates Module

Implements validation, integrity checks, and quality gates
for trust data and calculations.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .ledger import (
    EmailLedgerEntry,
    Event,
    ImpactTier,
    DeliveryOutcome,
    PromiseEvent,
    DeliveryEvent,
    RecourseEvent,
    DependencyEvent,
    MemoryDistortionEvent,
)


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """
    A validation issue found during hygiene checks.

    Attributes:
        code: Issue code identifier
        message: Human-readable description
        severity: Severity level
        location: Where the issue was found (e.g., field name)
        value: The problematic value
    """

    code: str
    message: str
    severity: ValidationSeverity
    location: str
    value: Any

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "location": self.location,
            "value": str(self.value),
        }


@dataclass
class ValidationResult:
    """
    Result of a validation check.

    Attributes:
        is_valid: Overall validity (True if no critical issues)
        issues: List of validation issues found
    """

    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue."""
        self.issues.append(issue)
        # Update is_valid based on severity
        if issue.severity == ValidationSeverity.CRITICAL:
            self.is_valid = False

    def get_errors(self) -> List[ValidationIssue]:
        """Get all error and critical issues."""
        return [i for i in self.issues if i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]

    def get_warnings(self) -> List[ValidationIssue]:
        """Get all warning issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "issues": [i.to_dict() for i in self.issues],
            "error_count": len(self.get_errors()),
            "warning_count": len(self.get_warnings()),
        }


class HygieneGate:
    """
    Base class for hygiene gates.

    A hygiene gate validates data before it enters the trust system.
    """

    def validate(self, data: Any) -> ValidationResult:
        """
        Validate the provided data.

        Args:
            data: Data to validate

        Returns:
            ValidationResult
        """
        raise NotImplementedError("Subclasses must implement validate()")


class EmailValidator(HygieneGate):
    """
    Validate email addresses and DKIM signatures.
    """

    # Simple email regex pattern
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    def validate(self, email: str) -> ValidationResult:
        """
        Validate an email address.

        Args:
            email: Email address to validate

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)

        if not email:
            result.add_issue(ValidationIssue(
                code="EMAIL_EMPTY",
                message="Email address is empty",
                severity=ValidationSeverity.ERROR,
                location="email",
                value=email,
            ))
            return result

        if not isinstance(email, str):
            result.add_issue(ValidationIssue(
                code="EMAIL_TYPE",
                message="Email must be a string",
                severity=ValidationSeverity.ERROR,
                location="email",
                value=type(email),
            ))
            return result

        if not self.EMAIL_PATTERN.match(email):
            result.add_issue(ValidationIssue(
                code="EMAIL_FORMAT",
                message="Email address format is invalid",
                severity=ValidationSeverity.ERROR,
                location="email",
                value=email,
            ))
            result.is_valid = False

        return result

    def validate_dkim_signer(self, signer: str) -> ValidationResult:
        """
        Validate DKIM signer format (selector.domain).

        Args:
            signer: DKIM signer string

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)

        if not signer:
            result.add_issue(ValidationIssue(
                code="DKIM_EMPTY",
                message="DKIM signer is empty",
                severity=ValidationSeverity.ERROR,
                location="signer",
                value=signer,
            ))
            return result

        parts = signer.split('.')
        if len(parts) < 2:
            result.add_issue(ValidationIssue(
                code="DKIM_FORMAT",
                message="DKIM signer must be in format selector.domain",
                severity=ValidationSeverity.ERROR,
                location="signer",
                value=signer,
            ))
            result.is_valid = False

        return result


class HashValidator(HygieneGate):
    """
    Validate hash strings (SHA-256 format).
    """

    # SHA-256 hex pattern (64 hex characters)
    SHA256_PATTERN = re.compile(r'^[0-9a-fA-F]{64}$')

    def validate(self, hash_string: str, hash_type: str = "SHA-256") -> ValidationResult:
        """
        Validate a hash string.

        Args:
            hash_string: Hash to validate
            hash_type: Type of hash (for error messages)

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)

        if not hash_string:
            result.add_issue(ValidationIssue(
                code="HASH_EMPTY",
                message=f"{hash_type} hash is empty",
                severity=ValidationSeverity.ERROR,
                location="hash",
                value=hash_string,
            ))
            return result

        if not isinstance(hash_string, str):
            result.add_issue(ValidationIssue(
                code="HASH_TYPE",
                message=f"{hash_type} hash must be a string",
                severity=ValidationSeverity.ERROR,
                location="hash",
                value=type(hash_string),
            ))
            return result

        if not self.SHA256_PATTERN.match(hash_string):
            result.add_issue(ValidationIssue(
                code="HASH_FORMAT",
                message=f"{hash_type} hash must be 64 hex characters",
                severity=ValidationSeverity.ERROR,
                location="hash",
                value=hash_string,
            ))
            result.is_valid = False

        return result


class TimestampValidator(HygieneGate):
    """
    Validate timestamps and time ranges.
    """

    def validate(self, timestamp: datetime) -> ValidationResult:
        """
        Validate a timestamp.

        Args:
            timestamp: Timestamp to validate

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)

        if not isinstance(timestamp, datetime):
            result.add_issue(ValidationIssue(
                code="TIMESTAMP_TYPE",
                message="Timestamp must be a datetime object",
                severity=ValidationSeverity.ERROR,
                location="timestamp",
                value=type(timestamp),
            ))
            return result

        # Check for reasonable timestamps (not too far in past or future)
        now = datetime.utcnow()
        one_year_ago = now - timedelta(days=365)
        one_year_future = now + timedelta(days=365)

        if timestamp < one_year_ago:
            result.add_issue(ValidationIssue(
                code="TIMESTAMP_TOO_OLD",
                message="Timestamp is more than one year in the past",
                severity=ValidationSeverity.WARNING,
                location="timestamp",
                value=timestamp.isoformat(),
            ))

        if timestamp > one_year_future:
            result.add_issue(ValidationIssue(
                code="TIMESTAMP_FUTURE",
                message="Timestamp is more than one year in the future",
                severity=ValidationSeverity.ERROR,
                location="timestamp",
                value=timestamp.isoformat(),
            ))
            result.is_valid = False

        return result

    def validate_order(
        self,
        earlier: datetime,
        later: datetime,
        field_earlier: str = "earlier",
        field_later: str = "later",
    ) -> ValidationResult:
        """
        Validate that two timestamps are in correct order.

        Args:
            earlier: Earlier timestamp
            later: Later timestamp
            field_earlier: Field name for earlier timestamp
            field_later: Field name for later timestamp

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)

        if earlier > later:
            result.add_issue(ValidationIssue(
                code="TIMESTAMP_ORDER",
                message=f"{field_earlier} must be before {field_later}",
                severity=ValidationSeverity.ERROR,
                location=f"{field_earlier},{field_later}",
                value=f"{earlier.isoformat()} > {later.isoformat()}",
            ))
            result.is_valid = False

        return result


class MetricsValidator(HygieneGate):
    """
    Validate metric values and ranges.
    """

    def validate_range(
        self,
        value: float,
        min_val: float = 0.0,
        max_val: float = 1.0,
        field_name: str = "metric",
    ) -> ValidationResult:
        """
        Validate that a value is within range.

        Args:
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            field_name: Field name for error messages

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)

        if not isinstance(value, (int, float)):
            result.add_issue(ValidationIssue(
                code="METRIC_TYPE",
                message=f"{field_name} must be a number",
                severity=ValidationSeverity.ERROR,
                location=field_name,
                value=type(value),
            ))
            return result

        if value < min_val:
            result.add_issue(ValidationIssue(
                code="METRIC_TOO_LOW",
                message=f"{field_name} is below minimum ({value} < {min_val})",
                severity=ValidationSeverity.ERROR,
                location=field_name,
                value=value,
            ))
            result.is_valid = False

        if value > max_val:
            result.add_issue(ValidationIssue(
                code="METRIC_TOO_HIGH",
                message=f"{field_name} is above maximum ({value} > {max_val})",
                severity=ValidationSeverity.ERROR,
                location=field_name,
                value=value,
            ))
            result.is_valid = False

        return result

    def validate_metrics(self, metrics: Dict[str, float]) -> ValidationResult:
        """
        Validate all trust metrics.

        Args:
            metrics: Dictionary of metric name to value

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)

        for metric_name, value in metrics.items():
            sub_result = self.validate_range(value, 0.0, 1.0, metric_name)
            if not sub_result.is_valid:
                result.is_valid = False
                result.issues.extend(sub_result.issues)

        return result


class EventValidator(HygieneGate):
    """
    Validate event data integrity.
    """

    def __init__(self):
        """Initialize with sub-validators."""
        self.timestamp_validator = TimestampValidator()
        self.email_validator = EmailValidator()
        self.metrics_validator = MetricsValidator()

    def validate_promise_event(self, event: PromiseEvent) -> ValidationResult:
        """
        Validate a promise event.

        Args:
            event: PromiseEvent to validate

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)

        # Validate timestamp
        ts_result = self.timestamp_validator.validate(event.timestamp)
        result.issues.extend(ts_result.issues)
        if not ts_result.is_valid:
            result.is_valid = False

        # Validate agent_id format (should be a DID)
        if not event.agent_id or not isinstance(event.agent_id, str):
            result.add_issue(ValidationIssue(
                code="AGENT_ID_INVALID",
                message="Agent ID must be a non-empty string (DID)",
                severity=ValidationSeverity.ERROR,
                location="agent_id",
                value=event.agent_id,
            ))
            result.is_valid = False

        # Validate impact tier
        if not isinstance(event.impact_tier, ImpactTier):
            result.add_issue(ValidationIssue(
                code="IMPACT_TIER_INVALID",
                message="Impact tier must be a valid ImpactTier enum",
                severity=ValidationSeverity.ERROR,
                location="impact_tier",
                value=event.impact_tier,
            ))
            result.is_valid = False

        # Validate promise text
        if not event.promise_text or not isinstance(event.promise_text, str):
            result.add_issue(ValidationIssue(
                code="PROMISE_TEXT_INVALID",
                message="Promise text must be a non-empty string",
                severity=ValidationSeverity.ERROR,
                location="promise_text",
                value=event.promise_text,
            ))
            result.is_valid = False

        return result

    def validate_delivery_event(self, event: DeliveryEvent) -> ValidationResult:
        """
        Validate a delivery event.

        Args:
            event: DeliveryEvent to validate

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)

        # Validate timestamp
        ts_result = self.timestamp_validator.validate(event.timestamp)
        result.issues.extend(ts_result.issues)
        if not ts_result.is_valid:
            result.is_valid = False

        # Validate promise_id
        if not event.promise_id or not isinstance(event.promise_id, str):
            result.add_issue(ValidationIssue(
                code="PROMISE_ID_INVALID",
                message="Promise ID must be a non-empty string",
                severity=ValidationSeverity.ERROR,
                location="promise_id",
                value=event.promise_id,
            ))
            result.is_valid = False

        # Validate outcome
        if not isinstance(event.outcome, DeliveryOutcome):
            result.add_issue(ValidationIssue(
                code="DELIVERY_OUTCOME_INVALID",
                message="Delivery outcome must be a valid DeliveryOutcome enum",
                severity=ValidationSeverity.ERROR,
                location="outcome",
                value=event.outcome,
            ))
            result.is_valid = False

        # Validate amounts for partial deliveries
        if event.outcome == DeliveryOutcome.PARTIAL:
            if event.delivered_amount is None or event.expected_amount is None:
                result.add_issue(ValidationIssue(
                    code="PARTIAL_DELIVERY_AMOUNTS_MISSING",
                    message="Partial delivery must specify delivered_amount and expected_amount",
                    severity=ValidationSeverity.ERROR,
                    location="delivered_amount,expected_amount",
                    value=event,
                ))
                result.is_valid = False
            elif event.delivered_amount > event.expected_amount:
                result.add_issue(ValidationIssue(
                    code="DELIVERED_EXCEEDS_EXPECTED",
                    message="Delivered amount cannot exceed expected amount",
                    severity=ValidationSeverity.WARNING,
                    location="delivered_amount",
                    value=f"{event.delivered_amount} > {event.expected_amount}",
                ))

        return result

    def validate_email_entry(self, entry: EmailLedgerEntry) -> ValidationResult:
        """
        Validate an email ledger entry.

        Args:
            entry: EmailLedgerEntry to validate

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)

        # Validate email addresses
        for_result = self.email_validator.validate(entry.from_addr)
        result.issues.extend(for_result.issues)
        if not for_result.is_valid:
            result.is_valid = False

        to_result = self.email_validator.validate(entry.to_addr)
        result.issues.extend(to_result.issues)
        if not to_result.is_valid:
            result.is_valid = False

        # Validate DKIM signer
        dkim_result = self.email_validator.validate_dkim_signer(entry.signer)
        result.issues.extend(dkim_result.issues)
        if not dkim_result.is_valid:
            result.is_valid = False

        # Validate hashes
        hash_validator = HashValidator()
        body_hash_result = hash_validator.validate(entry.body_hash)
        result.issues.extend(body_hash_result.issues)
        if not body_hash_result.is_valid:
            result.is_valid = False

        headers_hash_result = hash_validator.validate(entry.headers_hash)
        result.issues.extend(headers_hash_result.issues)
        if not headers_hash_result.is_valid:
            result.is_valid = False

        # Validate timestamp
        ts_result = self.timestamp_validator.validate(entry.timestamp)
        result.issues.extend(ts_result.issues)
        if not ts_result.is_valid:
            result.is_valid = False

        # Validate message_id
        if not entry.message_id or not isinstance(entry.message_id, str):
            result.add_issue(ValidationIssue(
                code="MESSAGE_ID_INVALID",
                message="Message ID must be a non-empty string",
                severity=ValidationSeverity.ERROR,
                location="message_id",
                value=entry.message_id,
            ))
            result.is_valid = False

        # Validate references if present
        if entry.references:
            if not isinstance(entry.references, list):
                result.add_issue(ValidationIssue(
                    code="REFERENCES_TYPE",
                    message="References must be a list",
                    severity=ValidationSeverity.ERROR,
                    location="references",
                    value=type(entry.references),
                ))
                result.is_valid = False

        return result


class IntegrityChecker:
    """
    Check data integrity across the ledger.
    """

    def check_promise_delivery_consistency(
        self,
        promises: Dict[str, PromiseEvent],
        deliveries: Dict[str, DeliveryEvent],
    ) -> ValidationResult:
        """
        Check consistency between promises and deliveries.

        Args:
            promises: Dict of promise_id to PromiseEvent
            deliveries: Dict of delivery_id to DeliveryEvent

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)

        # Build a map of promise_id to deliveries
        deliveries_by_promise: Dict[str, List[DeliveryEvent]] = {}
        for delivery in deliveries.values():
            if delivery.promise_id not in deliveries_by_promise:
                deliveries_by_promise[delivery.promise_id] = []
            deliveries_by_promise[delivery.promise_id].append(delivery)

        # Check each promise
        for promise_id, promise in promises.items():
            promise_deliveries = deliveries_by_promise.get(promise_id, [])

            if not promise_deliveries:
                # No delivery yet - this is OK, just note it
                continue

            # Check that deliveries happen after promise
            for delivery in promise_deliveries:
                if delivery.timestamp < promise.timestamp:
                    result.add_issue(ValidationIssue(
                        code="DELIVERY_BEFORE_PROMISE",
                        message=f"Delivery timestamp is before promise timestamp",
                        severity=ValidationSeverity.ERROR,
                        location=f"promise:{promise_id}",
                        value=f"{delivery.timestamp.isoformat()} < {promise.timestamp.isoformat()}",
                    ))
                    result.is_valid = False

        return result

    def check_chain_integrity(self, chain: List[EmailLedgerEntry]) -> ValidationResult:
        """
        Check integrity of an email chain.

        Args:
            chain: List of EmailLedgerEntry in chronological order

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)

        if not chain:
            result.add_issue(ValidationIssue(
                code="CHAIN_EMPTY",
                message="Email chain is empty",
                severity=ValidationSeverity.ERROR,
                location="chain",
                value=len(chain),
            ))
            return result

        # Check that each message references the previous one
        for i in range(1, len(chain)):
            current = chain[i]
            previous = chain[i - 1]

            # Check in_reply_to
            if current.in_reply_to != previous.message_id:
                result.add_issue(ValidationIssue(
                    code="CHAIN_REFERENCE_BROKEN",
                    message=f"Message {i} does not reply to message {i-1}",
                    severity=ValidationSeverity.WARNING,
                    location=f"chain[{i}].in_reply_to",
                    value=f"Expected {previous.message_id}, got {current.in_reply_to}",
                ))

            # Check references
            if previous.message_id not in current.references:
                result.add_issue(ValidationIssue(
                    code="CHAIN_REFERENCES_BROKEN",
                    message=f"Message {i} references do not include message {i-1}",
                    severity=ValidationSeverity.WARNING,
                    location=f"chain[{i}].references",
                    value=current.references,
                ))

            # Check timestamp order
            if current.timestamp <= previous.timestamp:
                result.add_issue(ValidationIssue(
                    code="CHAIN_TIMESTAMP_ORDER",
                    message=f"Message {i} timestamp is not after message {i-1}",
                    severity=ValidationSeverity.ERROR,
                    location=f"chain[{i}].timestamp",
                    value=f"{current.timestamp.isoformat()} <= {previous.timestamp.isoformat()}",
                ))
                result.is_valid = False

        return result


class HygieneGates:
    """
    Collection of all hygiene gates for comprehensive validation.
    """

    def __init__(self):
        """Initialize all validators."""
        self.email_validator = EmailValidator()
        self.hash_validator = HashValidator()
        self.timestamp_validator = TimestampValidator()
        self.metrics_validator = MetricsValidator()
        self.event_validator = EventValidator()
        self.integrity_checker = IntegrityChecker()

    def validate_all(self, data: Any) -> ValidationResult:
        """
        Run all applicable validators on data.

        Args:
            data: Data to validate (can be any supported type)

        Returns:
            ValidationResult with all issues
        """
        result = ValidationResult(is_valid=True)

        # Route to appropriate validator based on type
        if isinstance(data, PromiseEvent):
            sub_result = self.event_validator.validate_promise_event(data)
            result.issues.extend(sub_result.issues)
            if not sub_result.is_valid:
                result.is_valid = False

        elif isinstance(data, DeliveryEvent):
            sub_result = self.event_validator.validate_delivery_event(data)
            result.issues.extend(sub_result.issues)
            if not sub_result.is_valid:
                result.is_valid = False

        elif isinstance(data, EmailLedgerEntry):
            sub_result = self.event_validator.validate_email_entry(data)
            result.issues.extend(sub_result.issues)
            if not sub_result.is_valid:
                result.is_valid = False

        elif isinstance(data, str):
            # Try email validation
            email_result = self.email_validator.validate(data)
            result.issues.extend(email_result.issues)
            if not email_result.is_valid:
                result.is_valid = False

        elif isinstance(data, datetime):
            # Try timestamp validation
            ts_result = self.timestamp_validator.validate(data)
            result.issues.extend(ts_result.issues)
            if not ts_result.is_valid:
                result.is_valid = False

        else:
            result.add_issue(ValidationIssue(
                code="VALIDATION_NOT_SUPPORTED",
                message=f"No validator available for type {type(data)}",
                severity=ValidationSeverity.WARNING,
                location="type",
                value=type(data),
            ))

        return result
