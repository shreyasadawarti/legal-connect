import api from '@/services/api'
import type { Complaint, Paged } from '@/types/platform'

export interface ComplaintPayload {
  subject: string
  description: string
  related_appointment_id?: string
}

export async function createComplaint(payload: ComplaintPayload): Promise<Complaint> {
  const { data } = await api.post<Complaint>('/complaints', payload)
  return data
}

export async function listMyComplaints(page = 1): Promise<Paged<Complaint>> {
  const { data } = await api.get<Paged<Complaint>>('/complaints', { params: { page } })
  return data
}

export async function submitReview(lawyerId: string, rating: number, comment?: string) {
  return api.post('/reviews', { lawyer_id: lawyerId, rating, comment })
}

export async function listLawyerReviews(lawyerId: string): Promise<Paged<import('@/types/platform').Review>> {
  const { data } = await api.get<Paged<import('@/types/platform').Review>>(`/reviews/${lawyerId}`)
  return data
}

export async function makePayment(appointmentId: string, amount: number) {
  return api.post('/payments', { appointment_id: appointmentId, amount })
}
