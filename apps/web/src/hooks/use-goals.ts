"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api-client"
import { toast } from "sonner"
import { financialPollingOptions } from "./use-financial-polling"

export interface Goal {
  id: number
  title: string
  target_amount: number
  current_amount: number
  deadline: string | null
  status: "active" | "completed" | "cancelled"
  created_at: string
  updated_at: string | null
}

export interface GoalCreate {
  title: string
  target_amount: number
  current_amount?: number
  deadline?: string | null
  status?: "active" | "completed" | "cancelled"
}

export interface GoalUpdate {
  title?: string
  target_amount?: number
  current_amount?: number
  deadline?: string | null
  status?: "active" | "completed" | "cancelled"
}

export interface GoalListResponse {
  items: Goal[]
  total: number
}

export function useGoals() {
  return useQuery({
    queryKey: ["goals"],
    queryFn: async () => {
      const data = await api.get<Goal[]>("/bagcoin/goals")
      if (Array.isArray(data)) return { items: data, total: data.length } as GoalListResponse
      return (data as unknown as GoalListResponse)
    },
    ...financialPollingOptions,
  })
}

export function useGoal(id: number) {
  return useQuery({
    queryKey: ["goals", id],
    queryFn: () => api.get<Goal>(`/bagcoin/goals/${id}`),
    enabled: !!id,
  })
}

const TOAST_ID_CREATE_GOAL = "goals-create"

export function useCreateGoal(options?: { silent?: boolean }) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: GoalCreate) =>
      api.post<Goal>("/bagcoin/goals", data),
    onSuccess: () => {
      toast.dismiss(TOAST_ID_CREATE_GOAL)
      qc.invalidateQueries({ queryKey: ["goals"] })
      if (!options?.silent) {
        toast.success("Meta criada com sucesso!", { id: TOAST_ID_CREATE_GOAL })
      }
    },
    onError: (err: Error) => {
      toast.dismiss(TOAST_ID_CREATE_GOAL)
      console.error('[hook:goals]', err)
      if (!options?.silent) {
        toast.error("Não foi possível criar a meta. Tente novamente.", { id: TOAST_ID_CREATE_GOAL })
      }
    },
  })
}

const TOAST_ID_UPDATE_GOAL = "goals-update"

export function useUpdateGoal(options?: { silent?: boolean }) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: GoalUpdate }) =>
      api.patch<Goal>(`/bagcoin/goals/${id}`, data),
    onSuccess: () => {
      toast.dismiss(TOAST_ID_UPDATE_GOAL)
      qc.invalidateQueries({ queryKey: ["goals"] })
      if (!options?.silent) {
        toast.success("Meta atualizada com sucesso!", { id: TOAST_ID_UPDATE_GOAL })
      }
    },
    onError: (err: Error) => {
      toast.dismiss(TOAST_ID_UPDATE_GOAL)
      console.error('[hook:goals]', err)
      if (!options?.silent) {
        toast.error("Não foi possível atualizar a meta. Tente novamente.", { id: TOAST_ID_UPDATE_GOAL })
      }
    },
  })
}

const TOAST_ID_DELETE_GOAL = "goals-delete"

export function useDeleteGoal(options?: { silent?: boolean }) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      api.delete(`/bagcoin/goals/${id}`),
    onSuccess: () => {
      toast.dismiss(TOAST_ID_DELETE_GOAL)
      qc.invalidateQueries({ queryKey: ["goals"] })
      if (!options?.silent) {
        toast.success("Meta excluída com sucesso!", { id: TOAST_ID_DELETE_GOAL })
      }
    },
    onError: (err: Error) => {
      toast.dismiss(TOAST_ID_DELETE_GOAL)
      console.error('[hook:goals]', err)
      if (!options?.silent) {
        toast.error("Não foi possível excluir a meta. Tente novamente.", { id: TOAST_ID_DELETE_GOAL })
      }
    },
  })
}
