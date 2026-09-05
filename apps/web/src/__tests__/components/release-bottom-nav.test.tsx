import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import { BottomNavBar } from "@/components/release/bottom-nav-bar"

describe("BottomNavBar", () => {
  const items = [
    { label: "Início", icon: "home", href: "/app", isActive: true },
    { label: "Transações", icon: "portfolio", href: "/app/transacoes" },
  ]

  it("fica flutuante no frame central da aplicação", () => {
    const onNavigate = vi.fn()
    render(<BottomNavBar items={items} onNavigate={onNavigate} />)

    const nav = screen.getByRole("navigation")
    expect(nav).toHaveClass("rls-floating-bottom-nav")
    expect(nav).not.toHaveClass("bottom-0")
    expect(nav).not.toHaveClass("border-t")

    fireEvent.click(screen.getByText("Transações"))
    expect(onNavigate).toHaveBeenCalledWith("/app/transacoes")
  })
})
