import { describe, it, expect, vi } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useAccounts, useCreateAccount, useUpdateAccount, useDeleteAccount } from "@/hooks/use-accounts"
import type { ReactNode } from "react"

const mockAccounts = vi.hoisted(() => [
  { id: 1, name: "NuBank", type: "CHECKING", balance: 5200, bank: "NuBank", color: "#7c3aed", created_at: "2026-04-01T00:00:00Z" },
  { id: 2, name: "Poupança", type: "SAVINGS", balance: 12000, bank: "Bradesco", color: "#0052ff", created_at: "2026-04-01T00:00:00Z" },
])

vi.mock("@/lib/api-client", () => ({
  default: {},
  api: {
    get: vi.fn().mockResolvedValue(mockAccounts),
    post: vi.fn().mockImplementation((_url: string, body: Record<string, unknown>) =>
      Promise.resolve({ ...mockAccounts[0], ...body, id: 99 })
    ),
    patch: vi.fn().mockImplementation((_url: string, body: Record<string, unknown>) =>
      Promise.resolve({ ...mockAccounts[0], ...body })
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

describe("useAccounts", () => {
  it("retorna lista de contas", async () => {
    const { result } = renderHook(() => useAccounts(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toHaveLength(2)
    expect(result.current.data![0].name).toBe("NuBank")
    expect(result.current.data![0].balance).toBe(5200)
  })
})

describe("useCreateAccount", () => {
  it("dispara mutation POST", async () => {
    const { result } = renderHook(() => useCreateAccount(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isIdle).toBe(true))
    const res = await result.current.mutateAsync({ name: "Nova Conta", type: "CHECKING", balance: 1000 })
    expect(res.name).toBe("Nova Conta")
  })
})

describe("useUpdateAccount", () => {
  it("dispara mutation PATCH", async () => {
    const { result } = renderHook(() => useUpdateAccount(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isIdle).toBe(true))
    const res = await result.current.mutateAsync({ id: 1, data: { name: "Conta Atualizada" } })
    expect(res.name).toBe("Conta Atualizada")
  })
})

describe("useDeleteAccount", () => {
  it("dispara mutation DELETE", async () => {
    const { result } = renderHook(() => useDeleteAccount(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isIdle).toBe(true))
    await expect(result.current.mutateAsync(1)).resolves.toBeUndefined()
  })
})
