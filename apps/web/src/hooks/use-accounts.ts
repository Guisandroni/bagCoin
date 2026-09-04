"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api-client"
import { toast } from "sonner"

export interface AccountResponse {
  id: number
  name: string
  type: string
  balance: number
  bank: string
  color: string
  created_at: string
}

export interface AccountCreate {
  name: string
  type: "CHECKING" | "SAVINGS"
  balance?: number
  bank?: string
  color?: string
}

export interface AccountUpdate {
  name?: string
  type?: "CHECKING" | "SAVINGS"
  balance?: number
  bank?: string
  color?: string
}

export function useAccounts() {
  return useQuery({
    queryKey: ["accounts"],
    queryFn: async () => {
      return api.get<AccountResponse[]>("/bagcoin/accounts")
    },
  })
}

const TOAST_ID_CREATE = "accounts-create"

export function useCreateAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AccountCreate) =>
      api.post<AccountResponse>("/bagcoin/accounts", data),
    onSuccess: () => {
      toast.dismiss(TOAST_ID_CREATE)
      qc.invalidateQueries({ queryKey: ["accounts"] })
      toast.success("Conta criada com sucesso!", { id: TOAST_ID_CREATE })
    },
    onError: (err: Error) => {
      toast.dismiss(TOAST_ID_CREATE)
      console.error('[hook:accounts]', err)
      toast.error("Não foi possível criar a conta. Tente novamente.", { id: TOAST_ID_CREATE })
    },
  })
}

const TOAST_ID_UPDATE = "accounts-update"

export function useUpdateAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: AccountUpdate }) =>
      api.patch<AccountResponse>(`/bagcoin/accounts/${id}`, data),
    onSuccess: () => {
      toast.dismiss(TOAST_ID_UPDATE)
      qc.invalidateQueries({ queryKey: ["accounts"] })
      toast.success("Conta atualizada com sucesso!", { id: TOAST_ID_UPDATE })
    },
    onError: (err: Error) => {
      toast.dismiss(TOAST_ID_UPDATE)
      console.error('[hook:accounts]', err)
      toast.error("Não foi possível atualizar a conta. Tente novamente.", { id: TOAST_ID_UPDATE })
    },
  })
}

const TOAST_ID_DELETE = "accounts-delete"

export function useDeleteAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      api.delete(`/bagcoin/accounts/${id}`),
    onSuccess: () => {
      toast.dismiss(TOAST_ID_DELETE)
      qc.invalidateQueries({ queryKey: ["accounts"] })
      toast.success("Conta excluída com sucesso!", { id: TOAST_ID_DELETE })
    },
    onError: (err: Error) => {
      toast.dismiss(TOAST_ID_DELETE)
      console.error('[hook:accounts]', err)
      toast.error("Não foi possível excluir a conta. Tente novamente.", { id: TOAST_ID_DELETE })
    },
  })
}
