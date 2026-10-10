import api from '@/services/api'
import type { Payment, PaymentOrder } from '@/types/platform'

export interface PaymentVerifyPayload {
  payment_id: string
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
}

export async function createPaymentOrder(appointmentId: string): Promise<PaymentOrder> {
  const { data } = await api.post<PaymentOrder>('/payments/order', {
    appointment_id: appointmentId,
  })
  return data
}

export async function verifyPayment(payload: PaymentVerifyPayload): Promise<Payment> {
  const { data } = await api.post<Payment>('/payments/verify', payload)
  return data
}

export async function getAppointmentPayment(
  appointmentId: string,
): Promise<Payment | null> {
  const { data } = await api.get<{ payment: Payment | null }>(
    `/payments/appointment/${appointmentId}`,
  )
  return data.payment
}
