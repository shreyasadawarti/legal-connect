import { useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import ProtectedRoute from '@/components/auth/ProtectedRoute'
import RoleRoute from '@/components/auth/RoleRoute'
import PlaceholderPage from '@/components/PlaceholderPage'
import AdminLoginPage from '@/features/auth/AdminLoginPage'
import EmailVerificationPage from '@/features/auth/EmailVerificationPage'
import ForgotPasswordPage from '@/features/auth/ForgotPasswordPage'
import LoginPage from '@/features/auth/LoginPage'
import RegisterPage from '@/features/auth/RegisterPage'
import ResetPasswordPage from '@/features/auth/ResetPasswordPage'
import AdminDashboard from '@/features/dashboard/AdminDashboard'
import CitizenDashboard from '@/features/dashboard/CitizenDashboard'
import LawyerDashboard from '@/features/dashboard/LawyerDashboard'
import CitizenAppointmentsPage from '@/features/appointments/CitizenAppointmentsPage'
import LawyerAppointmentsPage from '@/features/appointments/LawyerAppointmentsPage'
import ChatPage from '@/features/chat/ChatPage'
import VideoCallPage from '@/features/chat/VideoCallPage'
import ComplaintsPage from '@/features/complaints/ComplaintsPage'
import AiAssistantPage from '@/features/ai/AiAssistantPage'
import NearbyLawyersMapPage from '@/features/ai/NearbyLawyersMapPage'
import AdminAnalyticsPage from '@/features/admin/AdminAnalyticsPage'
import AdminAppointmentsPage from '@/features/admin/AdminAppointmentsPage'
import AdminAuditLogsPage from '@/features/admin/AdminAuditLogsPage'
import AdminComplaintsPage from '@/features/admin/AdminComplaintsPage'
import AdminLawyersPage from '@/features/admin/AdminLawyersPage'
import AdminReportsPage from '@/features/admin/AdminReportsPage'
import AdminUsersPage from '@/features/admin/AdminUsersPage'
import DocumentsPage from '@/features/documents/DocumentsPage'
import EmergencyHelpPage from '@/features/emergency/EmergencyHelpPage'
import EarningsPage from '@/features/lawyer/EarningsPage'
import LawyerListPage from '@/features/lawyers/LawyerListPage'
import LawyerProfilePage from '@/features/lawyers/LawyerProfilePage'
import LawyerProfileSettingsPage from '@/features/lawyers/LawyerProfileSettingsPage'
import NotificationsPage from '@/features/notifications/NotificationsPage'
import ProfilePage from '@/features/profile/ProfilePage'
import DashboardLayout from '@/layouts/DashboardLayout'
import PublicLayout from '@/layouts/PublicLayout'
import AboutPage from '@/pages/AboutPage'
import ContactPage from '@/pages/ContactPage'
import FaqPage from '@/pages/FaqPage'
import HowItWorksPage from '@/pages/HowItWorksPage'
import LandingPage from '@/pages/LandingPage'
import NotFoundPage from '@/pages/NotFoundPage'
import PrivacyPage from '@/pages/PrivacyPage'
import TermsPage from '@/pages/TermsPage'
import { useAuthStore } from '@/stores/authStore'
import { useThemeStore } from '@/stores/themeStore'

function Placeholder({ title }: { title: string }) {
  return <PlaceholderPage title={title} />
}

export default function App() {
  const theme = useThemeStore((s) => s.theme)
  const fetchCurrentUser = useAuthStore((s) => s.fetchCurrentUser)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])

  useEffect(() => {
    if (localStorage.getItem('access_token')) {
      fetchCurrentUser()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <Routes>
      {/* Public */}
      <Route element={<PublicLayout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/how-it-works" element={<HowItWorksPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/faq" element={<FaqPage />} />
        <Route path="/contact" element={<ContactPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/terms" element={<TermsPage />} />
      </Route>

      {/* Auth */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/verify-email" element={<EmailVerificationPage />} />
      <Route path="/admin/login" element={<AdminLoginPage />} />

      {/* Protected (any authenticated user) */}
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/profile" element={<ProfilePage />} />

          {/* Citizen */}
          <Route element={<RoleRoute roles={['user']} />}>
            <Route path="/dashboard" element={<CitizenDashboard />} />
            <Route path="/lawyers" element={<LawyerListPage />} />
            <Route path="/lawyers/:userId" element={<LawyerProfilePage />} />
            <Route path="/appointments" element={<CitizenAppointmentsPage />} />
            <Route path="/complaints" element={<ComplaintsPage />} />
            <Route path="/notifications" element={<NotificationsPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/chat/video" element={<VideoCallPage />} />
            <Route path="/ai-assistant" element={<AiAssistantPage />} />
            <Route path="/nearby-lawyers" element={<NearbyLawyersMapPage />} />
            <Route path="/emergency" element={<EmergencyHelpPage />} />
            <Route path="/reviews" element={<Navigate to="/appointments" replace />} />
          </Route>

          {/* Lawyer */}
          <Route element={<RoleRoute roles={['lawyer']} />}>
            <Route path="/lawyer/dashboard" element={<LawyerDashboard />} />
            <Route path="/lawyer/appointments" element={<LawyerAppointmentsPage />} />
            <Route path="/lawyer/profile" element={<LawyerProfileSettingsPage />} />
            <Route path="/lawyer/availability" element={<LawyerProfileSettingsPage />} />
            <Route path="/lawyer/verification" element={<Placeholder title="Verification" />} />
            <Route path="/lawyer/documents" element={<DocumentsPage />} />
            <Route path="/lawyer/chat" element={<ChatPage />} />
            <Route path="/lawyer/chat/video" element={<VideoCallPage />} />
            <Route path="/lawyer/earnings" element={<EarningsPage />} />
            <Route path="/lawyer/reviews" element={<Placeholder title="Reviews" />} />
          </Route>

          {/* Admin */}
          <Route element={<RoleRoute roles={['admin']} />}>
            <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
            <Route path="/admin/dashboard" element={<AdminDashboard />} />
            <Route path="/admin/users" element={<AdminUsersPage />} />
            <Route path="/admin/lawyers" element={<AdminLawyersPage />} />
            <Route path="/admin/appointments" element={<AdminAppointmentsPage />} />
            <Route path="/admin/complaints" element={<AdminComplaintsPage />} />
            <Route path="/admin/reports" element={<AdminReportsPage />} />
            <Route path="/admin/analytics" element={<AdminAnalyticsPage />} />
            <Route path="/admin/audit-logs" element={<AdminAuditLogsPage />} />
            <Route path="/admin/settings" element={<Placeholder title="Settings" />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
