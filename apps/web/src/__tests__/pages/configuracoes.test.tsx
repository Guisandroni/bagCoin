import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import ConfiguracoesPage from "@/app/app/configuracoes/page"

const mockSetTheme = vi.fn()
const mockToggleDrawer = vi.fn()
let mockTheme = "dark"

vi.mock("next-themes", () => ({
  useTheme: () => ({
    theme: mockTheme,
    setTheme: mockSetTheme,
  }),
}))

vi.mock("@/lib/store", () => ({
  useAppStore: (selector?: (state: { toggleDrawer: typeof mockToggleDrawer }) => unknown) => {
    const state = { toggleDrawer: mockToggleDrawer }
    return selector ? selector(state) : state
  },
}))

describe("ConfiguracoesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockTheme = "dark"
  })

  it("renderiza título e botão de abrir drawer", () => {
    render(<ConfiguracoesPage />)
    expect(screen.getByText("Configurações")).toBeInTheDocument()

    fireEvent.click(screen.getByLabelText("Abrir menu"))
    expect(mockToggleDrawer).toHaveBeenCalled()
  })

  it("renderiza as três opções de aparência", () => {
    render(<ConfiguracoesPage />)
    expect(screen.getByText("Claro")).toBeInTheDocument()
    expect(screen.getByText("Escuro")).toBeInTheDocument()
    expect(screen.getByText("Sistema")).toBeInTheDocument()
  })

  it("chama setTheme ao clicar nas opções", () => {
    render(<ConfiguracoesPage />)
    fireEvent.click(screen.getByText("Claro"))
    fireEvent.click(screen.getByText("Escuro"))
    fireEvent.click(screen.getByText("Sistema"))

    expect(mockSetTheme).toHaveBeenCalledWith("light")
    expect(mockSetTheme).toHaveBeenCalledWith("dark")
    expect(mockSetTheme).toHaveBeenCalledWith("system")
  })

  it("não renderiza o formulário de suporte dentro das configurações", () => {
    render(<ConfiguracoesPage />)

    expect(screen.queryByText("Suporte")).not.toBeInTheDocument()
    expect(screen.queryByLabelText("Assunto")).not.toBeInTheDocument()
    expect(screen.queryByLabelText("Mensagem para o suporte")).not.toBeInTheDocument()
    expect(screen.queryByText("Enviar mensagem")).not.toBeInTheDocument()
  })
})
