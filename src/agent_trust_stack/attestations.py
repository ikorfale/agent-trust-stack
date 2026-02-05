"""
Attestation Chain Module

Handles hierarchical attestations, chain verification,
and revocation mechanisms.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class SeverityLevel(Enum):
    """Severity levels for attestations and incidents."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AuthorityAttestation:
    """
    An attestation from a trusted authority.

    Attributes:
        id: Unique identifier for the attestation
        type: Type of attestation
        issuer: DID of the issuing authority
        subject: DID of the subject being attested
        claims: Claims being asserted about the subject
        validity: Validity period (not_before, not_after)
        parent_attestation: ID of parent attestation in chain
        signature: Cryptographic signature
        revoked: Whether this attestation has been revoked
        revoked_at: Timestamp when attestation was revoked (if applicable)
    """

    id: str
    type: str
    issuer: str
    subject: str
    claims: Dict[str, any]
    validity: Dict[str, datetime]
    parent_attestation: Optional[str] = None
    signature: Optional[bytes] = None
    revoked: bool = False
    revoked_at: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert attestation to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "issuer": self.issuer,
            "subject": self.subject,
            "claims": self.claims,
            "validity": {
                "not_before": self.validity["not_before"].isoformat(),
                "not_after": self.validity["not_after"].isoformat(),
            },
            "parent_attestation": self.parent_attestation,
            "revoked": self.revoked,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
        }

    def to_json(self) -> str:
        """Convert attestation to JSON."""
        return json.dumps(self.to_dict(), indent=2)

    def is_valid(self) -> bool:
        """
        Check if the attestation is currently valid.

        Returns:
            True if not revoked and within validity period
        """
        if self.revoked:
            return False

        now = datetime.utcnow()
        not_before = self.validity["not_before"]
        not_after = self.validity["not_after"]

        return not_before <= now <= not_after


@dataclass
class RevocationRecord:
    """
    A revocation record for attestations.

    Attributes:
        id: Unique identifier for the revocation
        attestation_id: ID of the attestation being revoked
        revoker: DID of the entity revoking the attestation
        timestamp: When the revocation occurred
        reason: Reason for revocation
        affected_attestations: List of attestation IDs affected (transitive)
    """

    id: str
    attestation_id: str
    revoker: str
    timestamp: datetime
    reason: str
    affected_attestations: List[str] = field(default_factory=list)


