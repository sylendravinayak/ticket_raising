import { useAppSelector } from '@/hooks/useAppDispatch';
import { USER_ROLES, ROLE_LABELS } from '@/config/constants';
import {
  LayoutDashboard,
  Ticket,
  Shield,
  Users,
  UserCheck,
  AlertTriangle,
} from 'lucide-react';
import { Link } from 'react-router-dom';

export default function DashboardPage() {
  const { user } = useAppSelector((s) => s.auth);

  if (!user) return null;

  const isCustomer = user.role === USER_ROLES.USER;
  const isAgent = user.role === USER_ROLES.SUPPORT_AGENT;
  const isLeadOrAdmin =
    user.role === USER_ROLES.ADMIN || user.role === USER_ROLES.TEAM_LEAD;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">
          Welcome back, <span className="font-medium">{user.email}</span> —{' '}
          <span className="badge bg-indigo-100 text-indigo-800">{ROLE_LABELS[user.role]}</span>
        </p>
      </div>

      {/* Quick action cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <DashboardCard
          to="/tickets/me"
          icon={<Ticket size={24} className="text-indigo-600" />}
          title="My Tickets"
          description={
            isCustomer
              ? 'View and track your submitted tickets'
              : isAgent
                ? 'View tickets assigned to you'
                : 'View tickets relevant to you'
          }
        />

        {isCustomer && (
          <DashboardCard
            to="/tickets/new"
            icon={<AlertTriangle size={24} className="text-amber-600" />}
            title="Report an Issue"
            description="Create a new support ticket"
          />
        )}

        {isLeadOrAdmin && (
          <DashboardCard
            to="/tickets/all"
            icon={<Users size={24} className="text-green-600" />}
            title="All Tickets"
            description="View and manage all system tickets"
          />
        )}

        <DashboardCard
          to="/profile"
          icon={<Shield size={24} className="text-purple-600" />}
          title="Profile"
          description="View your account details"
        />
      </div>

      {/* Role description */}
      <div className="card p-6">
        <h2 className="font-semibold text-gray-900 mb-2">Your Permissions</h2>
        {isCustomer && (
          <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
            <li>Create new support tickets</li>
            <li>View your own tickets and their status</li>
            <li>Track SLA deadlines on your tickets</li>
          </ul>
        )}
        {isAgent && (
          <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
            <li>View tickets assigned to you</li>
            <li>Self-assign unassigned tickets</li>
            <li>Transition ticket status (acknowledge, resolve, etc.)</li>
          </ul>
        )}
        {isLeadOrAdmin && (
          <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
            <li>View and manage all tickets in the system</li>
            <li>Assign tickets to any agent</li>
            <li>Transition ticket status</li>
            <li>Filter by SLA breach, escalation, and more</li>
          </ul>
        )}
      </div>
    </div>
  );
}

function DashboardCard({
  to,
  icon,
  title,
  description,
}: {
  to: string;
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <Link
      to={to}
      className="card p-5 hover:shadow-md transition-shadow flex items-start gap-4"
    >
      <div className="shrink-0 mt-0.5">{icon}</div>
      <div>
        <h3 className="font-semibold text-gray-900">{title}</h3>
        <p className="text-sm text-gray-500 mt-0.5">{description}</p>
      </div>
    </Link>
  );
}
