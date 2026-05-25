import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { SettingsDrawer } from "@/components/layout/shared/settings-drawer"

const mockPush = vi.fn()
const mockCloseDrawer = vi.fn()
const mockOpenIntegrationChat = vi.fn()
let drawerOpen = true

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => "/app/transacoes",
}))

vi.mock("@/lib/auth-store", () => ({
  useAuthStore: Object.assign(
    () => ({
      user: {
        email: "ana@bagcoin.com",
        full_name: "Ana Silva",
        phone_number: null,
        avatar_url: null,
      },
    }),
    {
      getState: () => ({
        user: {
          email: "ana@bagcoin.com",
          full_name: "Ana Silva",
          phone_number: null,
          avatar_url: null,
        },
      }),
    }
  ),
}))

vi.mock("@/lib/store", () => ({
  useAppStore: () => ({
    drawerOpen,
    closeDrawer: mockCloseDrawer,
  }),
}))

vi.mock("@/hooks/use-integrations", () => ({
  useOpenIntegrationChat: () => ({
    openIntegrationChat: mockOpenIntegrationChat,
    openingChannel: null,
  }),
}))

describe("SettingsDrawer", () => {
  beforeEach(() => {
    drawerOpen = true
    vi.clearAllMocks()
  })

  it("abre pela esquerda e mostra todas as opções úteis", () => {
    render(<SettingsDrawer />)

    expect(document.body.innerHTML).not.toContain("data-slot=\"sheet-content\"")
    expect(screen.getByLabelText("Fechar menu")).toHaveClass("rls-drawer-backdrop")
    expect(screen.getByLabelText("Menu")).toHaveClass("rls-drawer-panel")
    expect(screen.getByText("Início")).toBeInTheDocument()
    expect(screen.getByText("Transações")).toBeInTheDocument()
    expect(screen.getByText("Categorias")).toBeInTheDocument()
    expect(screen.getByText("Orçamentos")).toBeInTheDocument()
    expect(screen.getByText("Metas")).toBeInTheDocument()
    expect(screen.getByText("Perfil")).toBeInTheDocument()
    expect(screen.getByText("Suporte")).toBeInTheDocument()
    expect(screen.queryByText("Relatórios")).not.toBeInTheDocument()
    expect(screen.getByText("WhatsApp")).toBeInTheDocument()
    expect(screen.queryByText("Telegram")).not.toBeInTheDocument()
    expect(screen.queryByText("Aparência")).not.toBeInTheDocument()
    expect(screen.queryByText("Notificações")).not.toBeInTheDocument()
    expect(screen.queryByText("Privacidade")).not.toBeInTheDocument()
    expect(screen.queryByText("Sair")).not.toBeInTheDocument()
    expect(screen.queryByText("ana@bagcoin.com")).not.toBeInTheDocument()
    expect(screen.getByText("Ana Silva")).toBeInTheDocument()
  })

  it("fecha ao clicar no backdrop", () => {
    render(<SettingsDrawer />)

    fireEvent.click(screen.getByLabelText("Fechar menu"))

    expect(mockCloseDrawer).toHaveBeenCalled()
  })

  it("navega por links reais e fecha o drawer", () => {
    render(<SettingsDrawer />)

    fireEvent.click(screen.getByText("Perfil"))
    expect(mockCloseDrawer).toHaveBeenCalled()
    expect(mockPush).toHaveBeenCalledWith("/app/perfil")

    fireEvent.click(screen.getByText("Suporte"))
    expect(mockPush).toHaveBeenCalledWith("/app/suporte")

    fireEvent.click(screen.getByText("WhatsApp"))
    expect(mockOpenIntegrationChat).toHaveBeenCalledWith("whatsapp")
  })

})
