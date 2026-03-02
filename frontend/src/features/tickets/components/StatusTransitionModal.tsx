import { useState } from 'react';
import { ALLOWED_TRANSITIONS, type TicketStatus } from '@/config/constants';
import { X, ArrowRightLeft } from 'lucide-react';

interface Props {
  ticketId: number;
  currentStatus: string;
  onTransition: (newStatus: string, comment?: string) => Promise<void>;
  onClose: () => void;
}

export default function StatusTransitionModal({
  ticketId,
  currentStatus,
  onTransition,
  onClose,
}: Props) {
  const allowedNext = ALLOWED_TRANSITIONS[currentStatus as TicketStatus] || [];
  const [selectedStatus, setSelectedStatus] = useState<string>(allowedNext[0] || '');
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!selectedStatus) return;
    setLoading(true);
    try {
      await onTransition(selectedStatus, comment || undefined);
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="card w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Update Status — Ticket #{ticketId}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        {allowedNext.length === 0 ? (
          <p className="text-sm text-gray-500">
            No transitions available from <strong>{currentStatus}</strong>.
          </p>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                New Status
              </label>
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="input-field"
              >
                {allowedNext.map((s) => (
                  <option key={s} value={s}>
                    {s.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Comment <span className="text-gray-400">(optional)</span>
              </label>
              <textarea
                rows={3}
                maxLength={2000}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Add a note about this transition..."
                className="input-field resize-y"
              />
            </div>

            <div className="flex justify-end gap-3">
              <button onClick={onClose} className="btn-secondary">
                Cancel
              </button>
              <button onClick={handleSubmit} disabled={loading} className="btn-primary">
                {loading ? 'Updating…' : (
                  <span className="inline-flex items-center gap-1">
                    <ArrowRightLeft size={16} /> Transition
                  </span>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
