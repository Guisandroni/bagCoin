import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import { LoginCard } from "@/components/release/login-card"
import { RegisterCard } from "@/components/release/register-card"

describe("release auth password toggle", () => {
  it("alterna visibilidade da senha no login", () => {
    render(<LoginCard />)

    const password = screen.getByLabelText("Senha")
    expect(password).toHaveAttribute("type", "password")

    fireEvent.click(screen.getByLabelText("Mostrar senha"))
    expect(password).toHaveAttribute("type", "text")

    fireEvent.click(screen.getByLabelText("Ocultar senha"))
    expect(password).toHaveAttribute("type", "password")
  })

  it("alterna visibilidade das senhas no registro", () => {
    render(<RegisterCard />)

    const password = screen.getByLabelText("Senha")
    const confirmPassword = screen.getByLabelText("Confirmar Senha")
    expect(password).toHaveAttribute("type", "password")
    expect(confirmPassword).toHaveAttribute("type", "password")

    const toggles = screen.getAllByLabelText("Mostrar senha")
    fireEvent.click(toggles[0])
    fireEvent.click(toggles[1])

    expect(password).toHaveAttribute("type", "text")
    expect(confirmPassword).toHaveAttribute("type", "text")
  })

  it("mostra erro inline para senha sem complexidade", () => {
    const onRegister = vi.fn()
    render(<RegisterCard onRegister={onRegister} />)

    fireEvent.change(screen.getByLabelText("Nome Completo"), { target: { value: "Ana Silva" } })
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "ana@bagcoin.com" } })
    fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "abcdef" } })
    fireEvent.change(screen.getByLabelText("Confirmar Senha"), { target: { value: "abcdef" } })
    fireEvent.click(screen.getByRole("button", { name: /criar conta/i }))

    expect(onRegister).not.toHaveBeenCalled()
    expect(screen.getByText("Senha deve conter letra maiúscula, letra minúscula e número")).toBeInTheDocument()
    expect(
      screen.getByText("Senha incorreta. Use no mínimo 6 caracteres, com letra maiúscula, letra minúscula e número."),
    ).toBeInTheDocument()
  })

  it("atualiza checklist da senha em tempo real no cadastro", () => {
    render(<RegisterCard />)

    const password = screen.getByLabelText("Senha")
    const minLength = screen.getByTestId("password-check-min-length")
    const uppercase = screen.getByTestId("password-check-uppercase")
    const lowercase = screen.getByTestId("password-check-lowercase")
    const number = screen.getByTestId("password-check-number")

    expect(minLength).toHaveAttribute("data-status", "pending")
    expect(uppercase).toHaveAttribute("data-status", "pending")
    expect(lowercase).toHaveAttribute("data-status", "pending")
    expect(number).toHaveAttribute("data-status", "pending")

    fireEvent.change(password, { target: { value: "abc" } })
    expect(lowercase).toHaveAttribute("data-status", "ok")
    expect(minLength).toHaveAttribute("data-status", "pending")
    expect(uppercase).toHaveAttribute("data-status", "pending")
    expect(number).toHaveAttribute("data-status", "pending")

    fireEvent.change(password, { target: { value: "Abc" } })
    expect(uppercase).toHaveAttribute("data-status", "ok")
    expect(lowercase).toHaveAttribute("data-status", "ok")
    expect(minLength).toHaveAttribute("data-status", "pending")
    expect(number).toHaveAttribute("data-status", "pending")

    fireEvent.change(password, { target: { value: "Abc1" } })
    expect(number).toHaveAttribute("data-status", "ok")
    expect(minLength).toHaveAttribute("data-status", "pending")

    fireEvent.change(password, { target: { value: "Abcdef1" } })
    expect(minLength).toHaveAttribute("data-status", "ok")
    expect(uppercase).toHaveAttribute("data-status", "ok")
    expect(lowercase).toHaveAttribute("data-status", "ok")
    expect(number).toHaveAttribute("data-status", "ok")
  })

  it("mostra erro inline quando as senhas não coincidem", () => {
    const onRegister = vi.fn()
    render(<RegisterCard onRegister={onRegister} />)

    fireEvent.change(screen.getByLabelText("Nome Completo"), { target: { value: "Ana Silva" } })
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "ana@bagcoin.com" } })
    fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "Abcdef1" } })
    fireEvent.change(screen.getByLabelText("Confirmar Senha"), { target: { value: "Abcdef2" } })
    fireEvent.click(screen.getByRole("button", { name: /criar conta/i }))

    expect(onRegister).not.toHaveBeenCalled()
    expect(screen.getByText("Senhas não coincidem")).toBeInTheDocument()
    expect(screen.getByText("Senhas não coincidem. Confira os dois campos e tente novamente.")).toBeInTheDocument()
  })
})
