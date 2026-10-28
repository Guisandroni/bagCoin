import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent, within, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn(), prefetch: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/app/transacoes",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}))

import { TransacoesClient } from "@/app/app/transacoes/transacoes-client"
import TransacoesLoading from "@/app/app/transacoes/loading"
import { TransactionsView } from "@/components/release/transactions-view"
import { api } from "@/lib/api-client"
import type { ReactNode } from "react"
import type { ReleaseCategory, ReleaseTransaction } from "@/components/release/types"

const mockItems: ReleaseTransaction[] = [
  {
    id: "1",
    name: "Supermercado",
    category: "Alimentação",
    categoryIcon: "shopping-cart",
    amount: 287.5,
    date: "30 abr",
    transactionDate: "2026-04-30",
    type: "despesa",
    source: "manual",
  },
  {
    id: "2",
    name: "Salário",
    category: "Salário",
    categoryIcon: "banknote",
    amount: 8500,
    date: "09 mai",
    transactionDate: "2026-05-09",
    type: "receita",
    source: "auto",
  },
  {
    id: "3",
    name: "Uber",
    category: "Transporte",
    categoryIcon: "car",
    amount: 35,
    date: "06 mai",
    transactionDate: "2026-05-06",
    type: "despesa",
    source: "manual",
  },
]

const mockCategories: ReleaseCategory[] = [
  {
    id: 1,
    name: "Alimentação",
    icon: "🍽️",
    color: "#ff9800",
    allocated: 0,
    type: "despesa",
  },
  {
    id: 2,
    name: "Transporte",
    icon: "🚗",
    color: "#4285f4",
    allocated: 0,
    type: "despesa",
  },
  {
    id: 3,
    name: "Salário",
    icon: "💰",
    color: "#22c55e",
    allocated: 0,
    type: "receita",
  },
]

function expectCurrencyVisible(value: string) {
  expect(
    screen.getAllByText((content) => content.replace(/\u00a0/g, " ") === value).length
  ).toBeGreaterThan(0)
}

function todayIso() {
  const today = new Date()
  const year = today.getFullYear()
  const month = String(today.getMonth() + 1).padStart(2, "0")
  const day = String(today.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

function todayFullDate() {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(new Date())
}

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), dismiss: vi.fn() },
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

describe("TransacoesLoading", () => {
  it("renderiza skeleton loading", () => {
    const { container } = render(<TransacoesLoading />)
    const skeletons = container.querySelectorAll(".animate-pulse")
    expect(skeletons.length).toBeGreaterThanOrEqual(5)
  })
})

