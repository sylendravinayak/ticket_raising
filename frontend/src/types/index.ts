import type { UserRole } from '@/config/constants';

// ─── Auth Types ──────────────────────────────────────────
export interface User {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface SignupCredentials {
  email: string;
  password: string;
  role: UserRole;
}

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface SignupResponse {
  user: User;
  message: string;
}

// ─── Ticket Types ────────────────────────────────────────
export interface TicketBrief {
  ticket_id: number;
  ticket_number: string;
  title: string;
  status: string;
  severity: string;
  priority: string;
  environment: string;
  product: string;
  area_of_concern: string | null;
  source: string;
  customer_id: string;
  assignee_id: string | null;
  assigned_agent_id: number | null;
  queue_type: string;
  routing_status: string;
  sla_id: number | null;
  customer_tier_id: number | null;
  response_due_at: string | null;
  resolution_due_at: string | null;
  is_breached: boolean;
  is_escalated: boolean;
  created_at: string;
  updated_at: string;
}

export interface TicketEvent {
  event_id: number;
  ticket_id: number;
  triggered_by_user_id: string | null;
  event_type: string;
  field_name: string | null;
  old_value: string | null;
  new_value: string | null;
  comment_id: number | null;
  created_at: string;
}

export interface TicketComment {
  comment_id: number;
  ticket_id: number;
  author_id: string;
  author_role: string;
  body: string;
  is_internal: boolean;
  triggers_hold: boolean;
  triggers_resume: boolean;
  attachments: unknown[] | null;
  created_at: string;
}

export interface TicketAttachment {
  attachment_id: number;
  ticket_id: number;
  file_name: string;
  file_url: string;
  uploaded_by_user_id: string;
  uploaded_at: string;
}

export interface TicketDetail extends TicketBrief {
  description: string;
  hold_started_at: string | null;
  total_hold_minutes: number;
  resolved_at: string | null;
  closed_at: string | null;
  events: TicketEvent[];
  comments: TicketComment[];
  attachments: TicketAttachment[];
}

export interface TicketCreatePayload {
  title: string;
  description: string;
  product: string;
  environment: string;
  source?: string;
  area_of_concern?: string;
  attachments?: string[];
}

export interface TicketStatusUpdatePayload {
  new_status: string;
  comment?: string;
}

export interface TicketAssignPayload {
  assignee_id: string;
}

export interface CommentCreatePayload {
  body: string;
  is_internal?: boolean;
  triggers_hold?: boolean;
  triggers_resume?: boolean;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export interface TicketFilters {
  page?: number;
  page_size?: number;
  status?: string;
  severity?: string;
  priority?: string;
  is_breached?: boolean;
  is_escalated?: boolean;
  customer_id?: string;
  assignee_id?: string;
}
