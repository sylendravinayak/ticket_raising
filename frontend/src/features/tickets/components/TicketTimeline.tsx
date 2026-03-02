import type { TicketEvent } from '@/types';
import { formatDate } from '@/utils/formatDate';
import {
  Circle,
  CheckCircle2,
  ArrowRightLeft,
  UserCheck,
  AlertTriangle,
  ArrowUpRight,
  MessageSquare,
  RotateCcw,
  Lock,
} from 'lucide-react';

const eventIcons: Record<string, React.ReactNode> = {
  CREATED: <Circle size={16} className="text-blue-500" />,
  STATUS_CHANGED: <ArrowRightLeft size={16} className="text-yellow-500" />,
  ASSIGNED: <UserCheck size={16} className="text-green-500" />,
  PRIORITY_CHANGED: <ArrowRightLeft size={16} className="text-orange-500" />,
  SEVERITY_CHANGED: <ArrowRightLeft size={16} className="text-red-500" />,
  SLA_BREACHED: <AlertTriangle size={16} className="text-red-600" />,
  ESCALATED: <ArrowUpRight size={16} className="text-purple-500" />,
  COMMENT_ADDED: <MessageSquare size={16} className="text-gray-500" />,
  REOPENED: <RotateCcw size={16} className="text-amber-500" />,
  CLOSED: <Lock size={16} className="text-gray-500" />,
};

interface Props {
  events: TicketEvent[];
}

export default function TicketTimeline({ events }: Props) {
  if (!events.length) return null;

  return (
    <div className="card p-5">
      <h3 className="font-semibold text-gray-900 mb-4">Activity Timeline</h3>
      <ol className="relative border-l border-gray-200 ml-3 space-y-6">
        {[...events].reverse().map((ev) => (
          <li key={ev.event_id} className="ml-6">
            <span className="absolute -left-3 flex items-center justify-center w-6 h-6 rounded-full bg-white ring-4 ring-white">
              {eventIcons[ev.event_type] || <Circle size={16} className="text-gray-400" />}
            </span>
            <div>
              <p className="text-sm font-medium text-gray-900">
                {ev.event_type.replace(/_/g, ' ')}
              </p>
              {ev.field_name && (
                <p className="text-xs text-gray-500">
                  <span className="font-mono">{ev.field_name}</span>:{' '}
                  {ev.old_value && (
                    <span className="line-through text-red-400">{ev.old_value}</span>
                  )}{' '}
                  → <span className="text-green-600">{ev.new_value}</span>
                </p>
              )}
              <time className="text-xs text-gray-400 mt-0.5 block">
                {formatDate(ev.created_at)}
              </time>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
