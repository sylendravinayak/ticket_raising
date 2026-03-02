import { TICKET_STATUS, SEVERITIES, PRIORITIES, type TicketStatus } from '@/config/constants';
import type { TicketFilters } from '@/types';
import { Filter, X } from 'lucide-react';

interface Props {
  filters: TicketFilters;
  onChange: (filters: TicketFilters) => void;
  showAdvanced?: boolean;
}

export default function TicketFiltersBar({ filters, onChange, showAdvanced = false }: Props) {
  const update = (partial: Partial<TicketFilters>) =>
    onChange({ ...filters, ...partial, page: 1 });

  const clearAll = () =>
    onChange({ page: 1, page_size: filters.page_size });

  const hasFilters =
    filters.status || filters.severity || filters.priority ||
    filters.is_breached !== undefined || filters.is_escalated !== undefined;

  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 mb-3">
        <Filter size={16} className="text-gray-500" />
        <span className="text-sm font-medium text-gray-700">Filters</span>
        {hasFilters && (
          <button onClick={clearAll} className="ml-auto text-xs text-indigo-600 hover:text-indigo-800 flex items-center gap-1">
            <X size={14} /> Clear all
          </button>
        )}
      </div>
      <div className="flex flex-wrap gap-3">
        {/* Status */}
        <select
          value={filters.status || ''}
          onChange={(e) => update({ status: e.target.value || undefined })}
          className="input-field w-auto min-w-[140px]"
        >
          <option value="">All Statuses</option>
          {Object.values(TICKET_STATUS).map((s) => (
            <option key={s} value={s}>{s.replace('_', ' ')}</option>
          ))}
        </select>

        {/* Severity */}
        <select
          value={filters.severity || ''}
          onChange={(e) => update({ severity: e.target.value || undefined })}
          className="input-field w-auto min-w-[130px]"
        >
          <option value="">All Severities</option>
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        {/* Priority */}
        <select
          value={filters.priority || ''}
          onChange={(e) => update({ priority: e.target.value || undefined })}
          className="input-field w-auto min-w-[120px]"
        >
          <option value="">All Priorities</option>
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>

        {showAdvanced && (
          <>
            {/* Breached */}
            <select
              value={filters.is_breached === undefined ? '' : String(filters.is_breached)}
              onChange={(e) =>
                update({
                  is_breached: e.target.value === '' ? undefined : e.target.value === 'true',
                })
              }
              className="input-field w-auto min-w-[130px]"
            >
              <option value="">SLA Status</option>
              <option value="true">Breached</option>
              <option value="false">Not Breached</option>
            </select>

            {/* Escalated */}
            <select
              value={filters.is_escalated === undefined ? '' : String(filters.is_escalated)}
              onChange={(e) =>
                update({
                  is_escalated: e.target.value === '' ? undefined : e.target.value === 'true',
                })
              }
              className="input-field w-auto min-w-[130px]"
            >
              <option value="">Escalation</option>
              <option value="true">Escalated</option>
              <option value="false">Not Escalated</option>
            </select>
          </>
        )}
      </div>
    </div>
  );
}
