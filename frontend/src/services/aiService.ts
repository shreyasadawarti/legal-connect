import api from '@/services/api'
import type {
  AiChatReply,
  AiFaqAnswer,
  AiPrediction,
  AiRecommendations,
  AiSummary,
  AiTranslation,
  LegalCategory,
  NearbyLawyerMapResponse,
} from '@/types/platform'

export async function aiChat(
  message: string,
  history?: Array<{ role: string; content: string }>,
): Promise<AiChatReply> {
  const { data } = await api.post<AiChatReply>('/ai/chat', { message, history })
  return data
}

export async function aiSummarize(text: string): Promise<AiSummary> {
  const { data } = await api.post<AiSummary>('/ai/summarize', { text })
  return data
}

export async function aiFaq(question: string): Promise<AiFaqAnswer> {
  const { data } = await api.post<AiFaqAnswer>('/ai/faq', { question })
  return data
}

export async function aiPredictCategory(
  description: string,
  categories?: LegalCategory[],
): Promise<AiPrediction> {
  const { data } = await api.post<AiPrediction>('/ai/predict-category', {
    description,
    categories,
  })
  return data
}

export async function aiTranslate(
  text: string,
  targetLanguage: string,
): Promise<AiTranslation> {
  const { data } = await api.post<AiTranslation>('/ai/translate', {
    text,
    target_language: targetLanguage,
  })
  return data
}

export async function aiRecommendLawyers(
  description: string,
  limit = 5,
): Promise<AiRecommendations> {
  const { data } = await api.post<AiRecommendations>('/ai/recommend-lawyers', {
    description,
    limit,
  })
  return data
}

export async function aiNearbyLawyers(params: {
  lat?: number
  lng?: number
  radius_km?: number
  verified_only?: boolean
  limit?: number
}): Promise<NearbyLawyerMapResponse> {
  const { data } = await api.get<NearbyLawyerMapResponse>('/ai/nearby-lawyers', {
    params,
  })
  return data
}
