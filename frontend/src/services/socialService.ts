import api from '@/services/api'
import type { Complaint, ComplaintAgainstMe, Paged } from '@/types/platform'

export interface ComplaintPayload {
  subject: string
  description: string
  related_appointment_id?: string
  target_user_id?: string
  conversation_id?: string
  category?: string
}

export async function createComplaint(payload: ComplaintPayload): Promise<Complaint> {
  const { data } = await api.post<Complaint>('/complaints', payload)
  return data
}

export async function listMyComplaints(page = 1): Promise<Paged<Complaint>> {
  const { data } = await api.get<Paged<Complaint>>('/complaints', { params: { page } })
  return data
}

export async function listReceivedComplaints(page = 1): Promise<Paged<ComplaintAgainstMe>> {
  const { data } = await api.get<Paged<ComplaintAgainstMe>>('/complaints/received', {
    params: { page },
  })
  return data
}

export async function submitReview(
  lawyerId: string,
  rating: number,
  comment?: string,
  appointmentId?: string,
) {
  return api.post('/reviews', {
    lawyer_id: lawyerId,
    rating,
    comment,
    appointment_id: appointmentId,
  })
}

export async function listLawyerReviews(
  lawyerId: string,
  pageSize?: number,
): Promise<Paged<import('@/types/platform').Review>> {
  const { data } = await api.get<Paged<import('@/types/platform').Review>>(`/reviews/${lawyerId}`, {
    params: pageSize ? { page_size: pageSize } : undefined,
  })
  return data
}
