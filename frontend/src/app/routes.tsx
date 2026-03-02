import { Routes, Route, Navigate } from 'react-router-dom';
import AuthLayout from '@/layouts/AuthLayout';
import DashboardLayout from '@/layouts/DashboardLayout';
import ProtectedRoute from '@/features/auth/components/ProtectedRoute';
import RoleGuard from '@/features/auth/components/RoleGuard';
import { USER_ROLES } from '@/config/constants';

import LoginPage from '@/pages/LoginPage';
import SignupPage from '@/pages/SignupPage';
import DashboardPage from '@/pages/DashboardPage';
import MyTicketsPage from '@/pages/MyTicketsPage';
import AllTicketsPage from '@/pages/AllTicketsPage';
import CreateTicketPage from '@/pages/CreateTicketPage';
import TicketDetailPage from '@/pages/TicketDetailPage';
import ProfilePage from '@/pages/ProfilePage';
import UnauthorizedPage from '@/pages/UnauthorizedPage';
import NotFoundPage from '@/pages/NotFoundPage';

export default function AppRoutes() {
  return (
    <Routes>
      {/* Public — Auth */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
      </Route>

      {/* Protected — Dashboard shell */}
      <Route
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/profile" element={<ProfilePage />} />

        {/* Tickets */}
        <Route path="/tickets/me" element={<MyTicketsPage />} />
        <Route
          path="/tickets/all"
          element={
            <RoleGuard allowedRoles={[USER_ROLES.ADMIN, USER_ROLES.TEAM_LEAD]}>
              <AllTicketsPage />
            </RoleGuard>
          }
        />
        <Route
          path="/tickets/new"
          element={
            <RoleGuard allowedRoles={[USER_ROLES.USER]}>
              <CreateTicketPage />
            </RoleGuard>
          }
        />
        <Route path="/tickets/:ticketId" element={<TicketDetailPage />} />
      </Route>

      {/* Misc */}
      <Route path="/unauthorized" element={<UnauthorizedPage />} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
