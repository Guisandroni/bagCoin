import { describe, it, expect } from "vitest"
import { cn, formatCurrency } from "@/lib/utils"
import {
  categoriesFromDefaultsAndServer,
  serverBudgetToRelease,
  serverTransactionToRelease,
  summaryToDashboardSummary,
} from "@/lib/adapters"
import { getCategoryLucideIcon } from "@/lib/category"

describe("formatCurrency", () => {
  it("formats positive values", () => {
    expect(formatCurrency(8500)).toBe("R$ 8.500,00")
  })

  it("formats negative values", () => {
    expect(formatCurrency(-287.5)).toBe("-R$ 287,50")
  })

  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("R$ 0,00")
  })

  it("formats large values", () => {
    expect(formatCurrency(1234567.89)).toBe("R$ 1.234.567,89")
  })
})

describe("cn utility", () => {
  it("merges class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar")
  })

  it("handles conditional classes", () => {
    expect(cn("base", false && "hidden", "visible")).toBe("base visible")
  })
})

describe("release transaction adapter", () => {
  it("uses transaction type as source of truth and normalizes expense amount", () => {
    const tx = serverTransactionToRelease({
      id: "1",
      type: "EXPENSE",
      name: "Farmácia",
      category: "Saúde",
      amount: -89.9,
      date: "09 Mai",
      source: "manual",
      status: "confirmed",
    })

    expect(tx.type).toBe("despesa")
    expect(tx.amount).toBe(89.9)
    expect(tx.category).toBe("Saúde")
  })

  it("maps seed transaction descriptions to lucide icons", () => {
    expect(getCategoryLucideIcon("Supermercado")).toBe(getCategoryLucideIcon("Compras"))
    expect(getCategoryLucideIcon("Freelance Design")).toBe(getCategoryLucideIcon("Salário"))
  })

  it("normalizes legacy English short months to pt-BR", () => {
    const tx = serverTransactionToRelease({
      id: "2",
      type: "INCOME",
      name: "Salário",
      category: "Receita",
      amount: 8500,
      date: "07 May",
      transaction_date: "2026-05-07",
      source: "manual",
      status: "confirmed",
    })

    expect(tx.date).toBe("07 mai")
    expect(tx.transactionDate).toBe("2026-05-07")
  })
})

describe("release dashboard adapter", () => {
  it("uses category color and absolute values for release budgets", () => {
    const budget = serverBudgetToRelease(
      {
        id: 1,
        name: "Moradia",
        period: "weekly",
        total_limit: 1000,
        total_spent: -404.1,
        total_remaining: 1404.1,
        percentage: -40.4,
        budget_type: "category",
        category_id: 1,
        category_name: "Moradia",
        created_at: "2026-05-01T00:00:00Z",
        updated_at: null,
      },
      [
        {
          id: 1,
          name: "Moradia",
          color: "#45B7D1",
          type: "despesa",
          is_default: true,
        },
      ]
    )

    expect(budget).toMatchObject({
      category: "Moradia",
      categoryColor: "#45B7D1",
      period: "weekly",
      spent: 404.1,
      total: 1000,
      remaining: 595.9,
      percentage: 40.4,
    })
  })

  it("combines fixed and created categories for release selectors", () => {
    const categories = categoriesFromDefaultsAndServer([
      {
        id: 10,
        name: "Pet",
        color: "#f97316",
        type: "despesa",
        is_default: false,
      },
    ])

    expect(categories.some((category) => category.name === "Alimentação")).toBe(true)
    expect(categories).toContainEqual(expect.objectContaining({
      name: "Investimentos",
      type: "investimento",
    }))
    expect(categories).toContainEqual(expect.objectContaining({
      name: "Pet",
      color: "#f97316",
      isFixed: false,
    }))
  })

  it("maps budgets into the dashboard summary", () => {
    const summary = summaryToDashboardSummary(
      {
        balance: 1000,
        total_income: 2000,
        total_expenses: 1000,
        transaction_count: 2,
        categories: [],
        recent_transactions: [],
      },
      [
        {
          id: 1,
          name: "Mercado Mensal",
          period: "monthly",
          total_limit: 1200,
          total_spent: 450,
          total_remaining: 750,
          percentage: 38,
          budget_type: "general",
          category_id: 1,
          category_name: "Alimentação",
          created_at: "2026-05-01T00:00:00Z",
          updated_at: null,
        },
      ],
      []
    )

    expect(summary.budgets).toEqual([
      {
        name: "Alimentação",
        spent: 450,
        total: 1200,
        remaining: 750,
        percentage: 38,
      },
    ])
  })

  it("does not expose negative available balance in release dashboard summary", () => {
    const summary = summaryToDashboardSummary(
      {
        balance: -4884.9,
        total_income: 0,
        total_expenses: 4884.9,
        transaction_count: 1,
        categories: [],
        recent_transactions: [],
      },
      [],
      []
    )

    expect(summary.totalBalance).toBe(0)
    expect(summary.income).toBe(0)
    expect(summary.expenses).toBe(4884.9)
  })

  it("preserves hex colors from transaction summary categories", () => {
    const summary = summaryToDashboardSummary(
      {
        balance: 1000,
        total_income: 2000,
        total_expenses: 1000,
        transaction_count: 2,
        categories: [
          { name: "Supermercado", amount: 700, color: "#FFC107" },
          { name: "Farmácia", amount: 300, color: "#FF1493" },
        ],
        recent_transactions: [],
      },
      [],
      []
    )

    expect(summary.categoryBreakdown).toEqual([
      { name: "Supermercado", percentage: 70, amount: 700, color: "#FFC107", emoji: "🛒" },
      { name: "Farmácia", percentage: 30, amount: 300, color: "#FF1493", emoji: "❤️" },
    ])
  })
})
