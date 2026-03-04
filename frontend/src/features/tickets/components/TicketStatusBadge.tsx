import { cn } from '@/utils/cn';
import { TICKET_STATUS, STATUS_LABELS, type TicketStatus } from '@/config/constants';

const statusStyles: Record<TicketStatus, string> = {
  [TICKET_STATUS.NEW]: 'bg-blue-100 text-blue-800',
  [TICKET_STATUS.ACKNOWLEDGED]: 'bg-cyan-100 text-cyan-800',
  [TICKET_STATUS.OPEN]: 'bg-indigo-100 text-indigo-800',
  [TICKET_STATUS.IN_PROGRESS]: 'bg-yellow-100 text-yellow-800',
  [TICKET_STATUS.ON_HOLD]: 'bg-orange-100 text-orange-800',
  [TICKET_STATUS.RESOLVED]: 'bg-green-100 text-green-800',
  [TICKET_STATUS.CLOSED]: 'bg-gray-100 text-gray-800',
  [TICKET_STATUS.REOPENED]: 'bg-red-100 text-red-800',
};

interface Props {
  status: string;
  className?: string;
}

export default function TicketStatusBadge({ status, className }: Props) {
  const key = status as TicketStatus;
  return (
    <span className={cn('badge', statusStyles[key] || 'bg-gray-100 text-gray-700', className)}>
      {STATUS_LABELS[key] || status}
    </span>
  );
}
