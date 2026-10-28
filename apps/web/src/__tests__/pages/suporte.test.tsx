import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import SuportePage from "@/app/app/suporte/page"
import { api } from "@/lib/api-client"
import { toast } from "sonner"

const mockToggleDrawer = vi.fn()

vi.mock("@/lib/store", () => ({
  useAppStore: (selector?: (state: { toggleDrawer: typeof mockToggleDrawer }) => unknown) => {
    const state = { toggleDrawer: mockToggleDrawer }
    return selector ? selector(state) : state
  },
}))

vi.mock("@/lib/api-client", () => ({
  api: { post: vi.fn() },
}))

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe("SuportePage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renderiza apenas a área de envio de mensagem para suporte", () => {
    render(<SuportePage />)

    expect(screen.getByText("Suporte")).toBeInTheDocument()
    expect(screen.getByLabelText("Assunto")).toBeInTheDocument()
    expect(screen.getByLabelText("Mensagem para o suporte")).toBeInTheDocument()
    expect(screen.getByText("Enviar mensagem")).toBeInTheDocument()
    expect(screen.queryByText("Aparência")).not.toBeInTheDocument()
    expect(screen.queryByText("Preferências")).not.toBeInTheDocument()
    expect(screen.queryByText("WhatsApp")).not.toBeInTheDocument()
    expect(screen.queryByText("Privacidade")).not.toBeInTheDocument()
  })

  it("envia mensagem, limpa o formulário e exibe toast de sucesso", async () => {
    vi.mocked(api.post).mockResolvedValueOnce({})
    render(<SuportePage />)

    fireEvent.change(screen.getByLabelText("Assunto"), { target: { value: "  Ajuda  " } })
    fireEvent.change(screen.getByLabelText("Mensagem para o suporte"), { target: { value: "  Preciso de ajuda  " } })
    fireEvent.click(screen.getByText("Enviar mensagem"))

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/support/contact", {
        subject: "Ajuda",
        message: "Preciso de ajuda",
      })
      expect(toast.success).toHaveBeenCalledWith("Mensagem enviada ao suporte.")
    })
    expect(screen.getByLabelText("Assunto")).toHaveValue("")
    expect(screen.getByLabelText("Mensagem para o suporte")).toHaveValue("")
  })

  it("bloqueia assunto com menos de 3 caracteres antes do POST", () => {
    render(<SuportePage />)

    fireEvent.change(screen.getByLabelText("Assunto"), { target: { value: "oi" } })
    fireEvent.change(screen.getByLabelText("Mensagem para o suporte"), { target: { value: "Preciso de ajuda" } })
    fireEvent.click(screen.getByText("Enviar mensagem"))

    expect(api.post).not.toHaveBeenCalled()
    expect(toast.error).toHaveBeenCalledWith("Informe um assunto com pelo menos 3 caracteres.")
  })

  it("bloqueia mensagem com menos de 10 caracteres antes do POST", () => {
    render(<SuportePage />)

    fireEvent.change(screen.getByLabelText("Assunto"), { target: { value: "Ajuda" } })
    fireEvent.change(screen.getByLabelText("Mensagem para o suporte"), { target: { value: "curta" } })
    fireEvent.click(screen.getByText("Enviar mensagem"))

    expect(api.post).not.toHaveBeenCalled()
    expect(toast.error).toHaveBeenCalledWith("Informe uma mensagem com pelo menos 10 caracteres.")
  })

  it("usa erro seguro ao falhar", async () => {
    vi.mocked(api.post).mockRejectedValueOnce(new Error("Internal Server Error"))
    render(<SuportePage />)

    fireEvent.change(screen.getByLabelText("Assunto"), { target: { value: "Ajuda" } })
    fireEvent.change(screen.getByLabelText("Mensagem para o suporte"), { target: { value: "Preciso de ajuda" } })
    fireEvent.click(screen.getByText("Enviar mensagem"))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Não foi possível enviar sua mensagem. Tente novamente em instantes.")
    })
    expect(toast.error).not.toHaveBeenCalledWith("Internal Server Error")
  })
})
