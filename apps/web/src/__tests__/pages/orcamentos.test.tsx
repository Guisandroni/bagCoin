import { beforeEach, describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { OrcamentosClient } from "@/app/app/orcamentos/orcamentos-client"
import OrcamentosLoading from "@/app/app/orcamentos/loading"
import type { ReleaseBudget } from "@/components/release/types"
import type { ReactNode } from "react"

const mocks = vi.hoisted(() => ({
  createBudget: vi.fn(),
  updateBudget: vi.fn(),
}))

const mockBudgets: ReleaseBudget[] = [
  {
    id: "1",
    category: "Alimentação",
    categoryIcon: "utensils",
    categoryColor: "#22c55e",
    spent: 250,
    total: 1000,
    remaining: 750,
    percentage: 25,
    budgetDate: "2026-03-23",
  },
  {
    id: "2",
    category: "Lazer",
    categoryIcon: "gamepad-2",
    categoryColor: "#8b5cf6",
    spent: 100,
    total: 500,
    remaining: 400,
    percentage: 20,
    budgetDate: "2026-03-23",
  },
  {
    id: "3",
    category: "Moradia",
    categoryIcon: "home",
    categoryColor: "#45B7D1",
    spent: 1200,
    total: 1000,
    remaining: -200,
    percentage: 120,
    budgetDate: "2026-03-23",
  },
]

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn(), prefetch: vi.fn(), refresh: vi.fn() }),
}))

