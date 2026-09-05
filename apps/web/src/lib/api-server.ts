import { cookies } from "next/headers"
import { cacheLife, cacheTag } from "next/cache"

const API_BASE =
  process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"

async function serverFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const cookieStore = await cookies()
  const token = cookieStore.get("access_token")?.value

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  }
  if (token) headers["Authorization"] = `Bearer ${token}`

  const url = `${API_BASE}${path}`
  const start = Date.now()

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    } as RequestInit)

    const duration = Date.now() - start

    if (!res.ok) {
      const body = await res.text().catch(() => "<unreadable>")
      if (res.status === 401) {
        console.warn(`[api-server] 401 ${path} (${duration}ms)`)
        return null as T
      }
      console.error(
        `[api-server] ${res.status} ${path} (${duration}ms)\n` +
        `  request: ${options?.method || "GET"} ${url}\n` +
        `  response: ${body.slice(0, 300)}`
      )
      return null as T
    }

    return res.json() as Promise<T>
  } catch (err) {
    const duration = Date.now() - start
    const message = err instanceof Error ? err.message : String(err)
    console.error(`[api-server] ERR ${path} (${duration}ms): ${message}`)
    return null as T
  }
}

// ── Typed data fetchers with 'use cache' ──────────────────

export interface ServerTransaction {
  id: string
  type: "INCOME" | "EXPENSE"
  name: string
  description?: string
  category?: string
  category_id?: number | null
  category_name?: string
  amount: number
  date?: string
  transaction_date?: string
  source: string
  status: string
  is_recurring?: boolean
  recurrence_frequency?: "weekly" | "monthly" | "yearly" | null
}

export interface TransactionSummary {
  balance: number
  total_income: number
  total_expenses: number
  transaction_count: number
  categories: Array<{ name: string; amount: number; color: string }>
  recent_transactions: ServerTransaction[]
}

export async function getTransactionSummary(): Promise<TransactionSummary | null> {
  return serverFetch<TransactionSummary>("/bagcoin/transactions/summary")
}

export interface ServerCategory {
  id: number
  name: string
  color: string
  emoji?: string
  type: "despesa" | "receita" | "investimento"
  is_default: boolean
  is_user_created?: boolean
  can_delete?: boolean
  created_at?: string
  updated_at?: string | null
}

export async function getCategories(): Promise<ServerCategory[] | null> {
  return serverFetch("/bagcoin/categories")
}

export async function getTransactions(params?: {
  search?: string
  type?: string
  status?: string
  page?: number
  skip?: number
  limit?: number
  date_from?: string
  date_to?: string
}): Promise<{ items: ServerTransaction[]; total: number } | null> {
  const qs = new URLSearchParams()
  if (params?.search) qs.set("search", params.search)
  if (params?.type) qs.set("type", params.type)
  if (params?.status) qs.set("status", params.status)
  if (params?.page) qs.set("page", String(params.page))
  if (params?.skip !== undefined) qs.set("skip", String(params.skip))
  if (params?.limit) qs.set("limit", String(params.limit))
  if (params?.date_from) qs.set("date_from", params.date_from)
  if (params?.date_to) qs.set("date_to", params.date_to)
  const query = qs.toString()
  return serverFetch(`/bagcoin/transactions${query ? `?${query}` : ""}`)
}

export interface ServerBudget {
  id: number
  name: string
  period: "monthly" | "weekly" | "yearly" | string
  total_limit: number
  total_spent: number
  total_remaining: number
  percentage: number
  budget_type: string
  budget_date?: string
  category_id: number | null
  category_name: string | null
  created_at: string
  updated_at: string | null
}

export async function getBudgets(): Promise<ServerBudget[] | null> {
  return serverFetch("/bagcoin/budgets")
}

export interface ServerGoal {
  id: number
  title: string
  target_amount: number
  current_amount: number
  remaining_amount: number
  percentage: number
  status: "active" | "completed" | "cancelled"
  deadline: string | null
  created_at: string
  updated_at: string | null
}

export async function getGoals(): Promise<ServerGoal[] | null> {
  return serverFetch("/bagcoin/goals")
}

export interface ServerAccount {
  id: string
  name: string
  bank: string
  type: "CHECKING" | "SAVINGS"
  balance: number
  color: string
  active: boolean
  created_at: string
}

export async function getAccounts(): Promise<ServerAccount[] | null> {
  "use cache: private"
  cacheTag("accounts")
  cacheLife("hours")
  return serverFetch("/bagcoin/accounts")
}

export interface ServerCreditCard {
  id: string
  name: string
  issuer: string
  limit: number
  closing_day: number
  due_day: number
  color: string
  active: boolean
  created_at: string
}

export async function getCreditCards(): Promise<ServerCreditCard[] | null> {
  "use cache: private"
  cacheTag("credit-cards")
  cacheLife("hours")
  return serverFetch("/bagcoin/credit-cards")
}

export interface ServerReport {
  id: number
  user_uuid: string | null
  period_start: string
  period_end: string
  file_url: string | null
  created_at: string
  updated_at: string
}

export async function getReports(): Promise<ServerReport[] | null> {
  "use cache: private"
  cacheTag("reports")
  cacheLife("hours")
  return serverFetch("/bagcoin/reports")
}

export interface ServerConversation {
  id: string
  phone_number: string
  platform: string
  status: string
  message_count: number
  last_message: string | null
  last_message_at: string | null
  created_at: string
}

export async function getConversations(): Promise<ServerConversation[] | null> {
  "use cache: private"
  cacheTag("conversations")
  cacheLife("minutes")
  return serverFetch("/bagcoin/conversations")
}
