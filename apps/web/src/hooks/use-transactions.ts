"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import apiClient, { api } from "@/lib/api-client"
import { toast } from "sonner"
import { financialPollingOptions } from "./use-financial-polling"

export interface TransactionResponse {
  id: string
  type: "EXPENSE" | "INCOME"
  name: string
  category: string
  category_id?: number | null
  category_name?: string | null
  amount: number
  date: string
  transaction_date?: string | null
  source: string
  status: string
  is_recurring?: boolean
  recurrence_frequency?: "weekly" | "monthly" | "yearly" | null
}

interface TransactionListResponse {
  items: TransactionResponse[]
  total: number
}

export interface TransactionSummary {
  balance: number
  total_income: number
  total_expenses: number
  transaction_count: number
  categories: Array<{ name: string; amount: number; color: string }>
  recent_transactions: TransactionResponse[]
}

export interface CreateTransactionData {
  type: "EXPENSE" | "INCOME"
  amount: number
  description: string
  category_id?: number
  category_name?: string
  transaction_date?: string
  source?: "manual" | "auto"
  status?: "confirmed" | "pending"
  is_recurring?: boolean
  recurrence_frequency?: "weekly" | "monthly" | "yearly"
}

export interface UpdateTransactionData {
  id: string
  type?: "EXPENSE" | "INCOME"
  amount?: number
  description?: string
  category_id?: number
  category_name?: string
  transaction_date?: string
  status?: "confirmed" | "pending"
  is_recurring?: boolean
  recurrence_frequency?: "weekly" | "monthly" | "yearly"
}

export function useTransactions(filters?: {
  type?: string
  search?: string
  skip?: number
  limit?: number
  date_from?: string
  date_to?: string
}) {
  return useQuery<TransactionListResponse>({
    queryKey: ["transactions", filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters?.type) params.append("type", filters.type)
      if (filters?.search) params.append("search", filters.search)
      if (filters?.skip !== undefined) params.append("skip", String(filters.skip))
      if (filters?.limit !== undefined) params.append("limit", String(filters.limit))
      if (filters?.date_from) params.append("date_from", filters.date_from)
      if (filters?.date_to) params.append("date_to", filters.date_to)
      return api.get<TransactionListResponse>(`/bagcoin/transactions?${params.toString()}`)
    },
    ...financialPollingOptions,
  })
}

export function useTransactionSummary(filters?: { date_from?: string; date_to?: string }) {
  return useQuery<TransactionSummary>({
    queryKey: ["transactions", "summary", filters],
    queryFn: () => {
      const params = new URLSearchParams()
      if (filters?.date_from) params.append("date_from", filters.date_from)
      if (filters?.date_to) params.append("date_to", filters.date_to)
      const query = params.toString()
      return api.get<TransactionSummary>(`/bagcoin/transactions/summary${query ? `?${query}` : ""}`)
    },
    ...financialPollingOptions,
  })
}

const TOAST_ID_CREATE_TRANSACTION = "transactions-create"

export function useCreateTransaction(options?: { silent?: boolean }) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateTransactionData) =>
      api.post<TransactionResponse>("/bagcoin/transactions", data),
    onSuccess: () => {
      toast.dismiss(TOAST_ID_CREATE_TRANSACTION)
      queryClient.invalidateQueries({ queryKey: ["transactions"] })
      if (!options?.silent) {
        toast.success("Transação criada com sucesso!", { id: TOAST_ID_CREATE_TRANSACTION })
      }
    },
    onError: (err: Error) => {
      toast.dismiss(TOAST_ID_CREATE_TRANSACTION)
      console.error('[hook:transactions]', err)
      if (!options?.silent) {
        toast.error("Não foi possível criar a transação. Tente novamente.", { id: TOAST_ID_CREATE_TRANSACTION })
      }
    },
  })
}

const TOAST_ID_UPDATE_TRANSACTION = "transactions-update"

export function useUpdateTransaction(options?: { silent?: boolean }) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: UpdateTransactionData) =>
      api.patch<TransactionResponse>(`/bagcoin/transactions/${id}`, data),
    onSuccess: () => {
      toast.dismiss(TOAST_ID_UPDATE_TRANSACTION)
      queryClient.invalidateQueries({ queryKey: ["transactions"] })
      if (!options?.silent) {
        toast.success("Transação atualizada com sucesso!", { id: TOAST_ID_UPDATE_TRANSACTION })
      }
    },
    onError: (err: Error) => {
      toast.dismiss(TOAST_ID_UPDATE_TRANSACTION)
      console.error('[hook:transactions]', err)
      if (!options?.silent) {
        toast.error("Não foi possível atualizar a transação. Tente novamente.", { id: TOAST_ID_UPDATE_TRANSACTION })
      }
    },
  })
}

const TOAST_ID_DELETE_TRANSACTION = "transactions-delete"

export function useDeleteTransaction(options?: { silent?: boolean }) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/bagcoin/transactions/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] })
      if (!options?.silent) {
        toast.dismiss(TOAST_ID_DELETE_TRANSACTION)
        toast.success("Transação excluída com sucesso!", { id: TOAST_ID_DELETE_TRANSACTION })
      }
    },
    onError: (err: Error) => {
      console.error('[hook:transactions]', err)
      if (!options?.silent) {
        toast.dismiss(TOAST_ID_DELETE_TRANSACTION)
        toast.error("Não foi possível excluir a transação. Tente novamente.", { id: TOAST_ID_DELETE_TRANSACTION })
      }
    },
  })
}

export function useExportTransactionsCsv() {
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.get("/bagcoin/export.csv", {
        responseType: "blob",
      })
      return data as Blob
    },
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement("a")
      anchor.href = url
      anchor.download = "bagcoin-financeiro.csv"
      anchor.click()
      URL.revokeObjectURL(url)
      toast.success("CSV exportado com sucesso")
    },
    onError: (err: Error) => {
      toast.error("Não foi possível exportar o CSV. Tente novamente.")
    },
  })
}