vi.mock("@/hooks/use-budgets", () => ({
  useCreateBudget: () => ({ mutateAsync: mocks.createBudget, isPending: false }),
  useUpdateBudget: () => ({ mutateAsync: mocks.updateBudget, isPending: false }),
  useDeleteBudget: () => ({ mutateAsync: vi.fn(), isPending: false }),
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

describe("OrcamentosLoading", () => {
  it("renderiza skeleton loading", () => {
    const { container } = render(<OrcamentosLoading />)
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0)
  })
})

describe("OrcamentosClient", () => {
  beforeEach(() => {
    mocks.createBudget.mockReset()
    mocks.updateBudget.mockReset()
    mocks.createBudget.mockResolvedValue({})
    mocks.updateBudget.mockResolvedValue({})
  })

  it("renderiza budget cards com nomes de categoria", () => {
    render(<OrcamentosClient budgets={mockBudgets} totalSpent={350} totalBudget={1500} />, { wrapper: createWrapper() })
    expect(screen.getByText("Alimentação")).toBeInTheDocument()
    expect(screen.getByText("Lazer")).toBeInTheDocument()
    expect(screen.getAllByText("23/março").length).toBeGreaterThan(0)
    expect(screen.getAllByText("mensal").length).toBeGreaterThan(0)
  })

  it("exibe orçamento acima do limite sem valor negativo", () => {
    render(<OrcamentosClient budgets={mockBudgets} totalSpent={1550} totalBudget={2500} />, { wrapper: createWrapper() })
    expect(screen.getByText("R$ 200,00 acima do limite")).toBeInTheDocument()
    expect(screen.queryByText("-R$ 200,00 restantes")).not.toBeInTheDocument()
  })

  it("renderiza título da página", () => {
    render(<OrcamentosClient budgets={mockBudgets} totalSpent={350} totalBudget={1500} />, { wrapper: createWrapper() })
    expect(screen.getByRole("heading", { name: "Orçamentos" })).toBeInTheDocument()
  })

  it("exibe valores de gasto e total", () => {
    render(<OrcamentosClient budgets={mockBudgets} totalSpent={350} totalBudget={1500} />, { wrapper: createWrapper() })
    expect(screen.getByText(/R\$\s*350/)).toBeInTheDocument()
  })

  it("renderiza botão Adicionar Orçamento no header", () => {
    render(<OrcamentosClient budgets={mockBudgets} totalSpent={350} totalBudget={1500} />, { wrapper: createWrapper() })
    expect(screen.getByText("Adicionar Orçamento")).toBeInTheDocument()
    expect(screen.getByLabelText("Abrir menu")).toBeInTheDocument()
  })

  it("abre modal ao clicar em Adicionar Orçamento", () => {
    render(<OrcamentosClient budgets={mockBudgets} totalSpent={350} totalBudget={1500} />, { wrapper: createWrapper() })
    fireEvent.click(screen.getByText("Adicionar Orçamento"))
    expect(screen.getByText("Novo Orçamento")).toBeInTheDocument()
    expect(screen.getByText("Orçamento mensal.")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Mensal" })).not.toBeInTheDocument()
  })

  it("envia orçamento mensal com categoria recolhível e data atual", async () => {
    render(
      <OrcamentosClient
        budgets={mockBudgets}
        categories={[
          { id: 1, name: "Alimentação", icon: "🍽️", color: "#FF6B6B", allocated: 0, type: "despesa", isFixed: true },
          { id: 2, name: "Viagem", icon: "✈️", color: "#3498DB", allocated: 0, type: "despesa", isFixed: false },
        ]}
        totalSpent={350}
        totalBudget={1500}
      />,
      { wrapper: createWrapper() }
    )

    fireEvent.click(screen.getByText("Adicionar Orçamento"))
    const modal = screen.getByText("Novo Orçamento").closest("form")!
    expect(within(modal).queryByRole("button", { name: /Viagem/ })).not.toBeInTheDocument()
    fireEvent.click(within(modal).getByText("Ver categorias"))
    expect(within(modal).getByText("Ocultar categorias")).toBeInTheDocument()
    fireEvent.click(within(modal).getByText("Ocultar categorias"))
    expect(within(modal).queryByRole("button", { name: /Viagem/ })).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText("Pesquisar categorias"), {
      target: { value: "via" },
    })
    expect(within(modal).getByText("Ocultar categorias")).toBeInTheDocument()
    fireEvent.click(within(modal).getByRole("button", { name: /Viagem/ }))
    fireEvent.change(screen.getByLabelText("Limite mensal"), {
      target: { value: "750,00" },
    })
    fireEvent.click(within(modal).getByLabelText("Data"))
    expect(screen.getByRole("button", { name: String(new Date().getDate()) })).toHaveClass("bg-[var(--rls-primary-container)]")
    fireEvent.click(screen.getByLabelText("Fechar calendário"))
    fireEvent.click(within(modal).getByRole("button", { name: "Salvar" }))

    await waitFor(() => {
      expect(mocks.createBudget).toHaveBeenCalledWith(expect.objectContaining({
        name: "Viagem",
        category_id: 2,
        category_name: "Viagem",
        period: "monthly",
        total_limit: 750,
        budget_type: "category",
      }))
      expect(mocks.createBudget.mock.calls[0][0].budget_date).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    })
  })

  it("não permite criar orçamento digitando categoria inexistente", () => {
    render(
      <OrcamentosClient
        budgets={mockBudgets}
        categories={[
          { id: 1, name: "Alimentação", icon: "🍽️", color: "#FF6B6B", allocated: 0, type: "despesa", isFixed: true },
        ]}
        totalSpent={350}
        totalBudget={1500}
      />,
      { wrapper: createWrapper() }
    )

    fireEvent.click(screen.getByText("Adicionar Orçamento"))
    fireEvent.change(screen.getByLabelText("Pesquisar categorias"), {
      target: { value: "Categoria Nova" },
    })
    fireEvent.change(screen.getByLabelText("Limite mensal"), {
      target: { value: "500,00" },
    })

    expect(screen.getByRole("button", { name: "Salvar" })).toBeDisabled()
    expect(screen.getByText("Nenhuma categoria encontrada.")).toBeInTheDocument()
  })

  it("edita orçamento com categoria recolhível, mensal fixo e data", async () => {
    render(
      <OrcamentosClient
        budgets={mockBudgets}
        categories={[
          { id: 1, name: "Alimentação", icon: "🍽️", color: "#FF6B6B", allocated: 0, type: "despesa", isFixed: true },
          { id: 2, name: "Viagem", icon: "✈️", color: "#3498DB", allocated: 0, type: "despesa", isFixed: false },
        ]}
        totalSpent={350}
        totalBudget={1500}
      />,
      { wrapper: createWrapper() }
    )

    fireEvent.click(screen.getByText("Alimentação"))
    fireEvent.click(screen.getByText("Editar"))

    expect(screen.getByText("Editar Orçamento")).toBeInTheDocument()
    expect(screen.getByText("Orçamento mensal.")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Mensal" })).not.toBeInTheDocument()
    expect(screen.getByText("23 de março de 2026")).toBeInTheDocument()

    const sheet = screen.getByText("Editar Orçamento").closest(".rls")!
    expect(within(sheet).queryByRole("button", { name: /Viagem/ })).not.toBeInTheDocument()
    fireEvent.click(within(sheet).getByText("Ver categorias"))
    fireEvent.click(within(sheet).getByRole("button", { name: /Viagem/ }))
    fireEvent.change(within(sheet).getByLabelText("Limite"), { target: { value: "800,00" } })
    fireEvent.click(within(sheet).getByRole("button", { name: "Salvar" }))

    await waitFor(() => {
      expect(mocks.updateBudget).toHaveBeenCalledWith({
        id: 1,
        data: expect.objectContaining({
          category_id: 2,
          category_name: "Viagem",
          period: "monthly",
          budget_date: "2026-03-23",
          total_limit: 800,
          budget_type: "category",
        }),
      })
    })
  })

  it("renderiza com lista vazia de orçamentos", () => {
    render(<OrcamentosClient budgets={[]} totalSpent={0} totalBudget={0} />, { wrapper: createWrapper() })
    expect(screen.getByRole("heading", { name: "Orçamentos" })).toBeInTheDocument()
  })
})
