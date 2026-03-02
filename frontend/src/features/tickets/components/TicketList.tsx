import { useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '@/hooks/useAppDispatch';
import { fetchMyTickets, fetchAllTickets } from '../slices/ticketSlice';
import type { TicketFilters } from '@/types';
import { USER_ROLES } from '@/config/constants';
import TicketCard from './TicketCard';
import TicketFiltersBar from './TicketFilters';
import { Plus, Ticket } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Props {
  mode: 'my' | 'all';
}

export default function TicketList({ mode }: Props) {
  const dispatch = useAppDispatch();
  const { list, total, page, pageSize, loading, error } = useAppSelector((s) => s.tickets);
  const { user } = useAppSelector((s) => s.auth);

  const [filters, setFilters] = useState<TicketFilters>({
    page: 1,
    page_size: 20,
  });

  const isAdminOrLead =
    user?.role === USER_ROLES.ADMIN || user?.role === USER_ROLES.TEAM_LEAD;

  useEffect(() => {
    if (mode === 'all' && isAdminOrLead) {
      dispatch(fetchAllTickets(filters));
    } else {
      dispatch(fetchMyTickets(filters));
    }
  }, [dispatch, mode, filters, isAdminOrLead]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {mode === 'all' ? 'All Tickets' : 'My Tickets'}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {total} ticket{total !== 1 ? 's' : ''} found
          </p>
        </div>
        {user?.role === USER_ROLES.USER && (
          <Link to="/tickets/new" className="btn-primary">
            <Plus size={18} />
            New Ticket
          </Link>
        )}
      </div>

      {/* Filters */}
      <TicketFiltersBar
        filters={filters}
        onChange={setFilters}
        showAdvanced={mode === 'all'}
      />

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <svg className="animate-spin h-8 w-8 text-indigo-600" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
      )}

      {/* List */}
      {!loading && list.length === 0 && (
        <div className="text-center py-16">
          <Ticket size={48} className="mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-medium text-gray-600">No tickets found</h3>
          <p className="text-sm text-gray-400 mt-1">
            {mode === 'my'
              ? 'You don\'t have any tickets yet.'
              : 'No tickets match the current filters.'}
          </p>
          {user?.role === USER_ROLES.USER && (
            <Link to="/tickets/new" className="btn-primary mt-4 inline-flex">
              <Plus size={18} />
              Create your first ticket
            </Link>
          )}
        </div>
      )}

      {!loading && list.length > 0 && (
        <div className="space-y-3">
          {list.map((ticket) => (
            <TicketCard key={ticket.ticket_id} ticket={ticket} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4">
          <span className="text-sm text-gray-500">
            Page {page} of {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setFilters((f) => ({ ...f, page: (f.page || 1) - 1 }))}
              className="btn-secondary text-sm"
            >
              Previous
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setFilters((f) => ({ ...f, page: (f.page || 1) + 1 }))}
              className="btn-secondary text-sm"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
