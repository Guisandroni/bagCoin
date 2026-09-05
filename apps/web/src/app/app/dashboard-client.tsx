"use client"

import { usePathname, useRouter } from "next/navigation"
import { DashboardView } from "@/components/release/dashboard-view"
import { getReleaseNavItems, summaryToDashboardSummary } from "@/lib/adapters"
import { useExportTransactionsCsv } from "@/hooks/use-transactions"
import type { TransactionSummary, ServerBudget, ServerGoal } from "@/lib/api-server"

interface Props {
  summary: TransactionSummary | null
  budgets: ServerBudget[] | null
  goals: ServerGoal[] | null
}

export function DashboardClient({ summary, budgets, goals }: Props) {
  const pathname = usePathname()
  const router = useRouter()
  const exportCsv = useExportTransactionsCsv()
  const dashboardData = summaryToDashboardSummary(summary, budgets, goals)
  const navItems = getReleaseNavItems(pathname)

  return (
    <DashboardView
      summary={dashboardData}
      navItems={navItems}
      onNavigate={(href) => {
        if (href === "#settings") return
        router.push(href)
      }}
      onViewAllTransactions={() => router.push("/app/transacoes")}
      onViewAllCategories={() => router.push("/app/categorias")}
      onAddGoal={() => router.push("/app/metas")}
      onExportCsv={() => exportCsv.mutate()}
      isExportingCsv={exportCsv.isPending}
    />
  )
}
