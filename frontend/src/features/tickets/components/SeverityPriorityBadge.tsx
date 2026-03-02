import { cn } from '@/utils/cn';

const severityStyles: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-800',
  HIGH: 'bg-orange-100 text-orange-800',
  MEDIUM: 'bg-yellow-100 text-yellow-800',
  LOW: 'bg-green-100 text-green-800',
};

const priorityStyles: Record<string, string> = {
  P0: 'bg-red-100 text-red-800',
  P1: 'bg-orange-100 text-orange-800',
  P2: 'bg-yellow-100 text-yellow-800',
  P3: 'bg-green-100 text-green-800',
};

interface Props {
  value: string;
  type: 'severity' | 'priority';
  className?: string;
}

export default function SeverityPriorityBadge({ value, type, className }: Props) {
  const styles = type === 'severity' ? severityStyles : priorityStyles;
  return (
    <span className={cn('badge', styles[value] || 'bg-gray-100 text-gray-700', className)}>
      {value}
    </span>
  );
}
