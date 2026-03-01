import enum


class TicketStatus(str, enum.Enum):
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class Priority(str, enum.Enum):
    P0 = "P0"   
    P1 = "P1"   # High — major feature broken
    P2 = "P2"   # Medium — degraded experience
    P3 = "P3"   # Low — minor issue
    P4 = "P4"   # Trivial — cosmetic / nice to have


class Severity(str, enum.Enum):
    CRITICAL = "CRITICAL"   # Complete outage / data loss
    HIGH = "HIGH"           # Major functionality broken
    MEDIUM = "MEDIUM"       # Partial impact, workaround exists
    LOW = "LOW"             # Minor impact
    TRIVIAL = "TRIVIAL"     # Cosmetic / informational


class Channel(str, enum.Enum):
    UI = "UI"
    EMAIL = "EMAIL"


class EventType(str, enum.Enum):
    CREATED = "CREATED"
    STATUS_CHANGED = "STATUS_CHANGED"
    PRIORITY_CHANGED = "PRIORITY_CHANGED"
    SEVERITY_CHANGED = "SEVERITY_CHANGED"
    AGENT_ASSIGNED = "AGENT_ASSIGNED"
    AGENT_REASSIGNED = "AGENT_REASSIGNED"
    SLA_ASSIGNED = "SLA_ASSIGNED"
    SLA_BREACHED = "SLA_BREACHED"
    ESCALATED = "ESCALATED"
    COMMENT_ADDED = "COMMENT_ADDED"
    REOPENED = "REOPENED"
    CLOSED = "CLOSED"


class CustomerTier(str, enum.Enum):
    FREE = "FREE"
    STANDARD = "STANDARD"
    ENTERPRISE = "ENTERPRISE"


class ActorRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    AGENT = "AGENT"
    LEAD = "LEAD"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"