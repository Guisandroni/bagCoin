import { http, HttpResponse } from "msw"
import { setupServer } from "msw/node"

const API = "http://localhost:8000/api/v1"

// ----------------- ACCOUNTS -----------------
export const mockAccounts = [
  { id: 1, name: "NuBank", type: "CHECKING", balance: 5200, bank: "NuBank", color: "#7c3aed", created_at: "2026-04-01T00:00:00Z" },
  { id: 2, name: "Poupança", type: "SAVINGS", balance: 12000, bank: "Bradesco", color: "#0052ff", created_at: "2026-04-01T00:00:00Z" },
]

// ----------------- BUDGETS -----------------
export const mockBudgets = {
  items: [
    { id: 1, name: "Mercado Mensal", period: "monthly", total_limit: 1000, total_spent: 250, total_remaining: 750, percentage: 25, budget_type: "general", category_id: 1, category_name: "Alimentação", created_at: "2026-04-01T00:00:00Z", updated_at: null },
    { id: 2, name: "Lazer", period: "monthly", total_limit: 500, total_spent: 100, total_remaining: 400, percentage: 20, budget_type: "general", category_id: null, category_name: null, created_at: "2026-04-01T00:00:00Z", updated_at: null },
  ],
  total: 2,
}

export const mockBudgetSingle = {
  id: 1, name: "Mercado Mensal", period: "monthly", total_limit: 1000, total_spent: 250, total_remaining: 750, percentage: 25, budget_type: "general", category_id: 1, category_name: "Alimentação", created_at: "2026-04-01T00:00:00Z", updated_at: null,
}

// ----------------- TRANSACTIONS -----------------
export const mockTransactions = {
  items: [
    { id: "1", type: "EXPENSE", name: "Supermercado", category: "Alimentação", amount: 287.5, date: "30 Abr", source: "manual", status: "confirmed", created_at: "2026-04-30T00:00:00Z", updated_at: null },
    { id: "2", type: "INCOME", name: "Salário", category: "Salário", amount: 8500, date: "28 Abr", source: "auto", status: "confirmed", created_at: "2026-04-28T00:00:00Z", updated_at: null },
    { id: "3", type: "EXPENSE", name: "Uber", category: "Transporte", amount: 35, date: "29 Abr", source: "manual", status: "pending", created_at: "2026-04-29T00:00:00Z", updated_at: null },
  ],
  total: 3,
}

export const mockSummary = {
  balance: 8177.5,
  total_income: 8500,
  total_expenses: 322.5,
  transaction_count: 3,
  categories: [
    { name: "Alimentação", amount: 287.5, color: "#ff6b35" },
    { name: "Transporte", amount: 35, color: "#0052ff" },
  ],
  recent_transactions: mockTransactions.items,
}

// ----------------- GOALS -----------------
export const mockGoals = {
  items: [
    { id: 1, title: "Viagem Europa", target_amount: 15000, current_amount: 5000, deadline: "2026-12-31T00:00:00Z", status: "active", created_at: "2026-01-01T00:00:00Z", updated_at: null },
    { id: 2, title: "Fundo de Emergência", target_amount: 30000, current_amount: 30000, deadline: null, status: "completed", created_at: "2026-01-01T00:00:00Z", updated_at: null },
  ],
  total: 2,
}

// ----------------- CREDIT CARDS -----------------
export const mockCreditCards = [
  { id: 1, name: "Nubank", limit: 5000, closing_day: 3, due_day: 10, issuer: "Mastercard", color: "#7c3aed", created_at: "2026-04-01T00:00:00Z" },
  { id: 2, name: "Inter", limit: 8000, closing_day: 15, due_day: 22, issuer: "Visa", color: "#ff6b35", created_at: "2026-04-01T00:00:00Z" },
]

// ----------------- REPORTS -----------------
export const mockReports = {
  items: [
    { id: 1, user_uuid: null, period_start: "2026-04-01T00:00:00Z", period_end: "2026-04-30T00:00:00Z", file_url: "https://example.com/report.pdf", created_at: "2026-05-01T00:00:00Z", updated_at: "2026-05-01T00:00:00Z" },
    { id: 2, user_uuid: null, period_start: "2026-03-01T00:00:00Z", period_end: "2026-03-31T00:00:00Z", file_url: null, created_at: "2026-04-01T00:00:00Z", updated_at: "2026-04-01T00:00:00Z" },
  ],
  total: 2,
}

