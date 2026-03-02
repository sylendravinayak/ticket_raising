import { Link } from 'react-router-dom';
import { Clock, AlertTriangle, ArrowUpRight } from 'lucide-react';
import type { TicketBrief } from '@/types';
import TicketStatusBadge from './TicketStatusBadge';
import SeverityPriorityBadge from './SeverityPriorityBadge';
import { timeAgo } from '@/utils/formatDate';

interface Props {
  ticket: TicketBrief;
}

export default function TicketCard({ ticket }: Props) {
  return (
    <Link
      to={`/tickets/${ticket.ticket_id}`}
      className="card block p-5 hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-gray-500">{ticket.ticket_number}</span>
            <TicketStatusBadge status={ticket.status} />
            {ticket.is_breached && (
              <span className="badge bg-red-600 text-white">
                <AlertTriangle size={12} className="mr-1" />
                SLA Breached
              </span>
            )}
            {ticket.is_escalated && (
              <span className="badge bg-purple-100 text-purple-800">
                <ArrowUpRight size={12} className="mr-1" />
                Escalated
              </span>
            )}
          </div>
          <h3 className="text-sm font-semibold text-gray-900 truncate">{ticket.title}</h3>
          <p className="text-xs text-gray-500 mt-1">
            {ticket.product} · {ticket.environment}
            {ticket.area_of_concern && ` · ${ticket.area_of_concern}`}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <div className="flex gap-1">
            <SeverityPriorityBadge value={ticket.severity} type="severity" />
            <SeverityPriorityBadge value={ticket.priority} type="priority" />
          </div>
          <span className="text-xs text-gray-400 flex items-center gap-1 mt-1">
            <Clock size={12} />
            {timeAgo(ticket.created_at)}
          </span>
        </div>
      </div>
    </Link>
  );
}
