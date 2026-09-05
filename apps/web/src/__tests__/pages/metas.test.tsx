import { beforeEach, describe, it, expect, vi } from "vitest"
import { fireEvent, render, screen, within } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MetasClient } from "@/app/app/metas/metas-client"
import MetasLoading from "@/app/app/metas/loading"
import type { ReleaseGoal } from "@/components/release/types"
import type { ReactNode } from "react"

const mocks = vi.hoisted(() => ({
  createGoal: vi.fn(),
  updateGoal: vi.fn(),
  deleteGoal: vi.fn(),
}))

const mockGoals: ReleaseGoal[] = [
  {
    id: "1",
    name: "Viagem Europa",
    target: 15000,
    current: 5000,
    deadline: "2026-12-31",
    category: "viagem",
    status: "active",
  },
  {
    id: "2",
    name: "Fundo de Emergência",
    target: 30000,
    current: 30000,
    category: "outro",
    status: "completed",
  },
]

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn(), prefetch: vi.fn(), refresh: vi.fn() }),
}))

vi.mock("@/hooks/use-goals", () => ({
  useCreateGoal: () => ({ mutateAsync: mocks.createGoal, isPending: false }),
  useUpdateGoal: () => ({ mutateAsync: mocks.updateGoal, isPending: false }),
  useDeleteGoal: () => ({ mutateAsync: mocks.deleteGoal, isPending: false }),
}))

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock("@/lib/api-client", () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
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

describe("MetasLoading", () => {
  it("renderiza skeleton loading", () => {
    const { container } = render(<MetasLoading />)
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0)
  })
})

