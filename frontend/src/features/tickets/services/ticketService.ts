import api from '@/lib/axios';
import { ENV } from '@/config/env';
import type {
  CommentCreatePayload,
  PaginatedResponse,
  TicketAssignPayload,
  TicketBrief,
  TicketCreatePayload,
  TicketDetail,
  TicketFilters,
  TicketStatusUpdatePayload,
} from '@/types';

const URL = ENV.TICKET_API_URL;

function filtersToParams(f: TicketFilters): Record<string, string> {
  const p: Record<string, string> = {};
  if (f.page) p.page = String(f.page);
  if (f.page_size) p.page_size = String(f.page_size);
  if (f.status) p.status = f.status;
  if (f.severity) p.severity = f.severity;
  if (f.priority) p.priority = f.priority;
  if (f.is_breached !== undefined) p.is_breached = String(f.is_breached);
  if (f.is_escalated !== undefined) p.is_escalated = String(f.is_escalated);
  if (f.customer_id) p.customer_id = f.customer_id;
  if (f.assignee_id) p.assignee_id = f.assignee_id;
  return p;
}

export const ticketService = {
  async createTicket(payload: TicketCreatePayload): Promise<TicketDetail> {
    const { data } = await api.post<TicketDetail>(URL, payload);
    return data;
  },

  async getMyTickets(filters: TicketFilters = {}): Promise<PaginatedResponse<TicketBrief>> {
    const { data } = await api.get<PaginatedResponse<TicketBrief>>(`${URL}/me`, {
      params: filtersToParams(filters),
    });
    return data;
  },

  async getAllTickets(filters: TicketFilters = {}): Promise<PaginatedResponse<TicketBrief>> {
    const { data } = await api.get<PaginatedResponse<TicketBrief>>(URL, {
      params: filtersToParams(filters),
    });
    return data;
  },

  async getTicketDetail(ticketId: number): Promise<TicketDetail> {
    const { data } = await api.get<TicketDetail>(`${URL}/${ticketId}`);
    return data;
  },

  async updateStatus(ticketId: number, payload: TicketStatusUpdatePayload): Promise<TicketBrief> {
    const { data } = await api.put<TicketBrief>(`${URL}/${ticketId}/status`, payload);
    return data;
  },

  async assignTicket(ticketId: number, payload: TicketAssignPayload): Promise<TicketBrief> {
    const { data } = await api.post<TicketBrief>(`${URL}/${ticketId}/assign`, payload);
    return data;
  },

  async addComment(ticketId: number, payload: CommentCreatePayload): Promise<TicketDetail> {
    const { data } = await api.post<TicketDetail>(`${URL}/${ticketId}/comments`, payload);
    return data;
  },
};
