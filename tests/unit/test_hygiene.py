"""
Unit tests for Hygiene gates module.
"""

import pytest
from datetime import datetime, timedelta

from agent_trust_stack.hygiene import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    EmailValidator,
    HashValidator,
    TimestampValidator,
    MetricsValidator,
    EventValidator,
    IntegrityChecker,
    HygieneGates,
)
from agent_trust_stack.ledger import (
    EmailLedgerEntry,
    PromiseEvent,
    DeliveryEvent,
    DeliveryOutcome,
    ImpactTier,
)


class TestValidationIssue:
    """Tests for ValidationIssue."""

    def test_create_issue(self):
        """Test creating a validation issue."""
        issue = ValidationIssue(
            code="TEST_ERROR",
            message="Test error message",
            severity=ValidationSeverity.ERROR,
            location="test_field",
            value="invalid_value",
        )

        assert issue.code == "TEST_ERROR"
        assert issue.message == "Test error message"
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.location == "test_field"
        assert issue.value == "invalid_value"

    def test_to_dict(self):
        """Test converting issue to dictionary."""
        issue = ValidationIssue(
            code="TEST_ERROR",
            message="Test error",
            severity=ValidationSeverity.ERROR,
            location="field",
            value="value",
        )

        data = issue.to_dict()

        assert data["code"] == "TEST_ERROR"
        assert data["message"] == "Test error"
        assert data["severity"] == "error"
        assert data["location"] == "field"
        assert data["value"] == "value"


class TestValidationResult:
    """Tests for ValidationResult."""

    def test_initial_state(self):
        """Test initial validation result state."""
        result = ValidationResult(is_valid=True)

        assert result.is_valid is True
        assert len(result.issues) == 0
        assert len(result.get_errors()) == 0
        assert len(result.get_warnings()) == 0

    def test_add_warning(self):
        """Test adding a warning issue."""
        result = ValidationResult(is_valid=True)

        result.add_issue(ValidationIssue(
            code="WARN",
            message="Warning",
            severity=ValidationSeverity.WARNING,
            location="field",
            value="value",
        ))

        assert result.is_valid is True  # Warnings don't invalidate
        assert len(result.issues) == 1
        assert len(result.get_warnings()) == 1
        assert len(result.get_errors()) == 0

    def test_add_error(self):
        """Test adding an error issue."""
        result = ValidationResult(is_valid=True)

        result.add_issue(ValidationIssue(
            code="ERROR",
            message="Error",
            severity=ValidationSeverity.ERROR,
            location="field",
            value="value",
        ))

        assert result.is_valid is False
        assert len(result.issues) == 1
        assert len(result.get_errors()) == 1
        assert len(result.get_warnings()) == 0

    def test_add_critical(self):
        """Test adding a critical issue."""
        result = ValidationResult(is_valid=True)

        result.add_issue(ValidationIssue(
            code="CRITICAL",
            message="Critical error",
            severity=ValidationSeverity.CRITICAL,
            location="field",
            value="value",
        ))

        assert result.is_valid is False
        assert len(result.get_errors()) == 1

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = ValidationResult(is_valid=True)

        result.add_issue(ValidationIssue(
            code="WARN",
            message="Warning",
            severity=ValidationSeverity.WARNING,
            location="field",
            value="value",
        ))

        data = result.to_dict()

        assert data["is_valid"] is True
        assert len(data["issues"]) == 1
        assert data["warning_count"] == 1
        assert data["error_count"] == 0


class TestEmailValidator:
    """Tests for EmailValidator."""

    def test_valid_email(self):
        """Test validation of valid email."""
        validator = EmailValidator()
        result = validator.validate("user@example.com")

        assert result.is_valid is True
        assert len(result.issues) == 0

    def test_invalid_email_format(self):
        """Test validation of invalid email format."""
        validator = EmailValidator()
        result = validator.validate("invalid-email")

        assert result.is_valid is False
        assert len(result.issues) == 1
        assert result.issues[0].code == "EMAIL_FORMAT"

    def test_empty_email(self):
        """Test validation of empty email."""
        validator = EmailValidator()
        result = validator.validate("")

        assert result.is_valid is False
        assert len(result.issues) == 1
        assert result.issues[0].code == "EMAIL_EMPTY"

    def test_valid_dkim_signer(self):
        """Test validation of valid DKIM signer."""
        validator = EmailValidator()
        result = validator.validate_dkim_signer("selector1.example.com")

        assert result.is_valid is True
        assert len(result.issues) == 0

    def test_invalid_dkim_signer(self):
        """Test validation of invalid DKIM signer."""
        validator = EmailValidator()
        result = validator.validate_dkim_signer("invalid")

        assert result.is_valid is False
        assert len(result.issues) == 1
        assert result.issues[0].code == "DKIM_FORMAT"