// ----------------- CONVERSATIONS -----------------
export const mockConversations = {
  items: [
    { id: "conv-1", title: "Gastei 50 no mercado", user_id: "user-1", is_archived: false, created_at: "2026-05-01T00:00:00Z", updated_at: "2026-05-01T00:00:00Z" },
    { id: "conv-2", title: "Quanto gastei esse mês?", user_id: "user-1", is_archived: false, created_at: "2026-04-30T00:00:00Z", updated_at: "2026-04-30T00:00:00Z" },
  ],
  total: 2,
}

export const mockConversationDetail = {
  ...mockConversations.items[0],
  messages: [
    { id: "msg-1", conversation_id: "conv-1", role: "user", content: "Gastei 50 no mercado", created_at: "2026-05-01T00:00:00Z", updated_at: "2026-05-01T00:00:00Z" },
    { id: "msg-2", conversation_id: "conv-1", role: "assistant", content: "Registrei uma despesa de R$ 50 em Alimentação.", created_at: "2026-05-01T00:00:00Z", updated_at: "2026-05-01T00:00:00Z" },
  ],
}

// ----------------- MSW HANDLERS -----------------

export const handlers = [
  http.get(`${API}/bagcoin/accounts/`, () => HttpResponse.json(mockAccounts)),
  http.post(`${API}/bagcoin/accounts/`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ ...mockAccounts[0], ...(body as object), id: 99 }, { status: 201 })
  }),
  http.patch(`${API}/bagcoin/accounts/:id`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ ...mockAccounts[0], ...(body as object) })
  }),
  http.delete(`${API}/bagcoin/accounts/:id`, () => new HttpResponse(null, { status: 204 })),

  http.get(`${API}/bagcoin/budgets/`, () => HttpResponse.json(mockBudgets)),
  http.get(`${API}/bagcoin/budgets/1`, () => HttpResponse.json(mockBudgetSingle)),
  http.post(`${API}/bagcoin/budgets/`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ ...mockBudgetSingle, ...(body as object) }, { status: 201 })
  }),
  http.patch(`${API}/bagcoin/budgets/:id`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ ...mockBudgetSingle, ...(body as object) })
  }),
  http.delete(`${API}/bagcoin/budgets/:id`, () => new HttpResponse(null, { status: 204 })),

  http.get(`${API}/transactions`, () => HttpResponse.json(mockTransactions)),
  http.get(`${API}/transactions/summary`, () => HttpResponse.json(mockSummary)),
  http.post(`${API}/transactions`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ ...mockTransactions.items[0], ...(body as object), id: "99" }, { status: 201 })
  }),
  http.patch(`${API}/transactions/:id`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ ...mockTransactions.items[0], ...(body as object) })
  }),
  http.delete(`${API}/transactions/:id`, () => new HttpResponse(null, { status: 204 })),

  http.get(`${API}/bagcoin/goals/`, () => HttpResponse.json(mockGoals)),
  http.post(`${API}/bagcoin/goals/`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ ...mockGoals.items[0], ...(body as object), id: 99 }, { status: 201 })
  }),
  http.patch(`${API}/bagcoin/goals/:id`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ ...mockGoals.items[0], ...(body as object) })
  }),
  http.delete(`${API}/bagcoin/goals/:id`, () => new HttpResponse(null, { status: 204 })),

  http.get(`${API}/bagcoin/credit-cards/`, () => HttpResponse.json(mockCreditCards)),
  http.post(`${API}/bagcoin/credit-cards/`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ ...mockCreditCards[0], ...(body as object), id: 99 }, { status: 201 })
  }),
  http.patch(`${API}/bagcoin/credit-cards/:id`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ ...mockCreditCards[0], ...(body as object) })
  }),
  http.delete(`${API}/bagcoin/credit-cards/:id`, () => new HttpResponse(null, { status: 204 })),

  http.get(`${API}/bagcoin/reports/`, () => HttpResponse.json(mockReports)),
  http.get(`${API}/bagcoin/reports/1`, () => HttpResponse.json(mockReports.items[0])),
  http.delete(`${API}/bagcoin/reports/:id`, () => new HttpResponse(null, { status: 204 })),

  http.get(`${API}/bagcoin/conversations/`, () => HttpResponse.json(mockConversations)),
  http.get(`${API}/bagcoin/conversations/conv-1`, () => HttpResponse.json(mockConversationDetail)),
  http.post(`${API}/bagcoin/conversations/`, () =>
    HttpResponse.json({ ...mockConversations.items[0], id: "conv-new" }, { status: 201 })
  ),
]

export const server = setupServer(...handlers)
