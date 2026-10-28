"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api-client"
import { toast } from "sonner"

export interface CreditCardResponse {
  id: number
  name: string
  limit: number
  closing_day: number
  due_day: number
  issuer: string
  color: string
  created_at: string
}

export interface CreditCardCreate {
  name: string
  issuer: string
  limit: number
  closing_day: number
  due_day: number
  color?: string
}

export interface CreditCardUpdate {
  name?: string
  issuer?: string
  limit?: number
  closing_day?: number
  due_day?: number
  color?: string
}

export function useCreditCards() {
  return useQuery({
    queryKey: ["credit-cards"],
    queryFn: async () => {
      return api.get<CreditCardResponse[]>("/bagcoin/credit-cards")
    },
  })
}

const TOAST_ID_CREATE_CC = "credit-cards-create"

export function useCreateCreditCard() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreditCardCreate) =>
      api.post<CreditCardResponse>("/bagcoin/credit-cards", data),
    onSuccess: () => {
      toast.dismiss(TOAST_ID_CREATE_CC)
      qc.invalidateQueries({ queryKey: ["credit-cards"] })
      toast.success("Cartão criado com sucesso!", { id: TOAST_ID_CREATE_CC })
    },
    onError: (err: Error) => {
      toast.dismiss(TOAST_ID_CREATE_CC)
      console.error('[hook:credit-cards]', err)
      toast.error("Não foi possível criar o cartão. Tente novamente.", { id: TOAST_ID_CREATE_CC })
    },
  })
}

const TOAST_ID_UPDATE_CC = "credit-cards-update"

export function useUpdateCreditCard() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: CreditCardUpdate }) =>
      api.patch<CreditCardResponse>(`/bagcoin/credit-cards/${id}`, data),
    onSuccess: () => {
      toast.dismiss(TOAST_ID_UPDATE_CC)
      qc.invalidateQueries({ queryKey: ["credit-cards"] })
      toast.success("Cartão atualizado com sucesso!", { id: TOAST_ID_UPDATE_CC })
    },
    onError: (err: Error) => {
      toast.dismiss(TOAST_ID_UPDATE_CC)
      console.error('[hook:credit-cards]', err)
      toast.error("Não foi possível atualizar o cartão. Tente novamente.", { id: TOAST_ID_UPDATE_CC })
    },
  })
}

const TOAST_ID_DELETE_CC = "credit-cards-delete"

export function useDeleteCreditCard() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      api.delete(`/bagcoin/credit-cards/${id}`),
    onSuccess: () => {
      toast.dismiss(TOAST_ID_DELETE_CC)
      qc.invalidateQueries({ queryKey: ["credit-cards"] })
      toast.success("Cartão excluído com sucesso!", { id: TOAST_ID_DELETE_CC })
    },
    onError: (err: Error) => {
      toast.dismiss(TOAST_ID_DELETE_CC)
      console.error('[hook:credit-cards]', err)
      toast.error("Não foi possível excluir o cartão. Tente novamente.", { id: TOAST_ID_DELETE_CC })
    },
  })
}
