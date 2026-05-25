"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import apiClient, { api } from "@/lib/api-client"
import { toast } from "sonner"

export interface Report {
  id: number
  user_uuid: string | null
  period_start: string
  period_end: string
  file_url: string | null
  created_at: string
  updated_at: string
}

export interface ReportListResponse {
  items: Report[]
  total: number
}

export interface ReportGenerateRequest {
  report_type: "monthly" | "category" | "budget"
  month: number
  year: number
}

export interface ReportGenerateResponse extends Report {
  summary: {
    total_income: number
    total_expense: number
    balance: number
    transaction_count: number
  }
}

export function useReports() {
  return useQuery({
    queryKey: ["reports"],
    queryFn: async () => {
      const data = await api.get<Report[]>("/bagcoin/reports")
      if (Array.isArray(data)) return { items: data, total: data.length } as ReportListResponse
      return (data as unknown as ReportListResponse)
    },
  })
}

export function useReport(id: number) {
  return useQuery({
    queryKey: ["reports", id],
    queryFn: () => api.get<Report>(`/bagcoin/reports/${id}`),
    enabled: !!id,
  })
}

const TOAST_ID_CREATE_REPORT = "reports-create"

export function useCreateReport() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ReportGenerateRequest) =>
      api.post<ReportGenerateResponse>("/bagcoin/reports", body),
    onSuccess: () => {
      toast.dismiss(TOAST_ID_CREATE_REPORT)
      qc.invalidateQueries({ queryKey: ["reports"] })
      toast.success("Relatório gerado com sucesso!", { id: TOAST_ID_CREATE_REPORT })
    },
    onError: (err: Error) => {
      toast.dismiss(TOAST_ID_CREATE_REPORT)
      console.error('[hook:reports]', err)
      toast.error("Não foi possível gerar o relatório. Tente novamente.", { id: TOAST_ID_CREATE_REPORT })
    },
  })
}

const TOAST_ID_DELETE_REPORT = "reports-delete"

export function useDeleteReport() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      api.delete(`/bagcoin/reports/${id}`),
    onSuccess: () => {
      toast.dismiss(TOAST_ID_DELETE_REPORT)
      qc.invalidateQueries({ queryKey: ["reports"] })
      toast.success("Relatório excluído com sucesso!", { id: TOAST_ID_DELETE_REPORT })
    },
    onError: (err: Error) => {
      toast.dismiss(TOAST_ID_DELETE_REPORT)
      console.error('[hook:reports]', err)
      toast.error("Não foi possível excluir o relatório. Tente novamente.", { id: TOAST_ID_DELETE_REPORT })
    },
  })
}

const TOAST_ID_DOWNLOAD_REPORT = "reports-download"

export function useDownloadReport() {
  return useMutation({
    mutationFn: async (reportId: number) => {
      const { data } = await apiClient.get(`/bagcoin/reports/${reportId}/download`, {
        responseType: "blob",
      })
      return data as Blob
    },
    onSuccess: (blob, reportId) => {
      toast.dismiss(TOAST_ID_DOWNLOAD_REPORT)
      const u = URL.createObjectURL(blob)
      window.open(u, "_blank")
      URL.revokeObjectURL(u)
    },
    onError: (err: Error) => {
      toast.dismiss(TOAST_ID_DOWNLOAD_REPORT)
      console.error('[hook:reports]', err)
      toast.error("Não foi possível baixar o relatório. Tente novamente.", { id: TOAST_ID_DOWNLOAD_REPORT })
    },
  })
}
