import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest"
import { http, HttpResponse } from "msw"
import { setupServer } from "msw/node"

const API_BASE = "http://localhost:8000/api/v1"

const mockTransactions = [
  {
    id: "1",
    type: "EXPENSE",
    name: "Supermercado Pão de Açúcar",
    category: "Alimentação",
    amount: 287.5,
    date: "30 Abr",
    source: "manual",
    status: "confirmed",
  },
  {
    id: "2",
    type: "INCOME",
    name: "Salário — Empresa X",
    category: "Salário",
    amount: 8500,
    date: "28 Abr",
    source: "auto",
    status: "confirmed",
  },
]

const mockSummary = {
  balance: 3220,
  total_income: 8500,
  total_expenses: 5280,
  transaction_count: 12,
  categories: [
    { name: "Alimentação", amount: 1150, color: "#ff6b35" },
    { name: "Transporte", amount: 380, color: "#0052ff" },
  ],
  recent_transactions: mockTransactions,
}

export const handlers = [
  http.get(`${API_BASE}/bagcoin/transactions`, () => {
    return HttpResponse.json({ items: mockTransactions, total: 2 })
  }),

  http.get(`${API_BASE}/bagcoin/transactions/summary`, () => {
    return HttpResponse.json(mockSummary)
  }),

  http.post(`${API_BASE}/bagcoin/transactions`, async () => {
    return HttpResponse.json(
      {
        id: "99",
        type: "EXPENSE",
        name: "Novo lançamento",
        category: "Lazer",
        amount: 50,
        date: "01 Mai",
        source: "manual",
        status: "confirmed",
      },
      { status: 201 }
    )
  }),

  http.patch(`${API_BASE}/bagcoin/transactions/:id`, async ({ params }) => {
    return HttpResponse.json({
      ...mockTransactions[0],
      id: params.id,
      name: "Atualizado",
    })
  }),

  http.delete(`${API_BASE}/bagcoin/transactions/:id`, () => {
    return new HttpResponse(null, { status: 204 })
  }),

  http.get(`${API_BASE}/auth/me`, () => {
    return HttpResponse.json({
      id: "test-user-id",
      email: "ana@email.com",
      full_name: "Ana Silva",
      is_active: true,
      email_verified: true,
      role: "user",
    })
  }),
]

const server = setupServer(...handlers)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe("Transaction API hooks", () => {
  it("mock server returns transactions list", async () => {
    const response = await fetch(`${API_BASE}/bagcoin/transactions`)
    const data = await response.json()
    expect(data.items).toHaveLength(2)
    expect(data.items[0].name).toBe("Supermercado Pão de Açúcar")
  })

  it("mock server returns summary", async () => {
    const response = await fetch(`${API_BASE}/bagcoin/transactions/summary`)
    const data = await response.json()
    expect(data.balance).toBe(3220)
    expect(data.total_income).toBe(8500)
    expect(data.total_expenses).toBe(5280)
  })

  it("mock server creates transaction", async () => {
    const response = await fetch(`${API_BASE}/bagcoin/transactions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        type: "EXPENSE",
        amount: 50,
        description: "Novo lançamento",
        category_name: "Lazer",
        source: "manual",
        status: "confirmed",
      }),
    })
    const data = await response.json()
    expect(data.id).toBe("99")
    expect(response.status).toBe(201)
  })

  it("mock server deletes transaction", async () => {
    const response = await fetch(`${API_BASE}/bagcoin/transactions/1`, {
      method: "DELETE",
    })
    expect(response.status).toBe(204)
  })

  it("mock server returns auth me", async () => {
    const response = await fetch(`${API_BASE}/auth/me`)
    const data = await response.json()
    expect(data.email).toBe("ana@email.com")
    expect(data.full_name).toBe("Ana Silva")
  })
})
