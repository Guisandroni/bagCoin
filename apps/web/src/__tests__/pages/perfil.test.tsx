import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import PerfilPage from "@/app/app/perfil/page"

const mockToggleDrawer = vi.fn()
const mockLogout = vi.fn()

vi.mock("@/lib/store", () => ({
  useAppStore: (selector?: (state: { toggleDrawer: typeof mockToggleDrawer }) => unknown) => {
    const state = { toggleDrawer: mockToggleDrawer }
    return selector ? selector(state) : state
  },
}))

vi.mock("@/lib/auth-store", () => ({
  useAuthStore: Object.assign(
    (selector?: (state: { logout: typeof mockLogout }) => unknown) => {
      const state = { logout: mockLogout }
      return selector ? selector(state) : state
    },
    {
      getState: () => ({
        user: {
          email: "ana@bagcoin.com",
          full_name: "Ana Silva",
          phone_number: "+55 11 99999-1234",
          avatar_url: null,
        },
      }),
    }
  ),
}))

describe("PerfilPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renderiza perfil read-only com drawer e volta para início", () => {
    render(<PerfilPage />)

    expect(screen.getByText("Perfil")).toBeInTheDocument()
    expect(screen.getByText("Ana Silva")).toBeInTheDocument()
    expect(screen.queryByText("Segurança")).not.toBeInTheDocument()
    expect(screen.queryByText("Alterar Senha")).not.toBeInTheDocument()
    expect(screen.queryByText("Salvar Alterações")).not.toBeInTheDocument()
    expect(screen.getByText("Sair da Conta")).toBeInTheDocument()
    expect(screen.queryByLabelText("Início")).not.toBeInTheDocument()
    expect(screen.getByLabelText("Telefone")).toHaveAttribute("readOnly")

    fireEvent.click(screen.getByLabelText("Abrir menu"))
    expect(mockToggleDrawer).toHaveBeenCalled()

    fireEvent.click(screen.getByText("Sair da Conta"))
    expect(mockLogout).toHaveBeenCalled()
  })

  it("inicia com telefone escondido e permite alternar visibilidade", () => {
    render(<PerfilPage />)

    expect(screen.getByLabelText("Telefone")).toHaveValue("+•• •• •••••-1234")
    fireEvent.click(screen.getByLabelText("Mostrar telefone"))
    expect(screen.getByLabelText("Telefone")).toHaveValue("+55 11 99999-1234")
  })
})
