import { useEffect, useState } from 'react';
import { X, UserCheck, Users } from 'lucide-react';
import { useAppSelector } from '@/hooks/useAppDispatch';
import { USER_ROLES } from '@/config/constants';
import { authService } from '@/features/auth/services/authService';
import type { User } from '@/types';

interface Props {
  ticketId: number;
  onAssign: (assigneeId: string) => Promise<void>;
  onClose: () => void;
}

export default function AssignTicketModal({ ticketId, onAssign, onClose }: Props) {
  const { user } = useAppSelector((s) => s.auth);
  const isLead = user?.role === USER_ROLES.TEAM_LEAD;

  const [agents, setAgents] = useState<User[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState('');
  const [loadingAgents, setLoadingAgents] = useState(false);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState('');

  // Lead: fetch agents under this lead
  useEffect(() => {
    if (!isLead || !user) return;
    setLoadingAgents(true);
    authService
      .getAgentsByLeadId(user.id)
      .then((data) => {
        setAgents(data);
        if (data.length > 0) setSelectedAgentId(data[0].id);
      })
      .catch(() => setFetchError('Failed to load agents'))
      .finally(() => setLoadingAgents(false));
  }, [isLead, user]);

  const handleAssign = async () => {
    if (!selectedAgentId) return;
    setLoading(true);
    try {
      await onAssign(selectedAgentId);
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="card w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Users size={20} className="text-indigo-600" />
            Assign Ticket #{ticketId}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        {fetchError && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700 mb-4">
            {fetchError}
          </div>
        )}

        {loadingAgents ? (
          <div className="flex items-center justify-center py-8">
            <svg className="animate-spin h-6 w-6 text-indigo-600" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
        ) : (
          <div className="space-y-4">
            {isLead ? (
              <>
                {agents.length === 0 && !fetchError ? (
                  <p className="text-sm text-gray-500">No agents available under your team.</p>
                ) : (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Select Agent
                    </label>
                    <select
                      value={selectedAgentId}
                      onChange={(e) => setSelectedAgentId(e.target.value)}
                      className="input-field"
                    >
                      {agents.map((agent) => (
                        <option key={agent.id} value={agent.id}>
                          {agent.email}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </>
            ) : (
              <p className="text-sm text-gray-600">
                This ticket is in the open queue. Click below to assign it to yourself.
              </p>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={onClose} className="btn-secondary">
                Cancel
              </button>
              <button
                onClick={handleAssign}
                disabled={loading || (!selectedAgentId && isLead)}
                className="btn-primary"
              >
                {loading ? 'Assigning…' : (
                  <span className="inline-flex items-center gap-1">
                    <UserCheck size={16} /> Assign
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
