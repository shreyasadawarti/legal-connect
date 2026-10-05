import api from '@/services/api'
import type { Appointment, AppointmentStatus, Paged } from '@/types/platform'

export interface BookingPayload {
  lawyer_id: string
  category?: string
  start_time: string
  end_time: string
  description?: string
}

export async function bookAppointment(payload: BookingPayload): Promise<Appointment> {
  const { data } = await api.post<Appointment>('/appointments', payload)
  return data
}

export async function listAppointments(params?: {
  status?: AppointmentStatus
  page?: number
  page_size?: number
}): Promise<Paged<Appointment>> {
  const { data } = await api.get<Paged<Appointment>>('/appointments', { params })
  return data
}

export async function getAppointment(id: string): Promise<Appointment> {
  const { data } = await api.get<Appointment>(`/appointments/${id}`)
  return data
}

export async function cancelAppointment(id: string): Promise<Appointment> {
  const { data } = await api.patch<Appointment>(`/appointments/${id}/cancel`)
  return data
}

export async function rescheduleAppointment(
  id: string,
  start_time: string,
  end_time: string,
): Promise<Appointment> {
  const { data } = await api.patch<Appointment>(`/appointments/${id}/reschedule`, {
    start_time,
    end_time,
  })
  return data
}

export async function confirmAppointment(id: string): Promise<Appointment> {
  const { data } = await api.patch<Appointment>(`/appointments/${id}/confirm`)
  return data
}

export async function rejectAppointment(id: string): Promise<Appointment> {
  const { data } = await api.patch<Appointment>(`/appointments/${id}/reject`)
  return data
}

export async function completeAppointment(id: string): Promise<Appointment> {
  const { data } = await api.patch<Appointment>(`/appointments/${id}/complete`)
  return data
}
