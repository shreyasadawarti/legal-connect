import type { UserRole } from '@/types/user'

export type LegalCategory =
  | 'family'
  | 'criminal'
  | 'civil'
  | 'corporate'
  | 'property'
  | 'tax'
  | 'labor'
  | 'intellectual_property'
  | 'contract'
  | 'personal_injury'
  | 'immigration'
  | 'other'

export type LawyerStatus = 'PENDING_VERIFICATION' | 'ACTIVE' | 'REJECTED' | 'SUSPENDED'
export type AppointmentStatus = 'PENDING' | 'CONFIRMED' | 'COMPLETED' | 'CANCELLED' | 'REJECTED' | 'NO_SHOW'
export type NotificationType = 'APPOINTMENT' | 'REVIEW' | 'COMPLAINT' | 'SYSTEM' | 'PAYMENT'
export type ComplaintStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'REJECTED'
export type PaymentStatus = 'PENDING' | 'PAID' | 'FAILED' | 'REFUNDED'
export type UserStatus = 'ACTIVE' | 'SUSPENDED' | 'DEACTIVATED'

export interface AvailabilitySlot {
  day_of_week: number
  start_time: string
  end_time: string
}

export interface LawyerProfile {
  user_id: string
  name: string
  email: string
  phone?: string
  bio: string
  years_of_experience: number
  categories: LegalCategory[]
  specializations: string[]
  languages: string[]
  hourly_rate: number
  city?: string
  latitude?: number
  longitude?: number
  availability: AvailabilitySlot[]
  avg_rating: number
  rating_count: number
  verification_status: LawyerStatus
  is_verified: boolean
  rejection_reason?: string
  verification_document_id?: string
}

export interface Paged<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface Appointment {
  id: string
  lawyer_id: string
  lawyer_name: string
  client_id: string
  client_name: string
  category: LegalCategory
  start_time: string
  end_time: string
  status: AppointmentStatus
  description?: string
}

export interface Notification {
  id: string
  user_id: string
  type: NotificationType
  title: string
  message: string
  data?: Record<string, unknown>
  is_read: boolean
  created_at: string
}

export interface Complaint {
  id: string
  user_id: string
  subject: string
  description: string
  related_appointment_id?: string
  status: ComplaintStatus
  admin_note?: string
  created_at: string
}

export interface Payment {
  id: string
  appointment_id: string
  payee_id: string
  amount: number
  status: PaymentStatus
  reference: string
}

export interface Review {
  id: string
  lawyer_id: string
  lawyer_name: string
  reviewer_id: string
  reviewer_name: string
  rating: number
  comment?: string
  created_at: string
}

export interface LegalCategoryInfo {
  name: LegalCategory
  label: string
  description: string
}

export type { UserRole }

export interface DocumentItem {
  id: string
  owner_id: string
  owner_name: string
  title: string
  original_name: string
  mime_type: string
  size_bytes: number
  public_id: string
  resource_type: string
  related_appointment_id?: string
  doc_type?: string
  shared_with: string[]
  created_at?: string
}

export interface ChatPeer {
  id: string
  name: string
  role?: string
}

export interface ChatConversation {
  id: string
  type: string
  peers: ChatPeer[]
  peer?: ChatPeer | null
  last_message: string
  last_message_at?: string
  unread_count: number
}

export interface ChatMessage {
  id: string
  conversation_id: string
  sender_id: string
  recipient_id: string
  content: string
  message_type: string
  is_read: boolean
  created_at?: string
}

export interface MessageList {
  items: ChatMessage[]
  has_more: boolean
  conversation_id: string
}

export type SocketEvent =
  | { type: 'connected'; user_id: string }
  | { type: 'message'; message: ChatMessage; status?: 'sent' | 'delivered' }
  | { type: 'notice'; conversation_id: string }
  | { type: 'read'; conversation_id: string; reader_id: string }
  | { type: 'typing'; conversation_id: string; user_id: string }
  | { type: 'call-request'; conversation_id: string; from_user_id: string; to_user_id?: string }
  | { type: 'offer'; conversation_id: string; from_user_id: string; sdp?: string }
  | { type: 'answer'; conversation_id: string; from_user_id: string; sdp?: string }
  | { type: 'ice'; conversation_id: string; from_user_id: string; candidate?: string }
  | { type: 'call-decline'; conversation_id: string; from_user_id: string }
  | { type: 'call-end'; conversation_id: string; from_user_id: string }
  | { type: 'error'; error: string }

export interface AiChatReply {
  reply: string
}

export interface AiFaqAnswer {
  answer: string
  related_categories: LegalCategory[]
  suggested_action: string
}

export interface AiPrediction {
  category: LegalCategory
  confidence: number
  explanation: string
}

export interface AiRecommendations {
  recommendations: LawyerProfile[]
}

export interface AiSummary {
  summary: string
}

export interface AiTranslation {
  translated: string
}

export interface NearbyLawyerMapResponse {
  items: LawyerProfile[]
  total: number
}

export interface AdminDashboardStats {
  total_users: number
  total_lawyers: number
  total_appointments: number
  pending_verifications: number
  open_complaints: number
  total_revenue: number
}

export interface AdminUserItem {
  id: string
  name: string
  email: string
  role: UserRole
  status: UserStatus
  created_at?: string
}

export interface AdminLawyerItem extends LawyerProfile {
  status?: string
}

export interface AdminComplaintItem {
  id: string
  user_id: string
  user_name: string
  user_email: string
  subject: string
  description: string
  status: ComplaintStatus
  admin_note?: string
  created_at: string
}

export interface AdminAppointmentItem {
  id: string
  lawyer_id: string
  lawyer_name: string
  client_id: string
  client_name: string
  category: string
  start_time: string
  end_time: string
  status: AppointmentStatus
  description?: string
  created_at?: string
}

export interface AdminAnalytics {
  users_by_role: Record<string, number>
  appointments_by_status: Record<string, number>
  lawyers_by_status: Record<string, number>
  complaints_by_status: Record<string, number>
  appointments_by_month: Array<{ month: string; count: number }>
  top_categories: Array<{ category: string; count: number }>
  top_lawyers: Array<{
    name: string
    avg_rating: number
    rating_count: number
    categories: LegalCategory[]
  }>
  revenue_by_status: Record<string, number>
}

export interface AdminAuditItem {
  id: string
  actor_id?: string
  actor_name?: string
  action: string
  entity_type: string
  entity_id?: string
  details?: Record<string, unknown>
  created_at?: string
}

export interface AdminReport {
  report_type: string
  generated_at: string
  summary: Record<string, unknown>
}

