"use client"

import { ReportsView } from "@/components/release/reports-view"
import { serverTransactionToRelease } from "@/lib/adapters"
import { useAppStore } from "@/lib/store"
import type { ReleaseReportAnalytics, ReleaseTransaction } from "@/components/release/types"
import type { ServerTransaction, TransactionSummary } from "@/lib/api-server"
import { useExportTransactionsCsv } from "@/hooks/use-transactions"

interface Props {
  summary: TransactionSummary | null
  transactions: ServerTransaction[]
}

export function RelatoriosClient({ summary, transactions }: Props) {
  const toggleDrawer = useAppStore((state) => state.toggleDrawer)
  const analytics = buildReportAnalytics(summary, transactions.map(serverTransactionToRelease))
  const exportCsv = useExportTransactionsCsv()

  return (
    <div className="rls">
      <ReportsView
        analytics={analytics}
        onOpenDrawer={toggleDrawer}
      />
      <section className="mx-auto w-full max-w-md space-y-4 px-4 pb-8">
        <div className="rounded-xl border bg-white p-4">
          <h3 className="text-sm font-semibold">Ações</h3>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              className="rounded-md border px-3 py-2 text-sm font-medium disabled:opacity-50"
              disabled={exportCsv.isPending}
              onClick={() => exportCsv.mutate()}
            >
              Exportar CSV
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}

export function buildReportAnalytics(
  summary: TransactionSummary | null,
  transactions: ReleaseTransaction[]
): ReleaseReportAnalytics {
  const expenses = transactions.filter((tx) => tx.type === "despesa")

  return {
    balance: summary?.balance ?? 0,
    income: summary?.total_income ?? 0,
    expenses: summary?.total_expenses ?? 0,
    categoryExpenses: (summary?.categories ?? [])
      .map((cat) => ({ name: cat.name, amount: Math.abs(cat.amount), color: cat.color }))
      .sort((a, b) => b.amount - a.amount),
    monthlyExpenses: aggregateExpenses(expenses, "month"),
    weeklyExpenses: aggregateExpenses(expenses, "week").slice(0, 6),
    dailyExpenses: aggregateExpenses(expenses, "day").slice(0, 7),
  }
}

function aggregateExpenses(
  transactions: ReleaseTransaction[],
  mode: "month" | "week" | "day"
): Array<{ label: string; amount: number }> {
  const groups = new Map<string, { label: string; amount: number; sort: number }>()

  for (const tx of transactions) {
    const date = parseDate(tx.transactionDate)
    if (!date) continue
    const key = getGroupKey(date, mode)
    const current = groups.get(key.value) ?? { label: key.label, amount: 0, sort: key.sort }
    current.amount += tx.amount
    groups.set(key.value, current)
  }

  return Array.from(groups.values())
    .sort((a, b) => b.sort - a.sort)
    .map(({ label, amount }) => ({ label, amount }))
}

function parseDate(value?: string): Date | null {
  if (!value) return null
  const [year, month, day] = value.split("-").map(Number)
  if (!year || !month || !day) return null
  return new Date(year, month - 1, day)
}

function getGroupKey(date: Date, mode: "month" | "week" | "day") {
  if (mode === "month") {
    const value = `${date.getFullYear()}-${date.getMonth()}`
    return {
      value,
      label: date.toLocaleDateString("pt-BR", { month: "long", year: "numeric" }),
      sort: new Date(date.getFullYear(), date.getMonth(), 1).getTime(),
    }
  }

  if (mode === "week") {
    const start = new Date(date)
    start.setDate(date.getDate() - date.getDay())
    const end = new Date(start)
    end.setDate(start.getDate() + 6)
    return {
      value: `${start.getFullYear()}-${start.getMonth()}-${start.getDate()}`,
      label: `${start.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })} - ${end.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })}`,
      sort: start.getTime(),
    }
  }

  return {
    value: date.toISOString().slice(0, 10),
    label: date.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }),
    sort: date.getTime(),
  }
}