describe("TransacoesClient", () => {
  it("renderiza lista de transações com dados", () => {
    render(<TransacoesClient transactions={mockItems} />, { wrapper: createWrapper() })
    expect(screen.getAllByText("Supermercado").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Salário").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Uber").length).toBeGreaterThanOrEqual(1)
  })

  it("mostra categorias corretas na lista", () => {
    render(<TransacoesClient transactions={mockItems} />, { wrapper: createWrapper() })
    expect(screen.getByText(/Alimentação/)).toBeInTheDocument()
    expect(screen.getByText(/Transporte/)).toBeInTheDocument()
  })

  it("busca por texto altera o estado do filtro", () => {
    render(<TransacoesClient transactions={mockItems} />, { wrapper: createWrapper() })
    const searchInput = screen.getByPlaceholderText("Buscar transações...")
    fireEvent.change(searchInput, { target: { value: "Super" } })
    expect((searchInput as HTMLInputElement).value).toBe("Super")
  })

  it("abre modal ao clicar em Adicionar Transação", () => {
    render(<TransacoesClient transactions={mockItems} />, { wrapper: createWrapper() })
    fireEvent.click(screen.getByText("Adicionar Transação"))
    expect(screen.getByText("Nova Transação")).toBeInTheDocument()
    expect(screen.getByLabelText("Abrir menu")).toBeInTheDocument()
    expect(screen.getByText(todayFullDate())).toBeInTheDocument()
  })

  it("cria transação com categoria existente e recorrência", async () => {
    vi.mocked(api.post).mockResolvedValueOnce({})
    render(<TransacoesClient transactions={mockItems} categories={mockCategories} />, { wrapper: createWrapper() })

    fireEvent.click(screen.getByText("Adicionar Transação"))
    const modal = screen.getByText("Nova Transação").closest("form")!
    expect(within(modal).queryByRole("button", { name: /Alimentação/ })).not.toBeInTheDocument()
    fireEvent.click(within(modal).getByText("Ver categorias"))
    expect(within(modal).getByText("Ocultar categorias")).toBeInTheDocument()
    fireEvent.click(within(modal).getByText("Ocultar categorias"))
    expect(within(modal).queryByRole("button", { name: /Alimentação/ })).not.toBeInTheDocument()
    fireEvent.change(within(modal).getByLabelText("Pesquisar categorias"), { target: { value: "ali" } })
    expect(within(modal).getByText("Ocultar categorias")).toBeInTheDocument()
    fireEvent.change(within(modal).getByLabelText("Descrição"), { target: { value: "Mercado" } })
    fireEvent.click(within(modal).getByRole("button", { name: /Alimentação/ }))
    expect(within(modal).getByLabelText("Pesquisar categorias")).toHaveValue("Alimentação")
    expect(within(modal).queryByText("Ocultar categorias")).not.toBeInTheDocument()
    expect(within(modal).getByText("Ver categorias")).toBeInTheDocument()
    fireEvent.change(within(modal).getByLabelText("Valor"), { target: { value: "55,00" } })
    fireEvent.click(within(modal).getByLabelText("Transação recorrente"))
    expect(within(modal).getByText("Será repetida mensalmente.")).toBeInTheDocument()
    expect(within(modal).queryByText("Semanal")).not.toBeInTheDocument()
    fireEvent.click(within(modal).getByLabelText("Data"))
    expect(screen.getByRole("button", { name: String(new Date().getDate()) })).toHaveClass("bg-[var(--rls-primary-container)]")
    fireEvent.click(screen.getByLabelText("Fechar calendário"))
    fireEvent.click(within(modal).getByRole("button", { name: "Salvar" }))

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/bagcoin/transactions", expect.objectContaining({
        category_id: 1,
        category_name: "Alimentação",
        transaction_date: todayIso(),
        is_recurring: true,
        recurrence_frequency: "monthly",
      }))
    })
  })

  it("filtra transações localmente pelo nome ignorando acentos", () => {
    render(<TransacoesClient transactions={mockItems} />, { wrapper: createWrapper() })
    fireEvent.change(screen.getByPlaceholderText("Buscar transações..."), { target: { value: "salario" } })

    expect(screen.getAllByText("Salário").length).toBeGreaterThanOrEqual(1)
    expect(screen.queryByText("Supermercado")).not.toBeInTheDocument()
    expect(screen.queryByText("Uber")).not.toBeInTheDocument()
  })

  it("filtra transações localmente pela categoria", () => {
    render(<TransacoesClient transactions={mockItems} />, { wrapper: createWrapper() })
    fireEvent.change(screen.getByPlaceholderText("Buscar transações..."), { target: { value: "transporte" } })

    expect(screen.getByText("Uber")).toBeInTheDocument()
    expect(screen.queryByText("Supermercado")).not.toBeInTheDocument()
    expect(screen.queryByText("Salário")).not.toBeInTheDocument()
  })

  it("abre o modal de detalhes ao clicar em uma transação", () => {
    render(<TransacoesClient transactions={mockItems} />, { wrapper: createWrapper() })

    fireEvent.click(screen.getByText("Uber"))

    expect(screen.getByText("Detalhes da transação")).toBeInTheDocument()
    expect(screen.getAllByText("Transporte").length).toBeGreaterThanOrEqual(1)
  })

  it("confirma exclusão e mostra toast release de sucesso", async () => {
    vi.mocked(api.delete).mockResolvedValueOnce(undefined)
    render(<TransacoesClient transactions={mockItems} />, { wrapper: createWrapper() })

    fireEvent.click(screen.getByText("Uber"))
    fireEvent.click(screen.getByText("Excluir"))
    fireEvent.click(screen.getAllByRole("button", { name: "Excluir" }).at(-1)!)

    expect(await screen.findByText("Transação excluída com sucesso.")).toBeInTheDocument()
    expect(api.delete).toHaveBeenCalledWith("/bagcoin/transactions/3")
  })

  it("mantém modal aberto e mostra toast release em erro de exclusão", async () => {
    vi.mocked(api.delete).mockRejectedValueOnce(new Error("falha"))
    render(<TransacoesClient transactions={mockItems} />, { wrapper: createWrapper() })

    fireEvent.click(screen.getByText("Uber"))
    fireEvent.click(screen.getByText("Excluir"))
    fireEvent.click(screen.getAllByRole("button", { name: "Excluir" }).at(-1)!)

    expect(await screen.findByText("Erro ao excluir transação. Tente novamente.")).toBeInTheDocument()
    expect(screen.getByText("Excluir transação?")).toBeInTheDocument()
  })
})

