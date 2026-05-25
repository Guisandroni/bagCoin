"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api-client"
import { toast } from "sonner"

export interface Conversation {
  id: string
  title: string | null
  user_id: string
  is_archived: boolean
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  conversation_id: string
  role: "user" | "assistant" | "system"
  content: string
  model_name?: number
  tokens_used?: number
  created_at: string
  updated_at: string
}

export interface ConversationListResponse {
  items: Conversation[]
  total: number
}

export interface ConversationDetailResponse extends Conversation {
  messages: Message[]
}

export function useConversations() {
  return useQuery({
    queryKey: ["conversations"],
    queryFn: async () => {
      const data = await api.get<Conversation[]>("/bagcoin/conversations")
      if (Array.isArray(data)) return { items: data, total: data.length } as ConversationListResponse
      return (data as unknown as ConversationListResponse)
    },
  })
}

export function useConversation(id: string | null) {
  return useQuery({
    queryKey: ["conversations", id],
    queryFn: () => api.get<ConversationDetailResponse>(`/bagcoin/conversations/${id}`),
    enabled: !!id,
  })
}

const TOAST_ID_CREATE_CONVERSATION = "conversations-create"

export function useCreateConversation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<Conversation>("/bagcoin/conversations"),
    onSuccess: () => {
      toast.dismiss(TOAST_ID_CREATE_CONVERSATION)
      qc.invalidateQueries({ queryKey: ["conversations"] })
      toast.success("Conversa criada com sucesso!", { id: TOAST_ID_CREATE_CONVERSATION })
    },
    onError: (err: Error) => {
      toast.dismiss(TOAST_ID_CREATE_CONVERSATION)
      console.error('[hook:conversations]', err)
      toast.error("Não foi possível criar a conversa. Tente novamente.", { id: TOAST_ID_CREATE_CONVERSATION })
    },
  })
}