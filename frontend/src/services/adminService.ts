import api from '@/services/api'
import type { Paged } from '@/types/platform'
import type {
  AdminAnalytics,
  AdminAppointmentItem,
  AdminAuditItem,
  AdminComplaintItem,
  AdminDashboardStats,
  AdminLawyerItem,
  AdminReport,
  AdminUserItem,
  ComplaintStatus,
  LawyerStatus,
  UserStatus,
} from '@/types/platform'

export async function adminDashboard(): Promise<AdminDashboardStats> {
  const { data } = await api.get<AdminDashboardStats>('/admin/dashboard')
  return data
}

export async function adminListUsers(params: {
  role?: string
  status?: string
  q?: string
  page?: number
  page_size?: number
}): Promise<Paged<AdminUserItem>> {
  const { data } = await api.get<Paged<AdminUserItem>>('/admin/users', { params })
  return data
}

export async function adminSetUserStatus(
  userId: string,
  status: UserStatus,
): Promise<AdminUserItem> {
  const { data } = await api.patch<AdminUserItem>(
    `/admin/users/${userId}/status`,
    { status },
  )
  return data
}

export async function adminListLawyers(params: {
  verification_status?: string
  page?: number
  page_size?: number
}): Promise<Paged<AdminLawyerItem>> {
  const { data } = await api.get<Paged<AdminLawyerItem>>('/admin/lawyers', { params })
  return data
}

export async function adminSetLawyerVerification(
  userId: string,
  status: LawyerStatus,
  note?: string,
): Promise<AdminLawyerItem> {
  const { data } = await api.patch<AdminLawyerItem>(
    `/admin/lawyers/${userId}/verification`,
    { status, note },
  )
  return data
}

export async function adminGetVerificationDocument(
  userId: string,
): Promise<{ url: string; filename: string }> {
  const { data } = await api.get<{ url: string; filename: string }>(
    `/admin/lawyers/${userId}/verification-document`,
  )
  return data
}

export async function adminListComplaints(params: {
  complaint_status?: string
  page?: number
  page_size?: number
}): Promise<Paged<AdminComplaintItem>> {
  const { data } = await api.get<Paged<AdminComplaintItem>>('/admin/complaints', {
    params,
  })
  return data
}

export interface AdminComplaintResponsePayload {
  status: ComplaintStatus
  adminNote?: string
  reporterResponse?: string
  reportedResponse?: string
}

export async function adminRespondComplaint(
  complaintId: string,
  payload: AdminComplaintResponsePayload,
): Promise<AdminComplaintItem> {
  const { data } = await api.patch<AdminComplaintItem>(
    `/admin/complaints/${complaintId}`,
    {
      status: payload.status,
      admin_note: payload.adminNote,
      reporter_response: payload.reporterResponse,
      reported_response: payload.reportedResponse,
    },
  )
  return data
}

export async function adminListAppointments(params: {
  status?: string
  page?: number
  page_size?: number
}): Promise<Paged<AdminAppointmentItem>> {
  const { data } = await api.get<Paged<AdminAppointmentItem>>('/admin/appointments', {
    params,
  })
  return data
}

export async function adminAnalytics(): Promise<AdminAnalytics> {
  const { data } = await api.get<AdminAnalytics>('/admin/analytics')
  return data
}

export async function adminAuditLogs(params: {
  actor_id?: string
  entity_type?: string
  page?: number
  page_size?: number
}): Promise<Paged<AdminAuditItem>> {
  const { data } = await api.get<Paged<AdminAuditItem>>('/admin/audit-logs', {
    params,
  })
  return data
}

export async function adminReport<T>(
  reportType: string,
): Promise<AdminReport & { summary: T }> {
  const { data } = await api.get<AdminReport & { summary: T }>(
    `/admin/reports/${reportType}`,
  )
  return data
}

export async function adminDownloadReport(reportType: string): Promise<void> {
  const { data } = await api.get<Blob>(`/admin/reports/${reportType}/download`, {
    responseType: 'blob',
  })
  triggerDownload(data, `${reportType}-report.pdf`)
}

export function triggerDownload(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}
