import { afterEach, describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { ToastBanner } from "@/components/release/toast-banner"

describe("ToastBanner", () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it("renderiza variante destrutiva para erros", () => {
    render(
      <ToastBanner
        isOpen
        message="Erro ao excluir transação. Tente novamente."
        variant="error"
      />
    )

    const toast = screen.getByText("Erro ao excluir transação. Tente novamente.").closest("div")
    expect(toast).toHaveClass("bg-[var(--rls-error-container)]")
    expect(toast).toHaveClass("text-[var(--rls-on-error-container)]")
  })

  it("renderiza sucesso com o estilo release antigo", () => {
    render(
      <ToastBanner
        isOpen
        message="Meta criada com sucesso."
        variant="success"
      />
    )

    const toast = screen.getByText("Meta criada com sucesso.").closest("div")
    expect(toast).toHaveClass("bg-[var(--rls-secondary-container)]/20")
    expect(toast).toHaveClass("text-[var(--rls-on-secondary-container)]")
  })

  it("fica alinhado ao frame central e mais baixo na tela", () => {
    render(
      <ToastBanner
        isOpen
        message="Transação excluída com sucesso."
      />
    )

    const toast = screen.getByText("Transação excluída com sucesso.").closest("div")
    expect(toast).toHaveClass("top-[88px]")
    expect(toast).toHaveClass("left-1/2")
    expect(toast).toHaveClass("w-[calc(min(100%,28rem)-24px)]")
  })

  it("fecha automaticamente após a duração configurada", () => {
    vi.useFakeTimers()
    const onClose = vi.fn()
    render(
      <ToastBanner
        isOpen
        message="Transação excluída com sucesso."
        onClose={onClose}
        duration={1200}
      />
    )

    vi.advanceTimersByTime(1200)

    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
