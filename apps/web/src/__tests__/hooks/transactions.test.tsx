import { describe, it, expect, vi } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useTransactions, useTransactionSummary, useCreateTransaction, useUpdateTransaction, useDeleteTransaction } from "@/hooks/use-transactions"
import type { ReactNode } from "react"

const mockTxList = vi.hoisted(() => ({
  items: [
    { id: "1", type: "EXPENSE", name: "Supermercado", category: "Alimentação", amount: 287.5, date: "30 Abr", source: "manual", status: "confirmed" },
    { id: "2", type: "INCOME", name: "Salário", category: "Salário", amount: 8500, date: "28 Abr", source: "auto", status: "confirmed" },
    { id: "3", type: "EXPENSE", name: "Uber", category: "Transporte", amount: 35, date: "29 Abr", source: "manual", status: "pending" },
  ],
  total: 3,
}))

const mockSummaryData = vi.hoisted(() => ({
  balance: 8177.5,
  total_income: 8500,
  total_expenses: 322.5,
  transaction_count: 3,
  categories: [
    { name: "Alimentação", amount: 287.5, color: "#ff6b35" },
    { name: "Transporte", amount: 35, color: "#0052ff" },
  ],
  recent_transactions: mockTxList.items,
}))

vi.mock("@/lib/api-client", () => ({
  api: {
    get: vi.fn().mockImplementation((url: string) => {
      if (url.includes("summary")) return Promise.resolve(mockSummaryData)
      return Promise.resolve(mockTxList)
    }),
    post: vi.fn().mockImplementation((_url: string, body: Record<string, unknown>) => {
      const merged = { ...mockTxList.items[0], ...body, id: "99" }
      if (body?.description) merged.name = String(body.description)
      return Promise.resolve(merged)
    }),
    patch: vi.fn().mockImplementation((_url: string, body: Record<string, unknown>) => {
      const merged = { ...mockTxList.items[0], ...body }
      if (body?.description) merged.name = String(body.description)
      return Promise.resolve(merged)
    }),
    delete: vi.fn().mockResolvedValue(undefined),
  },
  default: {
    get: vi.fn().mockResolvedValue({ data: mockTxList }),
    post: vi.fn().mockResolvedValue({ data: {} }),
    patch: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn().mockResolvedValue({ data: undefined }),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  },
  getTokenStore: () => ({ getAccessToken: () => null }),
  setAuthCookies: vi.fn(),
  clearAuthCookies: vi.fn(),
}))

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), dismiss: vi.fn() },
}))



function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

describe("useTransactions", () => {
  it("retorna lista sem filtros", async () => {
    const { result } = renderHook(() => useTransactions(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.items).toHaveLength(3)
    expect(result.current.data?.total).toBe(3)
  })

  it("retorna com filtro de tipo", async () => {
    const { result } = renderHook(() => useTransactions({ type: "EXPENSE" }), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total).toBe(3)
  })

  it("retorna com busca", async () => {
    const { result } = renderHook(() => useTransactions({ search: "Super" }), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.items[0].name).toBe("Supermercado")
  })
})

describe("useTransactionSummary", () => {
  it("retorna sumario do dashboard", async () => {
    const { result } = renderHook(() => useTransactionSummary(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.balance).toBe(8177.5)
    expect(result.current.data?.total_income).toBe(8500)
    expect(result.current.data?.total_expenses).toBe(322.5)
    expect(result.current.data?.transaction_count).toBe(3)
    expect(result.current.data?.categories).toHaveLength(2)
    expect(result.current.data?.recent_transactions).toHaveLength(3)
  })
})

describe("useCreateTransaction", () => {
  it("cria uma transacao", async () => {
    const { result } = renderHook(() => useCreateTransaction(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isIdle).toBe(true))
    const res = await result.current.mutateAsync({ type: "EXPENSE", amount: 50, description: "Teste" })
    expect(res.id).toBe("99")
    expect(res.name).toBe("Teste")
  })
})

describe("useUpdateTransaction", () => {
  it("atualiza uma transacao", async () => {
    const { result } = renderHook(() => useUpdateTransaction(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isIdle).toBe(true))
    const res = await result.current.mutateAsync({ id: "1", description: "Atualizado" })
    expect(res.name).toBe("Atualizado")
  })
})

describe("useDeleteTransaction", () => {
  it("exclui uma transacao", async () => {
    const { result } = renderHook(() => useDeleteTransaction(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isIdle).toBe(true))
    await expect(result.current.mutateAsync("1")).resolves.toBeUndefined()
  })
})