describe("TransactionsView", () => {
  const navItems = [{ label: "Início", icon: "home", href: "/app" }]

  it("usa filtros por semana, mês e calendário com transactionDate", () => {
    const { container } = render(
      <TransactionsView
        transactions={mockItems}
        totalSpent={322.5}
        totalReceived={8500}
        navItems={navItems}
        onNavigate={() => {}}
        currentDate={new Date(2026, 4, 9)}
      />
    )

    expect(container.querySelector(".rls")).not.toHaveClass("pb-28")

    expect(screen.queryByText("Por dia")).not.toBeInTheDocument()
    expect(screen.getByText("Total Despesas")).toBeInTheDocument()
    expect(screen.getByText("Total Receitas")).toBeInTheDocument()
    expectCurrencyVisible("R$ 322,50")
    expectCurrencyVisible("R$ 8.500,00")

    fireEvent.click(screen.getByText("Por semana"))
    expect(screen.getAllByText("Salário").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("Uber")).toBeInTheDocument()
    expect(screen.queryByText("Supermercado")).not.toBeInTheDocument()
    expectCurrencyVisible("R$ 35,00")
    expectCurrencyVisible("R$ 8.500,00")

    fireEvent.click(screen.getByText("Por mês"))
    expect(screen.getAllByText("Salário").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("Uber")).toBeInTheDocument()
    expect(screen.queryByText("Supermercado")).not.toBeInTheDocument()
    expect(screen.getByText("maio de 2026")).toBeInTheDocument()
    expect(screen.queryByText("abril de 2026")).not.toBeInTheDocument()

    fireEvent.click(screen.getByText("Calendário"))
    expect(screen.getByLabelText("Selecionar mês")).toHaveValue("4")
    expect(screen.getByLabelText("Selecionar ano")).toHaveValue("2026")
    expect(screen.getByRole("button", { name: "9" })).toHaveClass("bg-[var(--rls-primary-container)]")
    expect(screen.getAllByText("Salário").length).toBeGreaterThanOrEqual(1)
    expect(screen.queryByText("Uber")).not.toBeInTheDocument()
    expectCurrencyVisible("R$ 0,00")
    expectCurrencyVisible("R$ 8.500,00")

    fireEvent.click(screen.getByRole("button", { name: "6" }))
    expect(screen.getByText("Uber")).toBeInTheDocument()
    expect(screen.queryByText("Salário")).not.toBeInTheDocument()
    expect(screen.queryByText("Supermercado")).not.toBeInTheDocument()
    expectCurrencyVisible("R$ 35,00")
    expectCurrencyVisible("R$ 0,00")
  })

  it("filtra transações por tipo de receita e despesa", () => {
    render(
      <TransactionsView
        transactions={mockItems}
        totalSpent={322.5}
        totalReceived={8500}
        navItems={navItems}
        onNavigate={() => {}}
        currentDate={new Date(2026, 4, 9)}
      />
    )

    fireEvent.click(screen.getByText("Despesas"))
    expect(screen.getByText("Supermercado")).toBeInTheDocument()
    expect(screen.getByText("Uber")).toBeInTheDocument()
    expect(screen.queryByText("Salário")).not.toBeInTheDocument()

    fireEvent.click(screen.getByText("Receitas"))
    expect(screen.getAllByText("Salário").length).toBeGreaterThanOrEqual(1)
    expect(screen.queryByText("Supermercado")).not.toBeInTheDocument()
    expect(screen.queryByText("Uber")).not.toBeInTheDocument()
  })

  it("combina filtro de tipo com busca e período", () => {
    render(
      <TransactionsView
        transactions={mockItems}
        totalSpent={322.5}
        totalReceived={8500}
        navItems={navItems}
        onNavigate={() => {}}
        currentDate={new Date(2026, 4, 9)}
      />
    )

    fireEvent.click(screen.getByText("Por mês"))
    fireEvent.click(screen.getByText("Despesas"))
    fireEvent.change(screen.getByPlaceholderText("Buscar transações..."), { target: { value: "salario" } })

    expect(screen.getByText("Nenhuma transação encontrada")).toBeInTheDocument()
    expectCurrencyVisible("R$ 0,00")
  })

  it("aciona seleção ao clicar na linha da transação", () => {
    const onSelectTransaction = vi.fn()
    render(
      <TransactionsView
        transactions={mockItems}
        totalSpent={322.5}
        totalReceived={8500}
        navItems={navItems}
        onNavigate={() => {}}
        onSelectTransaction={onSelectTransaction}
      />
    )

    fireEvent.click(within(screen.getByText("Supermercado").closest("button")!).getByText("Supermercado"))

    expect(onSelectTransaction).toHaveBeenCalledWith(expect.objectContaining({ id: "1" }))
  })
})
