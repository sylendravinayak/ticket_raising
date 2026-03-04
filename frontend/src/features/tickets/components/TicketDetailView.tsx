import { useEffect, useState, type FormEvent } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@/hooks/useAppDispatch';
import {
  fetchTicketDetail,
  updateTicketStatus,
  assignTicket,
  addComment,
  clearCurrentTicket,
} from '../slices/ticketSlice';
import { USER_ROLES, ALLOWED_TRANSITIONS, type TicketStatus } from '@/config/constants';
import TicketStatusBadge from './TicketStatusBadge';
import SeverityPriorityBadge from './SeverityPriorityBadge';
import TicketTimeline from './TicketTimeline';
import StatusTransitionModal from './StatusTransitionModal';
import AssignTicketModal from './AssignTicketModal';
import { formatDate } from '@/utils/formatDate';
import {
  ArrowLeft,
  ArrowRightLeft,
  UserCheck,
  AlertTriangle,
  ArrowUpRight,
  Clock,
  Shield,
  Paperclip,
  Send,
  MessageSquare,
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function TicketDetailView() {
  const { ticketId } = useParams<{ ticketId: string }>();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { currentTicket: ticket, detailLoading, error } = useAppSelector((s) => s.tickets);
  const { user } = useAppSelector((s) => s.auth);

  const [showStatusModal, setShowStatusModal] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);

  // Comment form state
  const [commentBody, setCommentBody] = useState('');
  const [isInternal, setIsInternal] = useState(false);
  const [commentLoading, setCommentLoading] = useState(false);

  useEffect(() => {
    if (ticketId) dispatch(fetchTicketDetail(Number(ticketId)));
    return () => { dispatch(clearCurrentTicket()); };
  }, [dispatch, ticketId]);

  if (detailLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <svg className="animate-spin h-10 w-10 text-indigo-600" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto py-10">
        <div className="rounded-lg bg-red-50 border border-red-200 p-6 text-center">
          <p className="text-red-700 font-medium">{error}</p>
          <button onClick={() => navigate(-1)} className="btn-secondary mt-4">
            <ArrowLeft size={16} /> Go Back
          </button>
        </div>
      </div>
    );
  }

  if (!ticket) return null;

  const isCustomer = user?.role === USER_ROLES.USER;
  const isAgent = user?.role === USER_ROLES.SUPPORT_AGENT;
  const isLead = user?.role === USER_ROLES.TEAM_LEAD;
  const isAdmin = user?.role === USER_ROLES.ADMIN;
  const isLeadOrAdmin = isLead || isAdmin;

  // Status transition: only non-customers can transition, and only if there are valid next states
  const canTransition = !isCustomer;
  const hasNextStates = (ALLOWED_TRANSITIONS[ticket.status as TicketStatus] || []).length > 0;

  // Assignment logic:
  // - Agent: can ONLY self-assign, and ONLY if ticket is in OPEN queue (queue_type === 'OPEN')
  // - Lead: can assign to agents ONLY if the ticket is currently assigned to them (assignee_id === lead's user id)
  // - Admin: can assign to anyone (always shown)
  const isOpenQueue = ticket.queue_type === 'OPEN';
  const canAgentSelfAssign = isAgent && isOpenQueue && ticket.assignee_id !== user?.id;
  const canLeadAssign = isLead && ticket.assignee_id === user?.id;
  const canAdminAssign = isAdmin;
  const showAssignButton = canAgentSelfAssign || canLeadAssign || canAdminAssign;

  const handleTransition = async (newStatus: string, comment?: string) => {
    const result = await dispatch(
      updateTicketStatus({
        ticketId: ticket.ticket_id,
        payload: { new_status: newStatus, comment },
      }),
    );
    if (updateTicketStatus.fulfilled.match(result)) {
      toast.success(`Status → ${newStatus.replace(/_/g, ' ')}`);
      dispatch(fetchTicketDetail(ticket.ticket_id));
    } else {
      toast.error((result.payload as string) || 'Transition failed');
    }
  };

  const handleAssign = async (assigneeId: string) => {
    const result = await dispatch(
      assignTicket({
        ticketId: ticket.ticket_id,
        payload: { assignee_id: assigneeId },
      }),
    );
    if (assignTicket.fulfilled.match(result)) {
      toast.success('Ticket assigned');
      dispatch(fetchTicketDetail(ticket.ticket_id));
    } else {
      toast.error((result.payload as string) || 'Assignment failed');
    }
  };

  // Agent self-assign shortcut (no modal needed)
  const handleSelfAssign = async () => {
    if (!user) return;
    await handleAssign(user.id);
  };

  const handleAddComment = async (e: FormEvent) => {
    e.preventDefault();
    if (!commentBody.trim()) return;
    setCommentLoading(true);
    const result = await dispatch(
      addComment({
        ticketId: ticket.ticket_id,
        payload: {
          body: commentBody.trim(),
          is_internal: isInternal,
        },
      }),
    );
    if (addComment.fulfilled.match(result)) {
      toast.success('Comment added');
      setCommentBody('');
      setIsInternal(false);
    } else {
      toast.error((result.payload as string) || 'Failed to add comment');
    }
    setCommentLoading(false);
  };

  // Filter internal comments for customers
  const visibleComments = isCustomer
    ? ticket.comments.filter((c) => !c.is_internal)
    : ticket.comments;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Back */}
      <button onClick={() => navigate(-1)} className="btn-ghost text-sm -ml-2">
        <ArrowLeft size={16} /> Back to tickets
      </button>

      {/* Header */}
      <div className="card p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <span className="text-sm font-mono text-gray-500">{ticket.ticket_number}</span>
              <TicketStatusBadge status={ticket.status} />
              <SeverityPriorityBadge value={ticket.severity} type="severity" />
              <SeverityPriorityBadge value={ticket.priority} type="priority" />
              {ticket.is_breached && (
                <span className="badge bg-red-600 text-white">
                  <AlertTriangle size={12} className="mr-1" /> SLA Breached
                </span>
              )}
              {ticket.is_escalated && (
                <span className="badge bg-purple-100 text-purple-800">
                  <ArrowUpRight size={12} className="mr-1" /> Escalated
                </span>
              )}
            </div>
            <h1 className="text-xl font-bold text-gray-900">{ticket.title}</h1>
          </div>

          {/* Actions — only relevant buttons per role */}
          <div className="flex gap-2 shrink-0">
            {canTransition && hasNextStates && (
              <button onClick={() => setShowStatusModal(true)} className="btn-primary text-sm">
                <ArrowRightLeft size={16} /> Change Status
              </button>
            )}
            {canAgentSelfAssign && (
              <button onClick={handleSelfAssign} className="btn-secondary text-sm">
                <UserCheck size={16} /> Self-Assign
              </button>
            )}
            {(canLeadAssign || canAdminAssign) && (
              <button onClick={() => setShowAssignModal(true)} className="btn-secondary text-sm">
                <UserCheck size={16} /> Assign
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Info Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="card p-5 space-y-3">
          <h3 className="font-semibold text-gray-900 text-sm uppercase tracking-wider">Details</h3>
          <InfoRow label="Product" value={ticket.product} />
          <InfoRow label="Environment" value={ticket.environment} />
          <InfoRow label="Source" value={ticket.source} />
          {ticket.area_of_concern && (
            <InfoRow label="Area of Concern" value={ticket.area_of_concern} />
          )}
          <InfoRow label="Queue" value={ticket.queue_type} />
          <InfoRow label="Routing" value={ticket.routing_status} />
          {ticket.assignee_id && (
            <InfoRow label="Assignee" value={ticket.assignee_id} mono />
          )}
        </div>

        <div className="card p-5 space-y-3">
          <h3 className="font-semibold text-gray-900 text-sm uppercase tracking-wider">SLA & Dates</h3>
          <InfoRow
            label="Response Due"
            value={formatDate(ticket.response_due_at)}
            icon={<Clock size={14} />}
          />
          <InfoRow
            label="Resolution Due"
            value={formatDate(ticket.resolution_due_at)}
            icon={<Clock size={14} />}
          />
          <InfoRow label="Created" value={formatDate(ticket.created_at)} />
          <InfoRow label="Updated" value={formatDate(ticket.updated_at)} />
          {ticket.resolved_at && <InfoRow label="Resolved" value={formatDate(ticket.resolved_at)} />}
          {ticket.closed_at && <InfoRow label="Closed" value={formatDate(ticket.closed_at)} />}
          {ticket.total_hold_minutes > 0 && (
            <InfoRow label="Total Hold" value={`${ticket.total_hold_minutes} min`} />
          )}
        </div>
      </div>

      {/* Description */}
      <div className="card p-6">
        <h3 className="font-semibold text-gray-900 mb-3">Description</h3>
        <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
          {ticket.description}
        </p>
      </div>

      {/* Attachments */}
      {ticket.attachments.length > 0 && (
        <div className="card p-5">
          <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <Paperclip size={16} /> Attachments
          </h3>
          <ul className="space-y-2">
            {ticket.attachments.map((att) => (
              <li key={att.attachment_id} className="text-sm">
                <a
                  href={att.file_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-600 hover:underline"
                >
                  {att.file_name}
                </a>
                <span className="text-xs text-gray-400 ml-2">
                  {formatDate(att.uploaded_at)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Comments */}
      <div className="card p-5">
        <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <MessageSquare size={16} /> Comments ({visibleComments.length})
        </h3>

        {visibleComments.length > 0 && (
          <div className="space-y-4 mb-6">
            {visibleComments.map((c) => (
              <div
                key={c.comment_id}
                className={`rounded-lg p-4 ${c.is_internal ? 'bg-yellow-50 border border-yellow-200' : 'bg-gray-50 border border-gray-200'}`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-medium text-gray-700">
                    {c.author_role}
                  </span>
                  {c.is_internal && (
                    <span className="badge bg-yellow-200 text-yellow-800">
                      <Shield size={10} className="mr-0.5" /> Internal
                    </span>
                  )}
                  <span className="text-xs text-gray-400 ml-auto">
                    {formatDate(c.created_at)}
                  </span>
                </div>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{c.body}</p>
              </div>
            ))}
          </div>
        )}

        {visibleComments.length === 0 && (
          <p className="text-sm text-gray-400 mb-6">No comments yet.</p>
        )}

        {/* Add Comment Form */}
        {ticket.status !== 'CLOSED' && (
          <form onSubmit={handleAddComment} className="border-t border-gray-200 pt-4 space-y-3">
            <textarea
              rows={3}
              maxLength={5000}
              value={commentBody}
              onChange={(e) => setCommentBody(e.target.value)}
              placeholder="Add a comment…"
              className="input-field resize-y"
              required
            />
            <div className="flex items-center justify-between">
              {!isCustomer && (
                <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={isInternal}
                    onChange={(e) => setIsInternal(e.target.checked)}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  Internal note
                </label>
              )}
              {isCustomer && <div />}
              <button
                type="submit"
                disabled={commentLoading || !commentBody.trim()}
                className="btn-primary text-sm"
              >
                {commentLoading ? 'Posting…' : (
                  <span className="inline-flex items-center gap-1">
                    <Send size={14} /> Post Comment
                  </span>
                )}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Timeline */}
      <TicketTimeline events={ticket.events} />

      {/* Modals */}
      {showStatusModal && (
        <StatusTransitionModal
          ticketId={ticket.ticket_id}
          currentStatus={ticket.status}
          onTransition={handleTransition}
          onClose={() => setShowStatusModal(false)}
        />
      )}
      {showAssignModal && (
        <AssignTicketModal
          ticketId={ticket.ticket_id}
          onAssign={handleAssign}
          onClose={() => setShowAssignModal(false)}
        />
      )}
    </div>
  );
}

function InfoRow({
  label,
  value,
  mono,
  icon,
}: {
  label: string;
  value: string;
  mono?: boolean;
  icon?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between text-sm">
      <span className="text-gray-500 flex items-center gap-1">
        {icon}
        {label}
      </span>
      <span className={`text-gray-900 font-medium text-right ${mono ? 'font-mono text-xs' : ''}`}>
        {value}
      </span>
    </div>
  );
}
