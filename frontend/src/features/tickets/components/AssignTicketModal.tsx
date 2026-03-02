import { useState, type FormEvent } from 'react';
import { X, UserCheck } from 'lucide-react';

interface Props {
  ticketId: number;
  currentAssignee: string | null;
  onAssign: (assigneeId: string) => Promise<void>;
  onClose: () => void;
}

export default function AssignTicketModal({ ticketId, currentAssignee, onAssign, onClose }: Props) {
  const [assigneeId, setAssigneeId] = useState(currentAssignee || '');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!assigneeId.trim()) return;
    setLoading(true);
    try {
      await onAssign(assigneeId.trim());
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
            Assign Ticket #{ticketId}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Agent User ID
            </label>
            
          </div>

          <div className="flex justify-end gap-3">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? 'Assigning…' : (
                <span className="inline-flex items-center gap-1">
                  <UserCheck size={16} /> Assign
                </span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
