import { useAppSelector } from '@/hooks/useAppDispatch';
import { ROLE_LABELS } from '@/config/constants';
import { formatDate } from '@/utils/formatDate';
import { Shield, Mail, Calendar, CheckCircle2, XCircle } from 'lucide-react';

export default function ProfilePage() {
  const { user } = useAppSelector((s) => s.auth);

  if (!user) return null;

  return (
    <div className="max-w-lg mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Profile</h1>

      <div className="card p-6 space-y-4">
        <div className="flex items-center gap-4 mb-2">
          <div className="w-14 h-14 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-bold text-xl">
            {user.email.charAt(0).toUpperCase()}
          </div>
          <div>
            <p className="font-semibold text-gray-900">{user.email}</p>
            <span className="badge bg-indigo-100 text-indigo-800">
              {ROLE_LABELS[user.role]}
            </span>
          </div>
        </div>

        <hr className="border-gray-100" />

        <div className="space-y-3 text-sm">
          <InfoRow icon={<Mail size={16} />} label="Email" value={user.email} />
          <InfoRow icon={<Shield size={16} />} label="Role" value={ROLE_LABELS[user.role]} />
          <InfoRow
            icon={user.is_active ? <CheckCircle2 size={16} className="text-green-500" /> : <XCircle size={16} className="text-red-500" />}
            label="Status"
            value={user.is_active ? 'Active' : 'Inactive'}
          />
          <InfoRow
            icon={user.is_verified ? <CheckCircle2 size={16} className="text-green-500" /> : <XCircle size={16} className="text-gray-400" />}
            label="Verified"
            value={user.is_verified ? 'Yes' : 'No'}
          />
          <InfoRow
            icon={<Calendar size={16} />}
            label="Joined"
            value={formatDate(user.created_at)}
          />
        </div>

        <hr className="border-gray-100" />

        <p className="text-xs text-gray-400 font-mono">ID: {user.id}</p>
      </div>
    </div>
  );
}

function InfoRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-gray-500 flex items-center gap-2">
        {icon} {label}
      </span>
      <span className="font-medium text-gray-900">{value}</span>
    </div>
  );
}
