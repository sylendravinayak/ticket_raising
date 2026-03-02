import { Outlet } from 'react-router-dom';
import { Ticket } from 'lucide-react';

export default function AuthLayout() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 via-white to-purple-50 px-4">
      <div className="w-full max-w-md">
        {/* Brand */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center">
            <Ticket size={22} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Ticketing Genie</h1>
        </div>

        {/* Card */}
        <div className="card p-8">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
