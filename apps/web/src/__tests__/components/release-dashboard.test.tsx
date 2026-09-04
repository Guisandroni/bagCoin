import { beforeEach, describe, it, expect, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import { DashboardView } from "@/components/release/dashboard-view"
import type { ReleaseDashboardSummary, ReleaseNavItem } from "@/components/release/types"

const mockToggleDrawer = vi.fn()

vi.mock("@/lib/store", () => ({
  useAppStore: (selector?: (state: { toggleDrawer: typeof mockToggleDrawer }) => unknown) => {
    const state = { toggleDrawer: mockToggleDrawer }
    return selector ? selector(state) : state
  },
}))

const summary: ReleaseDashboardSummary = {
  totalBalance: 9569.3,
  income: 11500,
  expenses: 1930.7,
  recentTransactions: [],
  categoryBreakdown: [
    { name: "Moradia", percentage: 62, amount: 1200, color: "#7B1FA2", emoji: "🏠" },
    { name: "Alimentação", percentage: 38, amount: 730.7, color: "#FF6D00", emoji: "🍽️" },
  ],
  goals: [
    { name: "Reserva", current: 4200, target: 5000, percentage: 84 },
  ],
  budgets: [
    { name: "Alimentação", spent: 450, total: 1200, remaining: 750, percentage: 38 },
  ],
}

const navItems: ReleaseNavItem[] = [
  { label: "Início", icon: "home", href: "/app", isActive: true },
  { label: "Categorias", icon: "categorias", href: "/app/categorias" },
]

describe("DashboardView", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders updated balance, category and goals/budgets sections", () => {
    const { container } = render(
      <DashboardView
        summary={summary}
        navItems={navItems}
        onNavigate={() => {}}
      />
    )

    expect(screen.getByText("Dashboard")).toBeInTheDocument()
    expect(screen.queryByText("Centro Financeiro")).not.toBeInTheDocument()
    expect(screen.getByText("Saldo Disponível")).toBeInTheDocument()
    expect(screen.getByText("Distribuição das despesas")).toBeInTheDocument()
    expect(screen.getByText("62%")).toBeInTheDocument()
    expect(screen.getByText("R$ 1.200,00")).toBeInTheDocument()
    expect(screen.getByText("🏠")).toBeInTheDocument()
    expect(screen.getByText("Metas")).toBeInTheDocument()
    expect(screen.getByText("Orçamentos")).toBeInTheDocument()
    expect(screen.getByText("Reserva")).toBeInTheDocument()
    expect(screen.getAllByText("Alimentação")).toHaveLength(2)
    expect(container.querySelector("svg circle[style*='color']")).toHaveStyle({ color: "#7B1FA2" })
    expect(container.querySelector("svg circle[style*='color']")?.getAttribute("stroke-dasharray")).toBe("59, 41")
    expect(container.querySelector("span[style*='background-color']")).not.toBeInTheDocument()
  })

  it("calls the category navigation action from the Ver mais button", () => {
    const onViewAllCategories = vi.fn()

    render(
      <DashboardView
        summary={summary}
        navItems={navItems}
        onNavigate={() => {}}
        onViewAllCategories={onViewAllCategories}
      />
    )

    fireEvent.click(screen.getByText("Ver mais"))

    expect(onViewAllCategories).toHaveBeenCalledTimes(1)
  })

  it("renders zero available balance when dashboard summary is floored", () => {
    render(
      <DashboardView
        summary={{ ...summary, totalBalance: 0, income: 0, expenses: 4884.9 }}
        navItems={navItems}
        onNavigate={() => {}}
      />
    )

    expect(screen.getByText("Saldo Disponível")).toBeInTheDocument()
    expect(screen.getAllByText("R$ 0,00").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("R$ 4.884,90").length).toBeGreaterThanOrEqual(1)
  })

  it("usa ícone de menu no header para abrir o drawer", () => {
    const { container } = render(
      <DashboardView
        summary={summary}
        navItems={navItems}
        onNavigate={() => {}}
      />
    )

    fireEvent.click(screen.getByLabelText("Abrir menu"))

    expect(mockToggleDrawer).toHaveBeenCalledTimes(1)
    expect(container.querySelector("header")).toHaveClass("border-b")
    expect(screen.getByRole("heading", { name: "Dashboard" })).toHaveClass("text-[22px]")
    expect(screen.getByRole("heading", { name: "Dashboard" })).not.toHaveClass("text-2xl")
  })

  it("trunca nomes longos em transações recentes sem quebrar o valor", () => {
    render(
      <DashboardView
        summary={{
          ...summary,
          recentTransactions: [
            {
              id: "tx-long",
              name: "Distribuição das despesas do mês com descrição muito grande",
              category: "Outros",
              amount: 1930.7,
              date: "25 mai",
              type: "despesa",
            },
          ],
        }}
        navItems={navItems}
        onNavigate={() => {}}
      />
    )

    expect(screen.getByText("Distribuição das despesas do mês com descrição muito grande")).toHaveClass("truncate")
    expect(screen.getByText("-R$ 1.930,70")).toHaveClass("whitespace-nowrap")
    expect(screen.getByText("-R$ 1.930,70")).toHaveClass("shrink-0")
  })
})
