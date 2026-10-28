import type {
  ReleaseTransaction,
  ReleaseGoal,
  ReleaseBudget,
  ReleaseDashboardSummary,
  ReleaseCategory,
  ReleaseReport,
  ReleaseNavItem,
  ReleaseProfile,
} from "@/components/release/types"
import type {
  ServerTransaction,
  ServerGoal,
  ServerBudget,
  TransactionSummary,
  ServerReport,
  ServerCategory,
} from "@/lib/api-server"
import { useAuthStore } from "@/lib/auth-store"
import { CATEGORIES, getCategoryEmoji, getCategoryColor } from "@/lib/category"

export function serverTransactionToRelease(
  tx: ServerTransaction
): ReleaseTransaction {
  const typeName = tx.type === "INCOME" ? "receita" : "despesa"
  const catName = tx.category || tx.category_name || ""
  const iconKey = catName || tx.name || tx.description || ""
  return {
    id: tx.id,
    name: tx.name || tx.description || "",
    category: catName,
    categoryId: tx.category_id ?? undefined,
    categoryIcon: getCategoryEmoji(iconKey),
    amount: Math.abs(tx.amount),
    date: normalizeReleaseDate(tx.date || tx.transaction_date || ""),
    transactionDate: normalizeTransactionDate(tx.transaction_date),
    type: typeName,
    source: tx.source,
    isRecurring: tx.is_recurring ?? false,
    recurrenceFrequency: tx.recurrence_frequency ?? undefined,
  }
}

export function serverGoalToRelease(goal: ServerGoal): ReleaseGoal {
  const catType = mapGoalCategory(goal.title)
  return {
    id: String(goal.id),
    name: goal.title || "Meta",
    target: goal.target_amount,
    current: goal.current_amount,
    deadline: goal.deadline ?? undefined,
    category: catType,
    color: getCategoryColor(goal.title),
    status: goal.status,
  }
}

export function serverBudgetToRelease(
  budget: ServerBudget,
  categories: ServerCategory[] | null = null
): ReleaseBudget {
  const catName = budget.category_name || budget.name || ""
  const category = categories?.find(
    (item) => normalizeName(item.name) === normalizeName(catName)
  )
  const total = Math.abs(Number(budget.total_limit) || 0)
  const spent = Math.abs(Number(budget.total_spent) || 0)
  const remaining = total - spent
  const percentage = total > 0 ? Math.round((spent / total) * 1000) / 10 : 0
  return {
    id: String(budget.id),
    categoryId: budget.category_id ?? undefined,
    category: catName,
    categoryIcon: getCategoryEmoji(catName),
    categoryColor: category?.color || getCategoryColor(catName),
    period: budget.period,
    spent,
    total,
    remaining,
    percentage,
    budgetDate: budget.budget_date || budget.created_at?.slice(0, 10),
  }
}

export function serverReportToRelease(report: ServerReport): ReleaseReport {
  const statusMap: Record<string, ReleaseReport["status"]> = {
    completed: "concluido",
    archived: "arquivado",
    pending: "pendente",
  }
  return {
    id: String(report.id),
    name: `Relatório ${report.period_start?.slice(0, 7) ?? ""}`,
    period: report.period_start ?? "",
    date: new Date(report.created_at).toLocaleDateString("pt-BR"),
    status: statusMap[report.file_url ? "completed" : "pending"] ?? "pendente",
    type: "mensal",
  }
}

export function summaryToDashboardSummary(
  summary: TransactionSummary | null,
  budgets: ServerBudget[] | null,
  goals: ServerGoal[] | null
): ReleaseDashboardSummary {
  const recent = (summary?.recent_transactions ?? []).slice(0, 4).map(serverTransactionToRelease)
  const categories = (summary?.categories ?? []).map((cat) => ({
    name: cat.name,
    percentage: summary?.total_expenses
      ? Math.round((cat.amount / summary.total_expenses) * 100)
      : 0,
    amount: Math.abs(Number(cat.amount) || 0),
    color: cat.color || getCategoryColor(cat.name),
    emoji: getCategoryEmoji(cat.name),
  }))

  const goalProgress = (goals ?? []).map((g) => ({
    name: g.title,
    current: g.current_amount,
    target: g.target_amount,
    percentage: g.percentage,
  }))

  const budgetProgress = (budgets ?? []).map((b) => ({
    name: b.category_name || b.name || "Orçamento",
    spent: b.total_spent,
    total: b.total_limit,
    remaining: b.total_remaining,
    percentage: b.percentage,
  }))

  return {
    totalBalance: Math.max(summary?.balance ?? 0, 0),
    income: summary?.total_income ?? 0,
    expenses: summary?.total_expenses ?? 0,
    recentTransactions: recent,
    categoryBreakdown: categories,
    goals: goalProgress,
    budgets: budgetProgress,
  }
}

export function categoriesFromSummary(
  summary: TransactionSummary | null
): ReleaseCategory[] {
  if (!summary) return []
  return (summary.categories ?? []).map((cat) => ({
    name: cat.name,
    icon: getCategoryEmoji(cat.name),
    color: cat.color,
    allocated: cat.amount,
    percentage: summary.total_expenses
      ? Math.round((cat.amount / summary.total_expenses) * 100)
      : 0,
    type: "despesa" as const,
  }))
}

