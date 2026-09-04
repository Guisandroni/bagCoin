export interface ReleaseProfile {
  name: string
  email: string
  avatarUrl?: string
  phone?: string
  tier?: string
}

export interface ReleaseGoal {
  id: string
  name: string
  target: number
  current: number
  deadline?: string
  category: ReleaseCategoryType
  color?: string
  icon?: string
  status?: "active" | "completed" | "cancelled"
}

export interface ReleaseBudget {
  id: string
  categoryId?: number
  category: string
  categoryIcon: string
  categoryColor: string
  period?: "monthly" | "weekly" | "yearly" | string
  spent: number
  total: number
  remaining: number
  percentage: number
  budgetDate?: string
}

export interface ReleaseTransaction {
  id: string
  name: string
  category: string
  categoryId?: number
  categoryIcon: string
  amount: number
  date: string
  transactionDate?: string
  type: "despesa" | "receita"
  source?: string
  isRecurring?: boolean
  recurrenceFrequency?: "weekly" | "monthly" | "yearly"
}

export type ReleaseCategoryType =
  | "viagem"
  | "veiculo"
  | "casa"
  | "outro"
  | "alimentacao"
  | "transporte"
  | "lazer"
  | "saude"
  | "moradia"
  | "investimento"
  | "compras"
  | "receita"

export interface ReleaseCategory {
  id?: number
  name: string
  icon: string
  emoji?: string
  color: string
  allocated: number
  percentage?: number
  isFixed?: boolean
  isUserCreated?: boolean
  canDelete?: boolean
  type: "despesa" | "receita" | "investimento"
}

export interface ReleaseReport {
  id: string
  name: string
  period: string
  date: string
  status: "concluido" | "arquivado" | "pendente"
  type: "mensal" | "anual" | "imposto" | "custom"
}

export interface ReleaseReportAnalytics {
  balance: number
  income: number
  expenses: number
  categoryExpenses: Array<{ name: string; amount: number; color: string }>
  monthlyExpenses: Array<{ label: string; amount: number }>
  weeklyExpenses: Array<{ label: string; amount: number }>
  dailyExpenses: Array<{ label: string; amount: number }>
}

export type ReleaseFilterPeriod =
  | "todo"
  | "week"
  | "month"
  | "calendar"

export type ReleaseBudgetType = "meta" | "orcamento"

export interface ReleaseTransactionUpdateInput {
  id: string
  type: "EXPENSE" | "INCOME"
  amount: number
  description: string
  category_id?: number
  category_name: string
  transaction_date: string
  is_recurring?: boolean
  recurrence_frequency?: "weekly" | "monthly" | "yearly"
}

export interface ReleaseDashboardSummary {
  totalBalance: number
  income: number
  expenses: number
  recentTransactions: ReleaseTransaction[]
  categoryBreakdown: { name: string; percentage: number; amount: number; color: string; emoji: string }[]
  goals: { name: string; current: number; target: number; percentage: number }[]
  budgets: { name: string; spent: number; total: number; remaining: number; percentage: number }[]
}

export interface ReleaseNavItem {
  label: string
  icon: string
  href: string
  isActive?: boolean
}
