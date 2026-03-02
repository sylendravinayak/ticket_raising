import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { ticketService } from '../services/ticketService';
import type {
  PaginatedResponse,
  TicketBrief,
  TicketCreatePayload,
  TicketDetail,
  TicketFilters,
  TicketStatusUpdatePayload,
  TicketAssignPayload,
} from '@/types';

interface TicketState {
  list: TicketBrief[];
  total: number;
  page: number;
  pageSize: number;
  currentTicket: TicketDetail | null;
  loading: boolean;
  detailLoading: boolean;
  error: string | null;
}

const initialState: TicketState = {
  list: [],
  total: 0,
  page: 1,
  pageSize: 20,
  currentTicket: null,
  loading: false,
  detailLoading: false,
  error: null,
};

// ─── Thunks ──────────────────────────────────────────────

export const fetchMyTickets = createAsyncThunk(
  'tickets/fetchMy',
  async (filters: TicketFilters, { rejectWithValue }) => {
    try {
      return await ticketService.getMyTickets(filters);
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to load tickets');
    }
  },
);

export const fetchAllTickets = createAsyncThunk(
  'tickets/fetchAll',
  async (filters: TicketFilters, { rejectWithValue }) => {
    try {
      return await ticketService.getAllTickets(filters);
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to load tickets');
    }
  },
);

export const fetchTicketDetail = createAsyncThunk(
  'tickets/fetchDetail',
  async (ticketId: number, { rejectWithValue }) => {
    try {
      return await ticketService.getTicketDetail(ticketId);
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.detail || 'Ticket not found');
    }
  },
);

export const createTicket = createAsyncThunk(
  'tickets/create',
  async (payload: TicketCreatePayload, { rejectWithValue }) => {
    try {
      return await ticketService.createTicket(payload);
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to create ticket');
    }
  },
);

export const updateTicketStatus = createAsyncThunk(
  'tickets/updateStatus',
  async (
    { ticketId, payload }: { ticketId: number; payload: TicketStatusUpdatePayload },
    { rejectWithValue },
  ) => {
    try {
      return await ticketService.updateStatus(ticketId, payload);
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.detail || 'Status update failed');
    }
  },
);

export const assignTicket = createAsyncThunk(
  'tickets/assign',
  async (
    { ticketId, payload }: { ticketId: number; payload: TicketAssignPayload },
    { rejectWithValue },
  ) => {
    try {
      return await ticketService.assignTicket(ticketId, payload);
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.detail || 'Assignment failed');
    }
  },
);

// ─── Slice ───────────────────────────────────────────────

const ticketSlice = createSlice({
  name: 'tickets',
  initialState,
  reducers: {
    clearCurrentTicket(state) {
      state.currentTicket = null;
    },
    clearTicketError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // Shared list handler
    const handleListFulfilled = (
      state: TicketState,
      action: { payload: PaginatedResponse<TicketBrief> },
    ) => {
      state.loading = false;
      state.list = action.payload.items;
      state.total = action.payload.total;
      state.page = action.payload.page;
      state.pageSize = action.payload.page_size;
    };

    // FETCH MY
    builder
      .addCase(fetchMyTickets.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchMyTickets.fulfilled, handleListFulfilled)
      .addCase(fetchMyTickets.rejected, (state, { payload }) => {
        state.loading = false;
        state.error = payload as string;
      });

    // FETCH ALL
    builder
      .addCase(fetchAllTickets.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchAllTickets.fulfilled, handleListFulfilled)
      .addCase(fetchAllTickets.rejected, (state, { payload }) => {
        state.loading = false;
        state.error = payload as string;
      });

    // DETAIL
    builder
      .addCase(fetchTicketDetail.pending, (state) => {
        state.detailLoading = true;
        state.error = null;
      })
      .addCase(fetchTicketDetail.fulfilled, (state, { payload }) => {
        state.detailLoading = false;
        state.currentTicket = payload;
      })
      .addCase(fetchTicketDetail.rejected, (state, { payload }) => {
        state.detailLoading = false;
        state.error = payload as string;
      });

    // CREATE
    builder
      .addCase(createTicket.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createTicket.fulfilled, (state) => {
        state.loading = false;
      })
      .addCase(createTicket.rejected, (state, { payload }) => {
        state.loading = false;
        state.error = payload as string;
      });

    // STATUS UPDATE
    builder
      .addCase(updateTicketStatus.fulfilled, (state, { payload }) => {
        const idx = state.list.findIndex((t) => t.ticket_id === payload.ticket_id);
        if (idx !== -1) state.list[idx] = payload;
        if (state.currentTicket?.ticket_id === payload.ticket_id) {
          state.currentTicket = { ...state.currentTicket, ...payload };
        }
      })
      .addCase(updateTicketStatus.rejected, (state, { payload }) => {
        state.error = payload as string;
      });

    // ASSIGN
    builder
      .addCase(assignTicket.fulfilled, (state, { payload }) => {
        const idx = state.list.findIndex((t) => t.ticket_id === payload.ticket_id);
        if (idx !== -1) state.list[idx] = payload;
        if (state.currentTicket?.ticket_id === payload.ticket_id) {
          state.currentTicket = { ...state.currentTicket, ...payload };
        }
      })
      .addCase(assignTicket.rejected, (state, { payload }) => {
        state.error = payload as string;
      });
  },
});

export const { clearCurrentTicket, clearTicketError } = ticketSlice.actions;
export default ticketSlice.reducer;
