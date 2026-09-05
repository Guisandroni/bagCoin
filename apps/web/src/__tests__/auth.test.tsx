import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { LoginForm } from "@/components/auth/login-form"
import { RegisterForm } from "@/components/auth/register-form"

const mockLogin = vi.fn()
const mockRegister = vi.fn()
const mockLoginWithGoogle = vi.fn()
const mockClearError = vi.fn()
let mockError: string | null = null

vi.mock("@/lib/auth-store", () => ({
  useAuthStore: () => ({
    login: mockLogin,
    register: mockRegister,
    loginWithGoogle: mockLoginWithGoogle,
    verifyEmail: vi.fn(),
    resendVerification: vi.fn(),
    isLoading: false,
    error: mockError,
    clearError: mockClearError,
  }),
}))

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock("@/components/auth/google-button", () => ({
  GoogleButton: ({ onSuccess, isLoading }: { onSuccess: (token: string) => void; isLoading: boolean }) => (
    <button data-testid="google-btn" disabled={isLoading} onClick={() => onSuccess("mock-token")}>
      Google
    </button>
  ),
}))

describe("LoginForm", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockError = null
  })

  it("renders email and password inputs", () => {
    render(<LoginForm />)
    expect(screen.getByLabelText("Email")).toBeInTheDocument()
    expect(screen.getByLabelText("Senha")).toBeInTheDocument()
  })

  it("renders submit button", () => {
    render(<LoginForm />)
    expect(screen.getByRole("button", { name: /entrar/i })).toBeInTheDocument()
  })

  it("shows validation errors on empty submit", async () => {
    render(<LoginForm />)
    const form = screen.getByRole("button", { name: /entrar/i })
    fireEvent.click(form)
    expect(mockLogin).not.toHaveBeenCalled()
  })

  it("calls login on valid submit", async () => {
    mockLogin.mockResolvedValueOnce(undefined)
    render(<LoginForm />)

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "test@email.com" } })
    fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "12345678" } })
    fireEvent.click(screen.getByRole("button", { name: /entrar/i }))

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("test@email.com", "12345678")
    })
  })

  it("displays error message when login fails", () => {
    mockError = "Email ou senha incorretos"
    render(<LoginForm />)
    expect(screen.getByText("Email ou senha incorretos")).toBeInTheDocument()
  })
})

describe("RegisterForm", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockError = null
  })

  it("renders name, email, phone and password inputs", () => {
    render(<RegisterForm />)
    expect(screen.getByLabelText("Nome")).toBeInTheDocument()
    expect(screen.getByLabelText("Email")).toBeInTheDocument()
    expect(screen.getByLabelText(/telefone/i)).toBeInTheDocument()
    expect(screen.getByLabelText("Senha")).toBeInTheDocument()
  })

  it("renders register button", () => {
    render(<RegisterForm />)
    expect(screen.getByRole("button", { name: /criar conta/i })).toBeInTheDocument()
  })
})