class TestHashValidator:
    """Tests for HashValidator."""

    def test_valid_sha256_hash(self):
        """Test validation of valid SHA-256 hash."""
        validator = HashValidator()
        valid_hash = "a" * 64  # 64 hex characters
        result = validator.validate(valid_hash)

        assert result.is_valid is True
        assert len(result.issues) == 0

    def test_invalid_hash_length(self):
        """Test validation of invalid hash length."""
        validator = HashValidator()
        result = validator.validate("abc")

        assert result.is_valid is False
        assert len(result.issues) == 1
        assert result.issues[0].code == "HASH_FORMAT"

    def test_invalid_hash_chars(self):
        """Test validation of hash with invalid characters."""
        validator = HashValidator()
        invalid_hash = "a" * 63 + "z"  # 64 chars but one is not hex
        result = validator.validate(invalid_hash)

        assert result.is_valid is False
        assert len(result.issues) == 1
        assert result.issues[0].code == "HASH_FORMAT"


class TestTimestampValidator:
    """Tests for TimestampValidator."""

    def test_valid_timestamp(self):
        """Test validation of valid timestamp."""
        validator = TimestampValidator()
        result = validator.validate(datetime.utcnow())

        assert result.is_valid is True
        assert len(result.issues) == 0

    def test_future_timestamp(self):
        """Test validation of future timestamp."""
        validator = TimestampValidator()
        future = datetime.utcnow() + timedelta(days=400)  # More than 1 year
        result = validator.validate(future)

        assert result.is_valid is False
        assert len(result.issues) == 1
        assert result.issues[0].code == "TIMESTAMP_FUTURE"

    def test_old_timestamp_warning(self):
        """Test validation of old timestamp (should be warning, not error)."""
        validator = TimestampValidator()
        old = datetime.utcnow() - timedelta(days=400)  # More than 1 year
        result = validator.validate(old)

        assert result.is_valid is True  # Old timestamps are warnings, not errors
        assert len(result.issues) == 1
        assert result.issues[0].code == "TIMESTAMP_TOO_OLD"
        assert result.issues[0].severity == ValidationSeverity.WARNING

    def test_timestamp_order_valid(self):
        """Test validation of correct timestamp order."""
        validator = TimestampValidator()
        earlier = datetime.utcnow() - timedelta(hours=1)
        later = datetime.utcnow()

        result = validator.validate_order(earlier, later, "start", "end")

        assert result.is_valid is True
        assert len(result.issues) == 0

    def test_timestamp_order_invalid(self):
        """Test validation of incorrect timestamp order."""
        validator = TimestampValidator()
        earlier = datetime.utcnow()
        later = datetime.utcnow() - timedelta(hours=1)

        result = validator.validate_order(earlier, later, "start", "end")

        assert result.is_valid is False
        assert len(result.issues) == 1
        assert result.issues[0].code == "TIMESTAMP_ORDER"


class TestMetricsValidator:
    """Tests for MetricsValidator."""

    def test_valid_metric(self):
        """Test validation of valid metric value."""
        validator = MetricsValidator()
        result = validator.validate_range(0.5, 0.0, 1.0, "pdr")

        assert result.is_valid is True
        assert len(result.issues) == 0

    def test_metric_too_low(self):
        """Test validation of metric value below minimum."""
        validator = MetricsValidator()
        result = validator.validate_range(-0.1, 0.0, 1.0, "pdr")

        assert result.is_valid is False
        assert len(result.issues) == 1
        assert result.issues[0].code == "METRIC_TOO_LOW"

    def test_metric_too_high(self):
        """Test validation of metric value above maximum."""
        validator = MetricsValidator()
        result = validator.validate_range(1.5, 0.0, 1.0, "pdr")

        assert result.is_valid is False
        assert len(result.issues) == 1
        assert result.issues[0].code == "METRIC_TOO_HIGH"

    def test_validate_multiple_metrics(self):
        """Test validation of multiple metrics."""
        validator = MetricsValidator()
        metrics = {
            "pdr": 0.9,
            "dependency_impact": 0.2,
            "mdr": 0.05,
        }

        result = validator.validate_metrics(metrics)

        assert result.is_valid is True
        assert len(result.issues) == 0

    def test_validate_invalid_metrics(self):
        """Test validation of invalid metrics."""
        validator = MetricsValidator()
        metrics = {
            "pdr": 0.9,
            "dependency_impact": 1.5,  # Invalid
            "mdr": 0.05,
        }

        result = validator.validate_metrics(metrics)

        assert result.is_valid is False
        # Should have at least one error for dependency_impact
        errors = result.get_errors()
        assert len(errors) > 0


