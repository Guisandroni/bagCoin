import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { RelatoriosClient, buildReportAnalytics } from "@/app/app/relatorios/relatorios-client"
import RelatoriosLoading from "@/app/app/relatorios/loading"
import type { ServerTransaction, TransactionSummary } from "@/lib/api-server"

const mockToggleDrawer = vi.fn()

const summary: TransactionSummary = {
  balance: 2500,
  total_income: 6500,
  total_expenses: 4000,
  transaction_count: 3,
  categories: [
    { name: "Alimentação", amount: 900, color: "#ff9500" },
    { name: "Transporte", amount: 300, color: "#1652f0" },
  ],
  recent_transactions: [],
}

const transactions: ServerTransaction[] = [
  {
    id: "1",
    type: "EXPENSE",
    name: "Supermercado",
    category: "Alimentação",
    amount: 900,
    date: "09 mai",
    transaction_date: "2026-05-09",
    source: "manual",
    status: "confirmed",
  },
  {
    id: "2",
    type: "EXPENSE",
    name: "Uber",
    category: "Transporte",
    amount: 300,
    date: "02 mai",
    transaction_date: "2026-05-02",
    source: "manual",
    status: "confirmed",
  },
  {
    id: "3",
    type: "INCOME",
    name: "Salário",
    category: "Salário",
    amount: 6500,
    date: "01 mai",
    transaction_date: "2026-05-01",
    source: "manual",
    status: "confirmed",
  },
]

vi.mock("@/lib/store", () => ({
  useAppStore: (selector?: (state: { toggleDrawer: typeof mockToggleDrawer }) => unknown) => {
    const state = { toggleDrawer: mockToggleDrawer }
    return selector ? selector(state) : state
  },
}))

vi.mock("@/hooks/use-reports", () => ({
  useReports: () => ({ data: { items: [] }, isLoading: false }),
  useCreateReport: () => ({ mutate: vi.fn(), isPending: false }),
  useDownloadReport: () => ({ mutate: vi.fn(), isPending: false }),
}))

vi.mock("@/hooks/use-transactions", () => ({
  useExportTransactionsCsv: () => ({ mutate: vi.fn(), isPending: false }),
}))

describe("RelatoriosLoading", () => {
  it("renderiza skeleton loading", () => {
    const { container } = render(<RelatoriosLoading />)
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0)
  })
})

describe("RelatoriosClient", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renderiza relatórios gráficos sem PDF e sem navbar", () => {
    const { container } = render(<RelatoriosClient summary={summary} transactions={transactions} />)

    expect(screen.getByText("Relatórios")).toBeInTheDocument()
    expect(screen.getByText("Maiores gastos por categoria")).toBeInTheDocument()
    expect(screen.getByText("Gastos por mês")).toBeInTheDocument()
    expect(screen.getByText("Gastos por semana")).toBeInTheDocument()
    expect(screen.getByText("Gastos por dia")).toBeInTheDocument()
    expect(screen.queryByText("Download PDF")).not.toBeInTheDocument()
    expect(container.querySelector("nav")).not.toBeInTheDocument()
  })

  it("alterna drawer pelo header sem botão de início", () => {
    render(<RelatoriosClient summary={summary} transactions={transactions} />)

    fireEvent.click(screen.getByLabelText("Abrir menu"))
    expect(mockToggleDrawer).toHaveBeenCalled()
    expect(screen.queryByLabelText("Início")).not.toBeInTheDocument()
  })

  it("agrega gastos por período usando apenas despesas", () => {
    const analytics = buildReportAnalytics(summary, transactions.map((tx) => ({
      id: tx.id,
      name: tx.name,
      category: tx.category ?? "",
      categoryIcon: "",
      amount: tx.amount,
      date: tx.date ?? "",
      transactionDate: tx.transaction_date,
      type: tx.type === "INCOME" ? "receita" : "despesa",
    })))

    expect(analytics.categoryExpenses[0]).toMatchObject({ name: "Alimentação", amount: 900 })
    expect(analytics.monthlyExpenses[0]).toMatchObject({ label: "maio de 2026", amount: 1200 })
    expect(analytics.dailyExpenses[0]).toMatchObject({ amount: 900 })
  })
})