export function categoriesFromSources(
  summary: TransactionSummary | null,
  categories: ServerCategory[] | null
): ReleaseCategory[] {
  const byName = new Map<string, ReleaseCategory>()

  for (const item of categoriesFromSummary(summary)) {
    byName.set(normalizeName(item.name), item)
  }

  for (const category of categories ?? []) {
    const key = normalizeName(category.name)
    const existing = byName.get(key)
    if (existing) {
      byName.set(key, {
        ...existing,
        id: category.id,
        icon: category.emoji || existing.icon,
        emoji: category.emoji,
        color: category.color || existing.color,
        type: category.type,
        isFixed: category.is_default,
        isUserCreated: category.is_user_created ?? !category.is_default,
        canDelete: category.can_delete ?? !category.is_default,
      })
      continue
    }
    byName.set(key, {
      id: category.id,
      name: category.name,
      icon: category.emoji || getCategoryEmoji(category.name),
      emoji: category.emoji,
      color: category.color || getCategoryColor(category.name),
      allocated: 0,
      percentage: 0,
      type: category.type,
      isFixed: category.is_default,
      isUserCreated: category.is_user_created ?? !category.is_default,
      canDelete: category.can_delete ?? !category.is_default,
    })
  }

  return Array.from(byName.values())
}

export function categoriesFromDefaultsAndServer(
  categories: ServerCategory[] | null
): ReleaseCategory[] {
  const byName = new Map<string, ReleaseCategory>()

  const hasServerDefaults = (categories ?? []).some((category) => category.is_default)
  if (!categories?.length || !hasServerDefaults) {
    for (const category of CATEGORIES) {
      byName.set(normalizeName(category.name), {
        name: category.name,
        icon: category.icon,
        color: category.color,
        allocated: 0,
        percentage: 0,
        type: releaseCategoryType(category.name),
        isFixed: true,
      })
    }
  }

  for (const category of categories ?? []) {
    byName.set(normalizeName(category.name), {
      id: category.id,
      name: category.name,
      icon: category.emoji || getCategoryEmoji(category.name),
      emoji: category.emoji,
      color: category.color || getCategoryColor(category.name),
      allocated: 0,
      percentage: 0,
      type: category.type,
      isFixed: category.is_default,
      isUserCreated: category.is_user_created ?? !category.is_default,
      canDelete: category.can_delete ?? !category.is_default,
    })
  }

  return Array.from(byName.values())
}

export function getReleaseProfile(): ReleaseProfile {
  const { user } = useAuthStore.getState()
  return {
    name: user?.full_name ?? "Usuário",
    email: user?.email ?? "",
    avatarUrl: user?.avatar_url ?? undefined,
    phone: user?.phone_number ?? undefined,
    tier: "Investidor Pro",
  }
}

export function getReleaseNavItems(
  pathname: string
): ReleaseNavItem[] {
  return [
    {
      label: "Início",
      icon: "home",
      href: "/app",
      isActive: pathname === "/app",
    },
    {
      label: "Transações",
      icon: "portfolio",
      href: "/app/transacoes",
      isActive: pathname.startsWith("/app/transacoes"),
    },
    {
      label: "Orçamentos",
      icon: "wallet",
      href: "/app/orcamentos",
      isActive: pathname.startsWith("/app/orcamentos"),
    },
    {
      label: "Metas",
      icon: "target",
      href: "/app/metas",
      isActive: pathname.startsWith("/app/metas"),
    },
    {
      label: "Categorias",
      icon: "categorias",
      href: "/app/categorias",
      isActive: pathname.startsWith("/app/categorias"),
    },
  ]
}

function mapGoalCategory(name: string): ReleaseCategoryType {
  const lower = name.toLowerCase()
  if (lower.includes("viagem") || lower.includes("trip")) return "viagem"
  if (lower.includes("car") || lower.includes("veículo") || lower.includes("auto")) return "veiculo"
  if (lower.includes("casa") || lower.includes("home") || lower.includes("moradia")) return "casa"
  return "outro"
}

function normalizeReleaseDate(value: string): string {
  const trimmed = value.trim()
  const monthMap: Record<string, string> = {
    Jan: "jan",
    Feb: "fev",
    Mar: "mar",
    Apr: "abr",
    May: "mai",
    Jun: "jun",
    Jul: "jul",
    Aug: "ago",
    Sep: "set",
    Oct: "out",
    Nov: "nov",
    Dec: "dez",
  }

  return trimmed.replace(
    /\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b/g,
    (month) => monthMap[month] ?? month
  )
}

function normalizeName(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
}

function releaseCategoryType(name: string): ReleaseCategory["type"] {
  const normalized = normalizeName(name)
  if (normalized === "investimentos") return "investimento"
  const local = CATEGORIES.find((category) => normalizeName(category.name) === normalized)
  return local?.type === "income"
    ? "receita"
    : "despesa"
}

function normalizeTransactionDate(value?: string): string | undefined {
  if (!value) return undefined
  const dateOnly = value.split("T")[0]
  return /^\d{4}-\d{2}-\d{2}$/.test(dateOnly) ? dateOnly : undefined
}

import type { ReleaseCategoryType } from "@/components/release/types"
