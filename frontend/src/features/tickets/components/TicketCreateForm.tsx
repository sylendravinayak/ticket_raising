import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@/hooks/useAppDispatch';
import { createTicket } from '../slices/ticketSlice';
import { ENVIRONMENTS } from '@/config/constants';
import { Send } from 'lucide-react';
import toast from 'react-hot-toast';

export default function TicketCreateForm() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { loading, error } = useAppSelector((s) => s.tickets);

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [product, setProduct] = useState('');
  const [environment, setEnvironment] = useState<string>('PROD');
  const [areaOfConcern, setAreaOfConcern] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const result = await dispatch(
      createTicket({
        title,
        description,
        product,
        environment,
        source: 'UI',
        area_of_concern: areaOfConcern || undefined,
      }),
    );
    if (createTicket.fulfilled.match(result)) {
      toast.success(`Ticket ${result.payload.ticket_number} created!`);
      navigate(`/tickets/${result.payload.ticket_id}`);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card p-6 max-w-2xl space-y-5">
      <h2 className="text-xl font-bold text-gray-900">Create New Ticket</h2>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Title *</label>
        <input
          type="text"
          required
          minLength={3}
          maxLength={500}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Brief summary of the issue"
          className="input-field"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Description *</label>
        <textarea
          required
          minLength={10}
          rows={5}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Detailed description of the problem..."
          className="input-field resize-y"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Product *</label>
          <input
            type="text"
            required
            maxLength={100}
            value={product}
            onChange={(e) => setProduct(e.target.value)}
            placeholder="e.g. Payments, Auth, Dashboard"
            className="input-field"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Environment *</label>
          <select
            value={environment}
            onChange={(e) => setEnvironment(e.target.value)}
            className="input-field"
          >
            {ENVIRONMENTS.map((env) => (
              <option key={env} value={env}>{env}</option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Area of Concern <span className="text-gray-400">(optional)</span>
        </label>
        <input
          type="text"
          maxLength={255}
          value={areaOfConcern}
          onChange={(e) => setAreaOfConcern(e.target.value)}
          placeholder="e.g. Checkout Flow, User Registration"
          className="input-field"
        />
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex justify-end gap-3 pt-2">
        <button type="button" onClick={() => navigate(-1)} className="btn-secondary">
          Cancel
        </button>
        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? (
            <span className="inline-flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Submitting…
            </span>
          ) : (
            <span className="inline-flex items-center gap-2">
              <Send size={16} />
              Submit Ticket
            </span>
          )}
        </button>
      </div>
    </form>
  );
}
