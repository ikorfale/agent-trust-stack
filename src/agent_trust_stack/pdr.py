"""
Policy-Driven Recourse (PDR) Module

Handles impact assessment, recourse procedures,
and remediation tracking for incidents.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class RecourseAction(Enum):
    """Types of recourse actions."""
    MONITOR = "monitor"
    THROTTLE = "throttle"
    SUSPEND = "suspend"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"
    ROLLBACK = "rollback"
    NOTIFY_STAKEHOLDERS = "notify_stakeholders"
    REQUIRE_MANUAL_APPROVAL = "require_manual_approval"


class SeverityLevel(Enum):
    """Severity levels for incidents."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ImpactAssessment:
    """
    Assessment of the impact of an incident or action.

    Attributes:
        incident_id: Unique identifier for the incident
        agent_id: DID of the responsible agent
        action_id: ID of the problematic action
        severity: Severity level of the incident
        affected_systems: List of systems affected
        affected_users: Number of users affected
        data_breach: Whether a data breach occurred
        financial_impact: Estimated financial impact
        remediation_cost: Estimated cost of remediation
        priority: Calculated priority for incident response
    """

    incident_id: str
    agent_id: str
    action_id: str
    severity: SeverityLevel
    affected_systems: List[str]
    affected_users: int
    data_breach: bool
    financial_impact: float
    remediation_cost: float
    priority: int = 0

    def __post_init__(self):
        """Calculate priority after initialization."""
        # Higher priority for more severe incidents with more affected users
        self.priority = (
            self.severity.value * 100
            + self.affected_users
            + (1000 if self.data_breach else 0)
        )

    def to_dict(self) -> Dict:
        """Convert impact assessment to dictionary."""
        return {
            "incident_id": self.incident_id,
            "agent_id": self.agent_id,
            "action_id": self.action_id,
            "severity": self.severity.name,
            "affected_systems": self.affected_systems,
            "affected_users": self.affected_users,
            "data_breach": self.data_breach,
            "financial_impact": self.financial_impact,
            "remediation_cost": self.remediation_cost,
            "priority": self.priority,
        }

    def to_json(self) -> str:
        """Convert impact assessment to JSON."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class RemediationAction:
    """
    A single remediation action.

    Attributes:
        action: Type of recourse action
        timestamp: When the action was performed
        performed_by: DID of the entity performing the action
        details: Additional details about the action
    """

    action: RecourseAction
    timestamp: datetime
    performed_by: str
    details: Dict[str, any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert remediation action to dictionary."""
        return {
            "action": self.action.value,
            "timestamp": self.timestamp.isoformat(),
            "performed_by": self.performed_by,
            "details": self.details,
        }


@dataclass
class IncidentRecord:
    """
    Complete record of an incident and its resolution.

    Attributes:
        incident_id: Unique identifier for the incident
        agent_id: DID of the responsible agent
        action_id: ID of the problematic action
        detected_at: When the incident was detected
        impact_assessment: Impact assessment for the incident
        severity: Severity level of the incident
        remediation_actions: List of remediation actions taken
        status: Current status of the incident (detected, in_progress, resolved)
        resolved_at: When the incident was resolved
    """

    incident_id: str
    agent_id: str
    action_id: str
    detected_at: datetime
    impact_assessment: ImpactAssessment
    severity: SeverityLevel
    remediation_actions: List[RemediationAction] = field(default_factory=list)
    status: str = "detected"
    resolved_at: Optional[datetime] = None

    def add_remediation_action(self, action: RemediationAction) -> None:
        """Add a remediation action to the incident record."""
        self.remediation_actions.append(action)

    def resolve(self) -> None:
        """Mark the incident as resolved."""
        self.status = "resolved"
        self.resolved_at = datetime.utcnow()


