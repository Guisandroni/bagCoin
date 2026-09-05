import { describe, it, expect, vi } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useGoals, useCreateGoal, useUpdateGoal, useDeleteGoal } from "@/hooks/use-goals"
import type { ReactNode } from "react"

const mockGoals = vi.hoisted(() => ({
  items: [
    { id: 1, title: "Viagem Europa", target_amount: 15000, current_amount: 5000, deadline: "2026-12-31T00:00:00Z", status: "active", created_at: "2026-01-01T00:00:00Z", updated_at: null },
    { id: 2, title: "Fundo de Emergência", target_amount: 30000, current_amount: 30000, deadline: null, status: "completed", created_at: "2026-01-01T00:00:00Z", updated_at: null },
  ],
  total: 2,
}))

vi.mock("@/lib/api-client", () => ({
  default: {},
  api: {
    get: vi.fn().mockResolvedValue(mockGoals),
    post: vi.fn().mockImplementation((_url: string, body: Record<string, unknown>) =>
      Promise.resolve({ ...mockGoals.items[0], ...body, id: 99 })
    ),
    patch: vi.fn().mockImplementation((_url: string, body: Record<string, unknown>) =>
      Promise.resolve({ ...mockGoals.items[0], ...body })
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

describe("useGoals", () => {
  it("retorna lista de metas", async () => {
    const { result } = renderHook(() => useGoals(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.items).toHaveLength(2)
    expect(result.current.data?.total).toBe(2)
    expect(result.current.data?.items[0].title).toBe("Viagem Europa")
    expect(result.current.data?.items[0].status).toBe("active")
    expect(result.current.data?.items[1].status).toBe("completed")
  })
})

describe("useCreateGoal", () => {
  it("cria uma nova meta", async () => {
    const { result } = renderHook(() => useCreateGoal(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isIdle).toBe(true))
    const res = await result.current.mutateAsync({ title: "Nova Meta", target_amount: 5000 })
    expect(res.title).toBe("Nova Meta")
  })
})

describe("useUpdateGoal", () => {
  it("atualiza uma meta", async () => {
    const { result } = renderHook(() => useUpdateGoal(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isIdle).toBe(true))
    const res = await result.current.mutateAsync({ id: 1, data: { title: "Meta Atualizada" } })
    expect(res.title).toBe("Meta Atualizada")
  })
})

describe("useDeleteGoal", () => {
  it("exclui uma meta", async () => {
    const { result } = renderHook(() => useDeleteGoal(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isIdle).toBe(true))
    await expect(result.current.mutateAsync(1)).resolves.toBeUndefined()
  })
})
