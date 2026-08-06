import { lazy, startTransition } from 'react';
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import PageSuspense from '../components/common/PageSuspense';
import AuthLayout from '../layouts/AuthLayout';
import DashboardLayout from '../layouts/DashboardLayout';
import ProtectedRoute from './ProtectedRoute';

// Route-based lazy loading + dynamic imports → separate chunks (code splitting)
const LoginPage = lazy(() => import('../pages/auth/LoginPage'));
const RegisterPage = lazy(() => import('../pages/auth/RegisterPage'));
const ForgotPasswordPage = lazy(() => import('../pages/auth/ForgotPasswordPage'));
const DashboardPage = lazy(() => import('../pages/dashboard/DashboardPage'));
const JobsPage = lazy(() => import('../pages/jobs/JobsPage'));
const TrackedJobsPage = lazy(() => import('../pages/jobs/TrackedJobsPage'));
const AppliedJobsPage = lazy(() => import('../pages/jobs/AppliedJobsPage'));
const HistoryJobsPage = lazy(() => import('../pages/jobs/HistoryJobsPage'));
const PortalsPage = lazy(() => import('../pages/portals/PortalsPage'));
const CompaniesPage = lazy(() => import('../pages/companies/CompaniesPage'));
const AutomationPage = lazy(() => import('../pages/automation/AutomationPage'));
const ReportsPage = lazy(() => import('../pages/reports/ReportsPage'));
const ProfilePage = lazy(() => import('../pages/profile/ProfilePage'));
const SettingsPage = lazy(() => import('../pages/settings/SettingsPage'));
const AdminPage = lazy(() => import('../pages/admin/AdminPage'));
const OnboardingPage = lazy(() => import('../pages/onboarding/OnboardingPage'));
const ApprovalsPage = lazy(() => import('../pages/approvals/ApprovalsPage'));
const QuestionsPage = lazy(() => import('../pages/questions/QuestionsPage'));
const PipelinePage = lazy(() => import('../pages/pipeline/PipelinePage'));
const EmailInboxPage = lazy(() => import('../pages/email/EmailInboxPage'));
const CalendarPage = lazy(() => import('../pages/calendar/CalendarPage'));
const ActivityPage = lazy(() => import('../pages/activity/ActivityPage'));

function Lazy({ children }: { children: React.ReactNode }) {
  return <PageSuspense>{children}</PageSuspense>;
}

/** Concurrent-friendly navigate helper for call sites that want startTransition. */
export function useTransitionNavigate() {
  const navigate = useNavigate();
  return (to: string) => startTransition(() => navigate(to));
}

export default function AppRouter() {
  return (
    <Routes>
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<Lazy><LoginPage /></Lazy>} />
        <Route path="/register" element={<Lazy><RegisterPage /></Lazy>} />
        <Route path="/forgot-password" element={<Lazy><ForgotPasswordPage /></Lazy>} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/onboarding" element={<Lazy><OnboardingPage /></Lazy>} />
          <Route path="/dashboard" element={<Lazy><DashboardPage /></Lazy>} />
          <Route path="/approvals" element={<Lazy><ApprovalsPage /></Lazy>} />
          <Route path="/pipeline" element={<Lazy><PipelinePage /></Lazy>} />
          <Route path="/email" element={<Lazy><EmailInboxPage /></Lazy>} />
          <Route path="/questions" element={<Lazy><QuestionsPage /></Lazy>} />
          <Route path="/calendar" element={<Lazy><CalendarPage /></Lazy>} />
          <Route path="/activity" element={<Lazy><ActivityPage /></Lazy>} />
          <Route path="/jobs" element={<Lazy><JobsPage /></Lazy>} />
          <Route path="/jobs/tracked" element={<Lazy><TrackedJobsPage /></Lazy>} />
          <Route path="/jobs/applied" element={<Lazy><AppliedJobsPage /></Lazy>} />
          <Route path="/jobs/history" element={<Lazy><HistoryJobsPage /></Lazy>} />
          <Route path="/job-portals" element={<Lazy><PortalsPage /></Lazy>} />
          <Route path="/companies" element={<Lazy><CompaniesPage /></Lazy>} />
          <Route path="/automation" element={<Lazy><AutomationPage /></Lazy>} />
          <Route path="/reports" element={<Lazy><ReportsPage /></Lazy>} />
          <Route path="/profile" element={<Lazy><ProfilePage /></Lazy>} />
          <Route path="/settings" element={<Lazy><SettingsPage /></Lazy>} />
          <Route path="/admin" element={<Lazy><AdminPage /></Lazy>} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