class AttestationChain:
    """
    Manage hierarchical attestation chains with verification and revocation.

    Chain structure:
    Root Authority
        └── Org Authority
            └── Service Authority
                └── Agent

    Example:
        >>> chain = AttestationChain()
        >>> root_att = chain.create_attestation(
        ...     issuer="did:ats:root",
        ...     subject="did:ats:acme-corp",
        ...     claims={"type": "organization", "name": "Acme Corp"}
        ... )
        >>> org_att = chain.create_attestation(
        ...     issuer="did:ats:acme-corp",
        ...     subject="did:ats:agent123",
        ...     parent_attestation=root_att.id,
        ...     claims={"role": "data-analyst", "clearance": 3}
        ... )
        >>> is_valid = chain.verify_chain("did:ats:agent123")
    """

    def __init__(self, ledger_client=None):
        self.ledger_client = ledger_client
        self._attestations: Dict[str, AuthorityAttestation] = {}
        self._revocations: Dict[str, RevocationRecord] = {}

    def create_attestation(
        self,
        issuer: str,
        subject: str,
        claims: Dict[str, any],
        validity_days: int = 365,
        parent_attestation: Optional[str] = None,
        attestation_type: str = "AuthorityAttestation",
    ) -> AuthorityAttestation:
        """
        Create a new attestation.

        Args:
            issuer: DID of the issuing authority
            subject: DID of the subject
            claims: Claims being asserted
            validity_days: Number of days the attestation is valid
            parent_attestation: ID of parent attestation in chain
            attestation_type: Type of attestation

        Returns:
            AuthorityAttestation instance
        """
        attestation_id = f"urn:uuid:{uuid.uuid4()}"

        now = datetime.utcnow()
        validity = {
            "not_before": now,
            "not_after": now + timedelta(days=validity_days),
        }

        attestation = AuthorityAttestation(
            id=attestation_id,
            type=attestation_type,
            issuer=issuer,
            subject=subject,
            claims=claims,
            validity=validity,
            parent_attestation=parent_attestation,
        )

        # Store attestation
        self._attestations[attestation_id] = attestation

        # Store in ledger
        if self.ledger_client:
            self.ledger_client.store_attestation(attestation)

        # TODO: Sign the attestation with issuer's private key
        # attestation.signature = self._sign_attestation(attestation)

        return attestation

    def verify_chain(self, subject: str) -> bool:
        """
        Verify the complete attestation chain for a subject.

        Args:
            subject: DID of the subject to verify

        Returns:
            True if chain is valid, False otherwise
        """
        # Find all attestations for this subject
        subject_attestations = [
            att for att in self._attestations.values()
            if att.subject == subject and not att.revoked
        ]

        if not subject_attestations:
            return False  # No valid attestations

        # Verify each attestation in the chain
        for att in subject_attestations:
            if not self._verify_attestation(att):
                return False

            # If there's a parent, verify it
            if att.parent_attestation:
                parent = self._attestations.get(att.parent_attestation)
                if not parent or not parent.is_valid():
                    return False

        return True

    def _verify_attestation(self, attestation: AuthorityAttestation) -> bool:
        """
        Verify a single attestation.

        Args:
            attestation: Attestation to verify

        Returns:
            True if valid, False otherwise
        """
        # Check if within validity period
        if not attestation.is_valid():
            return False

        # Check if revoked
        if attestation.revoked:
            return False

        # TODO: Verify signature
        # if not self._verify_signature(attestation):
        #     return False

        return True

    def revoke_attestation(
        self,
        attestation_id: str,
        revoker: str,
        reason: str,
        transitive: bool = True,
    ) -> RevocationRecord:
        """
        Revoke an attestation.

        Args:
            attestation_id: ID of the attestation to revoke
            revoker: DID of the entity revoking the attestation
            reason: Reason for revocation
            transitive: Whether to revoke downstream attestations

        Returns:
            RevocationRecord
        """
        attestation = self._attestations.get(attestation_id)
        if not attestation:
            raise ValueError(f"Attestation not found: {attestation_id}")

        # Mark as revoked
        attestation.revoked = True
        attestation.revoked_at = datetime.utcnow()

        # Create revocation record
        revocation_id = f"urn:uuid:{uuid.uuid4()}"
        affected = [attestation_id]

        # Revoke downstream attestations if transitive
        if transitive:
            downstream = self._find_downstream_attestations(attestation_id)
            for att_id in downstream:
                att = self._attestations.get(att_id)
                if att:
                    att.revoked = True
                    att.revoked_at = datetime.utcnow()
                    affected.append(att_id)

        revocation = RevocationRecord(
            id=revocation_id,
            attestation_id=attestation_id,
            revoker=revoker,
            timestamp=datetime.utcnow(),
            reason=reason,
            affected_attestations=affected,
        )

        self._revocations[revocation_id] = revocation

        # Store in ledger
        if self.ledger_client:
            self.ledger_client.store_revocation(revocation)

        return revocation

    def _find_downstream_attestations(self, attestation_id: str) -> List[str]:
        """
        Find all attestations downstream of the given attestation.

        Args:
            attestation_id: ID of the attestation

        Returns:
            List of downstream attestation IDs
        """
        downstream = []

        for att in self._attestations.values():
            if att.parent_attestation == attestation_id and not att.revoked:
                downstream.append(att.id)
                downstream.extend(self._find_downstream_attestations(att.id))

        return downstream

    def get_attestations_for_subject(self, subject: str) -> List[AuthorityAttestation]:
        """
        Get all attestations for a subject.

        Args:
            subject: DID of the subject

        Returns:
            List of AuthorityAttestation
        """
        return [
            att for att in self._attestations.values()
            if att.subject == subject
        ]

    def get_chain_for_subject(self, subject: str) -> List[AuthorityAttestation]:
        """
        Get the complete attestation chain for a subject.

        Args:
            subject: DID of the subject

        Returns:
            List of AuthorityAttestation in chain order (root to leaf)
        """
        chain = []

        # Start with subject's attestations
        subject_atts = self.get_attestations_for_subject(subject)
        if not subject_atts:
            return []

        # Follow chain up to root
        current = subject_atts[0]
        while current:
            chain.insert(0, current)  # Prepend to maintain order

            if not current.parent_attestation:
                break

            current = self._attestations.get(current.parent_attestation)

        return chain

    def _sign_attestation(self, attestation: AuthorityAttestation) -> bytes:
        """
        Sign an attestation with the issuer's private key.

        Args:
            attestation: Attestation to sign

        Returns:
            Signature bytes
        """
        # TODO: Implement signing with issuer's private key
        raise NotImplementedError("Attestation signing not yet implemented")

    def _verify_signature(self, attestation: AuthorityAttestation) -> bool:
        """
        Verify an attestation's signature.

        Args:
            attestation: Attestation to verify

        Returns:
            True if signature is valid
        """
        # TODO: Implement signature verification
        raise NotImplementedError("Signature verification not yet implemented")


# Import timedelta for validity calculation
from datetime import timedelta
