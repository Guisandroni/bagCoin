import { describe, it, expect, vi } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useBudgets, useBudget, useCreateBudget, useUpdateBudget, useDeleteBudget } from "@/hooks/use-budgets"
import type { ReactNode } from "react"

const mockBudgets = vi.hoisted(() => ({
  items: [
    { id: 1, name: "Mercado Mensal", period: "monthly", total_limit: 1000, total_spent: 250, total_remaining: 750, percentage: 25, budget_type: "general", category_id: 1, category_name: "Alimentação", created_at: "2026-04-01T00:00:00Z", updated_at: null },
    { id: 2, name: "Lazer", period: "monthly", total_limit: 500, total_spent: 100, total_remaining: 400, percentage: 20, budget_type: "general", category_id: null, category_name: null, created_at: "2026-04-01T00:00:00Z", updated_at: null },
  ],
  total: 2,
}))

const mockBudgetSingle = vi.hoisted(() => ({
  id: 1, name: "Mercado Mensal", period: "monthly", total_limit: 1000, total_spent: 250, total_remaining: 750, percentage: 25, budget_type: "general", category_id: 1, category_name: "Alimentação", created_at: "2026-04-01T00:00:00Z", updated_at: null,
}))

vi.mock("@/lib/api-client", () => ({
  default: {},
  api: {
    get: vi.fn().mockImplementation((url: string) => {
      if (url.includes("budgets/1")) return Promise.resolve(mockBudgetSingle)
      return Promise.resolve(mockBudgets)
    }),
    post: vi.fn().mockImplementation((_url: string, body: Record<string, unknown>) =>
      Promise.resolve({ ...mockBudgetSingle, ...body, id: 99 })
    ),
    patch: vi.fn().mockImplementation((_url: string, body: Record<string, unknown>) =>
      Promise.resolve({ ...mockBudgetSingle, ...body })
    ),
    delete: vi.fn().mockResolvedValue(undefined),
  },
  getTokenStore: () => ({ getAccessToken: () => null }),
  setAuthCookies: () => {},
  clearAuthCookies: () => {},
}))

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

describe("useBudgets", () => {
  it("retorna lista de orcamentos", async () => {
    const { result } = renderHook(() => useBudgets(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.items).toHaveLength(2)
    expect(result.current.data?.total).toBe(2)
    expect(result.current.data?.items[0].name).toBe("Mercado Mensal")
    expect(result.current.data?.items[0].percentage).toBe(25)
  })
})

describe("useBudget", () => {
  it("retorna um orcamento pelo ID", async () => {
    const { result } = renderHook(() => useBudget(1), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.name).toBe("Mercado Mensal")
    expect(result.current.data?.total_limit).toBe(1000)
  })
})

describe("useCreateBudget", () => {
  it("cria um novo orcamento", async () => {
    const { result } = renderHook(() => useCreateBudget(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isIdle).toBe(true))
    const res = await result.current.mutateAsync({ name: "Novo", period: "monthly", total_limit: 2000 })
    expect(res.name).toBe("Novo")
  })
})

describe("useUpdateBudget", () => {
  it("atualiza um orcamento", async () => {
    const { result } = renderHook(() => useUpdateBudget(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isIdle).toBe(true))
    const res = await result.current.mutateAsync({ id: 1, data: { name: "Atualizado" } })
    expect(res.name).toBe("Atualizado")
  })
})

describe("useDeleteBudget", () => {
  it("exclui um orcamento", async () => {
    const { result } = renderHook(() => useDeleteBudget(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isIdle).toBe(true))
    await expect(result.current.mutateAsync(1)).resolves.toBeUndefined()
  })
})
