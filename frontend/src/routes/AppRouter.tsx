import { Navigate, Route, Routes } from 'react-router-dom';
import AuthLayout from '../layouts/AuthLayout';
import DashboardLayout from '../layouts/DashboardLayout';
import AdminPage from '../pages/admin/AdminPage';
import ForgotPasswordPage from '../pages/auth/ForgotPasswordPage';
import LoginPage from '../pages/auth/LoginPage';
import RegisterPage from '../pages/auth/RegisterPage';
import AutomationPage from '../pages/automation/AutomationPage';
import CompaniesPage from '../pages/companies/CompaniesPage';
import DashboardPage from '../pages/dashboard/DashboardPage';
import AppliedJobsPage from '../pages/jobs/AppliedJobsPage';
import HistoryJobsPage from '../pages/jobs/HistoryJobsPage';
import JobsPage from '../pages/jobs/JobsPage';
import TrackedJobsPage from '../pages/jobs/TrackedJobsPage';
import PortalsPage from '../pages/portals/PortalsPage';
import ProfilePage from '../pages/profile/ProfilePage';
import ReportsPage from '../pages/reports/ReportsPage';
import SettingsPage from '../pages/settings/SettingsPage';
import ProtectedRoute from './ProtectedRoute';

export default function AppRouter() {
  return (
    <Routes>
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/jobs/tracked" element={<TrackedJobsPage />} />
          <Route path="/jobs/applied" element={<AppliedJobsPage />} />
          <Route path="/jobs/history" element={<HistoryJobsPage />} />
          <Route path="/job-portals" element={<PortalsPage />} />
          <Route path="/companies" element={<CompaniesPage />} />
          <Route path="/automation" element={<AutomationPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
