"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import { financialPollingOptions } from "./use-financial-polling"

export interface Budget {
  id: number
  name: string
  period: string
  total_limit: number
  total_spent: number
  total_remaining: number
  percentage: number
  budget_type: string
  budget_date?: string
  category_id: number | null
  category_name: string | null
  created_at: string
  updated_at: string | null
}

export interface BudgetCreate {
  name: string
  period: "monthly" | "weekly" | "yearly"
  total_limit: number
  budget_type?: string
  budget_date?: string
  category_id?: number | null
  category_name?: string
}

export interface BudgetUpdate {
  name?: string
  period?: "monthly" | "weekly" | "yearly" | string
  total_limit?: number
  budget_type?: string
  budget_date?: string
  category_id?: number | null
  category_name?: string
}

export interface BudgetListResponse {
  items: Budget[]
  total: number
}

export function useBudgets() {
  return useQuery({
    queryKey: ["budgets"],
    queryFn: async () => {
      const data = await api.get<Budget[]>("/bagcoin/budgets")
      if (Array.isArray(data)) return { items: data, total: data.length } as BudgetListResponse
      return (data as unknown as BudgetListResponse)
    },
    ...financialPollingOptions,
  })
}

export function useBudget(id: number) {
  return useQuery({
    queryKey: ["budgets", id],
    queryFn: () => api.get<Budget>(`/bagcoin/budgets/${id}`),
    enabled: !!id,
  })
}

const TOAST_ID_CREATE_BUDGET = "budgets-create"

export function useCreateBudget(options?: { silent?: boolean }) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: BudgetCreate) =>
      api.post<Budget>("/bagcoin/budgets", data),
    onSuccess: () => {
      toast.dismiss(TOAST_ID_CREATE_BUDGET)
      qc.invalidateQueries({ queryKey: ["budgets"] })
      if (!options?.silent) {
        toast.success("Orçamento criado com sucesso!", { id: TOAST_ID_CREATE_BUDGET })
      }
    },
    onError: (err: Error) => {
      toast.dismiss(TOAST_ID_CREATE_BUDGET)
      console.error('[hook:budgets]', err)
      if (!options?.silent) {
        toast.error("Não foi possível criar o orçamento. Tente novamente.", { id: TOAST_ID_CREATE_BUDGET })
      }
    },
  })
}

const TOAST_ID_UPDATE_BUDGET = "budgets-update"

export function useUpdateBudget(options?: { silent?: boolean }) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: BudgetUpdate }) =>
      api.patch<Budget>(`/bagcoin/budgets/${id}`, data),
    onSuccess: () => {
      toast.dismiss(TOAST_ID_UPDATE_BUDGET)
      qc.invalidateQueries({ queryKey: ["budgets"] })
      if (!options?.silent) {
        toast.success("Orçamento atualizado com sucesso!", { id: TOAST_ID_UPDATE_BUDGET })
      }
    },
    onError: (err: Error) => {
      toast.dismiss(TOAST_ID_UPDATE_BUDGET)
      console.error('[hook:budgets]', err)
      if (!options?.silent) {
        toast.error("Não foi possível atualizar o orçamento. Tente novamente.", { id: TOAST_ID_UPDATE_BUDGET })
      }
    },
  })
}

const TOAST_ID_DELETE_BUDGET = "budgets-delete"

export function useDeleteBudget(options?: { silent?: boolean }) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      api.delete(`/bagcoin/budgets/${id}`),
    onSuccess: () => {
      toast.dismiss(TOAST_ID_DELETE_BUDGET)
      qc.invalidateQueries({ queryKey: ["budgets"] })
      if (!options?.silent) {
        toast.success("Orçamento excluído com sucesso!", { id: TOAST_ID_DELETE_BUDGET })
      }
    },
    onError: (err: Error) => {
      toast.dismiss(TOAST_ID_DELETE_BUDGET)
      console.error('[hook:budgets]', err)
      if (!options?.silent) {
        toast.error("Não foi possível excluir o orçamento. Tente novamente.", { id: TOAST_ID_DELETE_BUDGET })
      }
    },
  })
}
