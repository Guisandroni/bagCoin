import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { act, renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import { openIntegrationChat, useOpenIntegrationChat } from "@/hooks/use-integrations"
import apiClient from "@/lib/api-client"

vi.mock("@/lib/api-client", () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  },
}))

function createWrapper(queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

function mockLinkToken(deeplink = "https://wa.me/5511999999999?text=bagcoin") {
  vi.mocked(apiClient.post).mockResolvedValue({
    data: {
      token: "token-123",
      expires_at: "2026-05-09T23:00:00Z",
      deeplink_whatsapp: deeplink,
      deeplink_telegram: "https://t.me/bagcoin_bot?start=token-123",
      manual_command_whatsapp: "bagcoin token-123",
      manual_command_telegram: "/start token-123",
    },
  })
}

describe("openIntegrationChat", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, "warn").mockImplementation(() => {})
    vi.spyOn(window, "open").mockReturnValue(null)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("abre o chatbot em nova aba sem redirecionar a aba atual quando o popup é bloqueado", async () => {
    mockLinkToken()
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const originalHref = window.location.href

    await openIntegrationChat("whatsapp", queryClient)

    expect(window.open).toHaveBeenCalledWith(
      "https://wa.me/5511999999999?text=bagcoin",
      "_blank",
      "noopener,noreferrer"
    )
    expect(window.location.href).toBe(originalHref)
  })
})

describe("useOpenIntegrationChat", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, "error").mockImplementation(() => {})
    vi.spyOn(console, "warn").mockImplementation(() => {})
    vi.spyOn(window, "open").mockReturnValue({ closed: false } as Window)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("ignora chamadas repetidas enquanto um chatbot já está abrindo", async () => {
    let resolvePost: (value: unknown) => void = () => {}
    vi.mocked(apiClient.post).mockReturnValue(
      new Promise((resolve) => {
        resolvePost = resolve
      }) as ReturnType<typeof apiClient.post>
    )
    const { result } = renderHook(() => useOpenIntegrationChat(), {
      wrapper: createWrapper(),
    })

    act(() => {
      void result.current.openIntegrationChat("whatsapp")
      void result.current.openIntegrationChat("whatsapp")
    })

    expect(apiClient.post).toHaveBeenCalledTimes(1)

    resolvePost({
      data: {
        token: "token-123",
        expires_at: "2026-05-09T23:00:00Z",
        deeplink_whatsapp: "https://wa.me/5511999999999?text=bagcoin",
        deeplink_telegram: "https://t.me/bagcoin_bot?start=token-123",
        manual_command_whatsapp: "bagcoin token-123",
        manual_command_telegram: "/start token-123",
      },
    })

    await waitFor(() => expect(result.current.openingChannel).toBeNull())
    expect(window.open).toHaveBeenCalledTimes(1)
  })
})