class RecourseProcedure:
    """
    Manage Policy-Driven Recourse (PDR) procedures.

    Based on severity, execute different recourse procedures:
    - LOW: Log incident, monitor agent
    - MEDIUM: Throttle agent, require manual approval
    - HIGH: Suspend agent, notify stakeholders
    - CRITICAL: Emergency shutdown, full investigation

    Example:
        >>> pdr = RecourseProcedure()
        >>> incident = pdr.create_incident(
        ...     agent_id="did:ats:agent123",
        ...     action_id="action-bad",
        ...     severity=SeverityLevel.HIGH,
        ...     affected_systems=["data-service", "reporting"]
        ... )
        >>> pdr.execute_recourse(incident)
    """

    # Recourse procedures by severity
    RECOURSE_PROCEDURES = {
        SeverityLevel.LOW: [
            RecourseAction.MONITOR,
        ],
        SeverityLevel.MEDIUM: [
            RecourseAction.THROTTLE,
            RecourseAction.REQUIRE_MANUAL_APPROVAL,
        ],
        SeverityLevel.HIGH: [
            RecourseAction.SUSPEND,
            RecourseAction.NOTIFY_STAKEHOLDERS,
            RecourseAction.ROLLBACK,
        ],
        SeverityLevel.CRITICAL: [
            RecourseAction.EMERGENCY_SHUTDOWN,
            RecourseAction.NOTIFY_STAKEHOLDERS,
            RecourseAction.ROLLBACK,
        ],
    }

    def __init__(self, ledger_client=None):
        self.ledger_client = ledger_client
        self._incidents: Dict[str, IncidentRecord] = {}

    def create_incident(
        self,
        agent_id: str,
        action_id: str,
        severity: SeverityLevel,
        affected_systems: List[str],
        affected_users: int = 0,
        data_breach: bool = False,
        financial_impact: float = 0.0,
        remediation_cost: float = 0.0,
    ) -> IncidentRecord:
        """
        Create a new incident record with impact assessment.

        Args:
            agent_id: DID of the responsible agent
            action_id: ID of the problematic action
            severity: Severity level
            affected_systems: List of systems affected
            affected_users: Number of users affected
            data_breach: Whether a data breach occurred
            financial_impact: Estimated financial impact
            remediation_cost: Estimated remediation cost

        Returns:
            IncidentRecord
        """
        incident_id = f"inc-{datetime.utcnow().strftime('%Y-%m-%d')}-{uuid.uuid4().hex[:8]}"

        impact = ImpactAssessment(
            incident_id=incident_id,
            agent_id=agent_id,
            action_id=action_id,
            severity=severity,
            affected_systems=affected_systems,
            affected_users=affected_users,
            data_breach=data_breach,
            financial_impact=financial_impact,
            remediation_cost=remediation_cost,
        )

        incident = IncidentRecord(
            incident_id=incident_id,
            agent_id=agent_id,
            action_id=action_id,
            detected_at=datetime.utcnow(),
            impact_assessment=impact,
            severity=severity,
            status="detected",
        )

        self._incidents[incident_id] = incident

        # Store in ledger
        if self.ledger_client:
            self.ledger_client.store_incident(incident)

        return incident

    def execute_recourse(
        self,
        incident: IncidentRecord,
        performed_by: str,
    ) -> List[RemediationAction]:
        """
        Execute recourse procedure based on incident severity.

        Args:
            incident: Incident record to execute recourse for
            performed_by: DID of the entity performing the recourse

        Returns:
            List of remediation actions performed
        """
        procedure = self.RECOURSE_PROCEDURES.get(incident.severity, [])
        actions = []

        for action_type in procedure:
            action = RemediationAction(
                action=action_type,
                timestamp=datetime.utcnow(),
                performed_by=performed_by,
            )

            # Execute the action
            self._execute_action(action, incident)

            # Add to incident record
            incident.add_remediation_action(action)
            actions.append(action)

        # Store updated incident in ledger
        if self.ledger_client:
            self.ledger_client.store_incident(incident)

        return actions

    def _execute_action(self, action: RemediationAction, incident: IncidentRecord) -> None:
        """
        Execute a single remediation action.

        Args:
            action: Action to execute
            incident: Incident record
        """
        # TODO: Implement action execution
        # Each action type has specific implementation:
        #
        # MONITOR: Add agent to monitoring list
        # THROTTLE: Rate-limit agent requests
        # SUSPEND: Temporarily disable agent
        # EMERGENCY_SHUTDOWN: Immediately disable agent
        # ROLLBACK: Revert changes made by action
        # NOTIFY_STAKEHOLDERS: Send notifications
        # REQUIRE_MANUAL_APPROVAL: Set approval flag
        raise NotImplementedError(f"Action execution not yet implemented: {action.action}")

    def assess_impact(
        self,
        action_id: str,
        agent_id: str,
        affected_systems: List[str],
        affected_users: int = 0,
        data_breach: bool = False,
        financial_impact: float = 0.0,
    ) -> ImpactAssessment:
        """
        Assess the impact of an incident or action.

        Args:
            action_id: ID of the action
            agent_id: DID of the agent
            affected_systems: List of affected systems
            affected_users: Number of affected users
            data_breach: Whether a data breach occurred
            financial_impact: Estimated financial impact

        Returns:
            ImpactAssessment
        """
        # Determine severity based on impact factors
        if data_breach:
            severity = SeverityLevel.CRITICAL
        elif affected_users > 1000 or financial_impact > 100000:
            severity = SeverityLevel.HIGH
        elif affected_users > 100 or financial_impact > 10000:
            severity = SeverityLevel.MEDIUM
        else:
            severity = SeverityLevel.LOW

        # Estimate remediation cost (simplified)
        remediation_cost = financial_impact * 0.1 + affected_users * 10

        incident_id = f"inc-{datetime.utcnow().strftime('%Y-%m-%d')}-{uuid.uuid4().hex[:8]}"

        return ImpactAssessment(
            incident_id=incident_id,
            agent_id=agent_id,
            action_id=action_id,
            severity=severity,
            affected_systems=affected_systems,
            affected_users=affected_users,
            data_breach=data_breach,
            financial_impact=financial_impact,
            remediation_cost=remediation_cost,
        )

    def get_incident(self, incident_id: str) -> Optional[IncidentRecord]:
        """
        Get an incident record by ID.

        Args:
            incident_id: ID of the incident

        Returns:
            IncidentRecord if found, None otherwise
        """
        return self._incidents.get(incident_id)

    def get_incidents_for_agent(self, agent_id: str) -> List[IncidentRecord]:
        """
        Get all incidents for an agent.

        Args:
            agent_id: DID of the agent

        Returns:
            List of IncidentRecord
        """
        return [
            inc for inc in self._incidents.values()
            if inc.agent_id == agent_id
        ]
