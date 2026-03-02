// ─── Roles ───────────────────────────────────────────────
export const USER_ROLES = {
  USER: 'user',
  ADMIN: 'admin',
  SUPPORT_AGENT: 'support_agent',
  TEAM_LEAD: 'team_lead',
} as const;

export type UserRole = (typeof USER_ROLES)[keyof typeof USER_ROLES];

export const ROLE_LABELS: Record<UserRole, string> = {
  user: 'Customer',
  admin: 'Admin',
  support_agent: 'Support Agent',
  team_lead: 'Team Lead',
};

// ─── Ticket Status ───────────────────────────────────────
export const TICKET_STATUS = {
  NEW: 'NEW',
  ACKNOWLEDGED: 'ACKNOWLEDGED',
  IN_PROGRESS: 'IN_PROGRESS',
  ON_HOLD: 'ON_HOLD',
  RESOLVED: 'RESOLVED',
  CLOSED: 'CLOSED',
  REOPENED: 'REOPENED',
} as const;

export type TicketStatus = (typeof TICKET_STATUS)[keyof typeof TICKET_STATUS];

export const STATUS_LABELS: Record<TicketStatus, string> = {
  NEW: 'New',
  ACKNOWLEDGED: 'Acknowledged',
  IN_PROGRESS: 'In Progress',
  ON_HOLD: 'On Hold',
  RESOLVED: 'Resolved',
  CLOSED: 'Closed',
  REOPENED: 'Reopened',
};

export const ALLOWED_TRANSITIONS: Record<TicketStatus, TicketStatus[]> = {
  NEW: ['ACKNOWLEDGED'],
  ACKNOWLEDGED: ['IN_PROGRESS'],
  IN_PROGRESS: ['ON_HOLD', 'RESOLVED'],
  ON_HOLD: ['IN_PROGRESS'],
  RESOLVED: ['CLOSED'],
  CLOSED: ['REOPENED'],
  REOPENED: ['ACKNOWLEDGED'],
};

// ─── Severity / Priority ────────────────────────────────
export const SEVERITIES = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const;
export type Severity = (typeof SEVERITIES)[number];

export const PRIORITIES = ['P0', 'P1', 'P2', 'P3'] as const;
export type Priority = (typeof PRIORITIES)[number];

// ─── Environment ─────────────────────────────────────────
export const ENVIRONMENTS = ['PROD', 'STAGE', 'DEV'] as const;
export type Environment = (typeof ENVIRONMENTS)[number];

// ─── Ticket Source ───────────────────────────────────────
export const TICKET_SOURCES = ['UI', 'EMAIL'] as const;
export type TicketSource = (typeof TICKET_SOURCES)[number];

// ─── Date Formats ────────────────────────────────────────
export const DATE_FORMATS = {
  SHORT: 'MMM dd, yyyy',
  LONG: 'MMMM dd, yyyy HH:mm',
  RELATIVE: 'relative',
} as const;

// ─── Pagination ──────────────────────────────────────────
export const DEFAULT_PAGE_SIZE = 20;