describe("MetasClient", () => {
  beforeEach(() => {
    mocks.createGoal.mockReset()
    mocks.updateGoal.mockReset()
    mocks.deleteGoal.mockReset()
    mocks.createGoal.mockResolvedValue({})
    mocks.updateGoal.mockResolvedValue({})
    mocks.deleteGoal.mockResolvedValue({})
  })

  it("renderiza goal cards com nomes", () => {
    render(
      <MetasClient goals={mockGoals} totalCurrent={35000} totalTarget={45000} globalPercentage={78} />,
      { wrapper: createWrapper() }
    )
    expect(screen.getByText("Viagem Europa")).toBeInTheDocument()
    expect(screen.getByText("Fundo de Emergência")).toBeInTheDocument()
  })

  it("renderiza título da página", () => {
    render(
      <MetasClient goals={mockGoals} totalCurrent={35000} totalTarget={45000} globalPercentage={78} />,
      { wrapper: createWrapper() }
    )
    expect(screen.getByRole("heading", { name: "Metas" })).toBeInTheDocument()
  })

  it("renderiza resumo total e porcentagem global", () => {
    render(
      <MetasClient goals={mockGoals} totalCurrent={35000} totalTarget={45000} globalPercentage={78} />,
      { wrapper: createWrapper() }
    )
    expect(screen.getByText("Total em Metas")).toBeInTheDocument()
    expect(screen.getByText("78%")).toBeInTheDocument()
  })

  it("renderiza valores monetários nos cards", () => {
    render(
      <MetasClient goals={mockGoals} totalCurrent={35000} totalTarget={45000} globalPercentage={78} />,
      { wrapper: createWrapper() }
    )
    expect(screen.getAllByText(/5\.000/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/15\.000/).length).toBeGreaterThanOrEqual(1)
  })

  it("renderiza botão Adicionar Meta no header", () => {
    render(
      <MetasClient goals={mockGoals} totalCurrent={35000} totalTarget={45000} globalPercentage={78} />,
      { wrapper: createWrapper() }
    )
    expect(screen.getByText("Adicionar Meta")).toBeInTheDocument()
    expect(screen.getByLabelText("Abrir menu")).toBeInTheDocument()
  })

  it("abre modal ao clicar em Adicionar Meta", () => {
    render(
      <MetasClient goals={mockGoals} totalCurrent={35000} totalTarget={45000} globalPercentage={78} />,
      { wrapper: createWrapper() }
    )
    fireEvent.click(screen.getByText("Adicionar Meta"))
    expect(screen.getByText("Nova Meta")).toBeInTheDocument()
    expect(screen.getByText(todayFullDate())).toBeInTheDocument()
  })

  it("bloqueia meta com valor alvo zero e não exige categoria", () => {
    render(
      <MetasClient goals={mockGoals} totalCurrent={35000} totalTarget={45000} globalPercentage={78} />,
      { wrapper: createWrapper() }
    )

    fireEvent.click(screen.getByText("Adicionar Meta"))
    fireEvent.change(screen.getByLabelText("Nome da Meta"), { target: { value: "Reserva" } })
    const targetInput = screen.getByLabelText("Valor Alvo")

    fireEvent.blur(targetInput)

    expect(screen.getByText("Informe um valor alvo maior que zero.")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Salvar" })).toBeDisabled()

    fireEvent.change(targetInput, { target: { value: "abc1500,50" } })

    expect(targetInput).toHaveValue("1500,50")
    expect(screen.getByRole("button", { name: "Salvar" })).not.toBeDisabled()
    expect(screen.queryByText("Categoria")).not.toBeInTheDocument()
  })

  it("destaca data atual no calendário de nova meta", () => {
    render(
      <MetasClient goals={mockGoals} totalCurrent={35000} totalTarget={45000} globalPercentage={78} />,
      { wrapper: createWrapper() }
    )

    fireEvent.click(screen.getByText("Adicionar Meta"))
    fireEvent.click(screen.getByLabelText("Prazo"))

    expect(screen.getByRole("button", { name: String(new Date().getDate()) })).toHaveClass("bg-[var(--rls-primary-container)]")
  })

  it("exibe e atualiza status da meta no modal de detalhes", async () => {
    render(
      <MetasClient goals={mockGoals} totalCurrent={35000} totalTarget={45000} globalPercentage={78} />,
      { wrapper: createWrapper() }
    )

    fireEvent.click(screen.getByText("Viagem Europa"))
    expect(screen.getAllByText("Ativa").length).toBeGreaterThan(0)

    fireEvent.click(screen.getByText("Editar"))
    const sheet = screen.getByText("Editar Meta").closest(".rls")!
    fireEvent.click(within(sheet).getByRole("button", { name: /Concluída/ }))
    fireEvent.click(screen.getByRole("button", { name: "Salvar" }))

    await screen.findByText("Meta atualizada com sucesso.")
    expect(mocks.updateGoal).toHaveBeenCalledWith({
      id: 1,
      data: expect.objectContaining({
        status: "completed",
        title: "Viagem Europa",
        target_amount: 15000,
        current_amount: 5000,
        deadline: "2026-12-31T00:00:00",
      }),
    })
  })

  it("usa verde para metas concluídas ou acima de 100% e vermelho para canceladas", () => {
    render(
      <MetasClient
        goals={[
          { ...mockGoals[0], current: 16000, status: "active" },
          { ...mockGoals[1], status: "cancelled" },
        ]}
        totalCurrent={46000}
        totalTarget={45000}
        globalPercentage={102}
      />,
      { wrapper: createWrapper() }
    )

    expect(screen.getByText("107%")).toHaveClass("bg-[var(--rls-secondary-container)]")
    expect(screen.getByText("100%")).toHaveClass("bg-[var(--rls-error-container)]")
  })

  it("renderiza com lista vazia de metas", () => {
    render(
      <MetasClient goals={[]} totalCurrent={0} totalTarget={0} globalPercentage={0} />,
      { wrapper: createWrapper() }
    )
    expect(screen.getByRole("heading", { name: "Metas" })).toBeInTheDocument()
  })
})

function todayFullDate() {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(new Date())
}