class TestEventValidator:
    """Tests for EventValidator."""

    def test_validate_valid_promise(self):
        """Test validation of valid promise event."""
        validator = EventValidator()
        promise = PromiseEvent.create(
            agent_id="did:ats:agent123",
            promise_text="I will deliver the report",
            impact_tier=ImpactTier.HIGH,
        )

        result = validator.validate_promise_event(promise)

        assert result.is_valid is True
        assert len(result.issues) == 0

    def test_validate_promise_empty_agent_id(self):
        """Test validation of promise with empty agent ID."""
        validator = EventValidator()
        promise = PromiseEvent(
            id="promise-1",
            agent_id="",
            promise_text="Test",
            impact_tier=ImpactTier.HIGH,
            timestamp=datetime.utcnow(),
        )

        result = validator.validate_promise_event(promise)

        assert result.is_valid is False
        errors = result.get_errors()
        assert len(errors) > 0
        assert any(e.code == "AGENT_ID_INVALID" for e in errors)

    def test_validate_valid_delivery(self):
        """Test validation of valid delivery event."""
        validator = EventValidator()
        delivery = DeliveryEvent.create(
            promise_id="promise-123",
            outcome=DeliveryOutcome.DELIVERED,
        )

        result = validator.validate_delivery_event(delivery)

        assert result.is_valid is True
        assert len(result.issues) == 0

    def test_validate_partial_delivery_without_amounts(self):
        """Test validation of partial delivery without amounts."""
        validator = EventValidator()
        delivery = DeliveryEvent.create(
            promise_id="promise-123",
            outcome=DeliveryOutcome.PARTIAL,
            # Missing delivered_amount and expected_amount
        )

        result = validator.validate_delivery_event(delivery)

        assert result.is_valid is False
        errors = result.get_errors()
        assert any(e.code == "PARTIAL_DELIVERY_AMOUNTS_MISSING" for e in errors)

    def test_validate_valid_email_entry(self):
        """Test validation of valid email entry."""
        validator = EventValidator()
        entry = EmailLedgerEntry.create(
            message_id="test@example.com",
            from_addr="sender@example.com",
            to_addr="recipient@example.com",
            timestamp=datetime.utcnow(),
            signer="selector1.example.com",
            body="Test email body",
            headers={"Subject": "Test"},
        )

        result = validator.validate_email_entry(entry)

        assert result.is_valid is True
        assert len(result.issues) == 0

    def test_validate_email_invalid_from(self):
        """Test validation of email entry with invalid from address."""
        validator = EventValidator()
        entry = EmailLedgerEntry.create(
            message_id="test@example.com",
            from_addr="invalid-email",  # Invalid format
            to_addr="recipient@example.com",
            timestamp=datetime.utcnow(),
            signer="selector1.example.com",
            body="Test",
            headers={"Subject": "Test"},
        )

        result = validator.validate_email_entry(entry)

        assert result.is_valid is False
        errors = result.get_errors()
        assert any(e.code == "EMAIL_FORMAT" for e in errors)


class TestHygieneGates:
    """Tests for HygieneGates."""

    def test_validate_promise_event(self):
        """Test validating promise through hygiene gates."""
        gates = HygieneGates()

        promise = PromiseEvent.create(
            agent_id="did:ats:agent123",
            promise_text="Test promise",
            impact_tier=ImpactTier.HIGH,
        )

        result = gates.validate_all(promise)

        assert result.is_valid is True

    def test_validate_email_address(self):
        """Test validating email address through hygiene gates."""
        gates = HygieneGates()

        result = gates.validate_all("user@example.com")

        assert result.is_valid is True

    def test_validate_invalid_email_address(self):
        """Test validating invalid email address through hygiene gates."""
        gates = HygieneGates()

        result = gates.validate_all("invalid-email")

        assert result.is_valid is False

    def test_validate_timestamp(self):
        """Test validating timestamp through hygiene gates."""
        gates = HygieneGates()

        result = gates.validate_all(datetime.utcnow())

        assert result.is_valid is True
