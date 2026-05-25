"use client"

import { ArrowDown, ArrowUp, Download } from "lucide-react"
import { AppBar } from "./app-bar"
import { InfoCard } from "./info-card"
import { DonutChart } from "./donut-chart"
import { BottomNavBar } from "./bottom-nav-bar"
import { cn } from "@/lib/utils"
import { CategoryIcon } from "@/lib/category"
import { useAppStore } from "@/lib/store"
import type { ReleaseDashboardSummary, ReleaseNavItem } from "./types"
import { formatCurrency, formatPercent } from "./format"

interface DashboardViewProps {
  summary: ReleaseDashboardSummary
  navItems: ReleaseNavItem[]
  onNavigate: (href: string) => void
  onViewAllTransactions?: () => void
  onViewAllCategories?: () => void
  onAddGoal?: () => void
  onExportCsv?: () => void
  isExportingCsv?: boolean
}

export function DashboardView({
  summary,
  navItems,
  onNavigate,
  onViewAllTransactions,
  onViewAllCategories,
  onExportCsv,
  isExportingCsv,
}: DashboardViewProps) {
  const toggleDrawer = useAppStore((state) => state.toggleDrawer)

  return (
    <div className="rls mx-auto min-h-dvh w-full max-w-md bg-[var(--rls-background)] shadow-[0_0_48px_rgba(22,82,240,0.08)]">
      <AppBar
        title="Dashboard"
        onOpenDrawer={toggleDrawer}
        titleClassName="min-w-0 flex-1 text-left text-[22px] font-semibold leading-7 text-[var(--rls-on-surface)]"
        actions={[
          {
            icon: <Download className="h-6 w-6" />,
            onClick: onExportCsv ?? (() => {}),
            label: isExportingCsv ? "Exportando CSV" : "Exportar CSV",
          },
        ]}
        className="border-b border-[var(--rls-outline-variant)]"
      />

      <main className="px-[var(--rls-container-margin)] flex flex-col gap-[var(--rls-stack-gap-lg)] pt-[var(--rls-stack-gap-md)] pb-[120px]">
        {/* Balance Section */}
        <section className="flex flex-col items-center">

          <span className="rls-text-body-md text-[var(--rls-on-surface-variant)] mb-1">
            Saldo Disponível
          </span>
          <h2 className="rls-text-display-lg text-[var(--rls-on-surface)]">
            {formatCurrency(summary.totalBalance)}
          </h2>

          <div className="mx-auto flex w-full max-w-[360px] justify-center gap-[var(--rls-stack-gap-md)] mt-[var(--rls-stack-gap-md)]">
            <InfoCard
              className="min-w-0 flex-1"
              variant="primary"
              title="Receita"
              value={formatCurrency(summary.income)}
              icon={<ArrowDown className="w-4 h-4" />}
            />
            <InfoCard
              className="min-w-0 flex-1"
              variant="danger"
              value={formatCurrency(summary.expenses)}
              title="Despesas"
              icon={
                <ArrowUp className="w-4 h-4 text-[var(--rls-error)]" />
              }
            />
          </div>
        </section>

        {/* Recent Transactions */}
        <section className="rounded-[var(--rls-radius)] bg-[var(--rls-surface-container-lowest)] p-[var(--rls-inline-padding-md)] shadow-sm">
          <div className="flex justify-between items-center mb-[var(--rls-stack-gap-md)]">
            <h3 className="rls-text-title-lg text-[var(--rls-on-surface)] text-base">
              Transações Recentes
            </h3>
            <button
              onClick={onViewAllTransactions}
              className="rls-text-label-lg text-[var(--rls-primary)]"
            >
              Ver tudo
            </button>
          </div>
          <div className="flex flex-col gap-[var(--rls-stack-gap-sm)]">
            {summary.recentTransactions.slice(0, 4).map((tx) => (
              <div
                key={tx.id}
                className="flex h-[72px] min-w-0 items-center justify-between gap-3 border-b border-[var(--rls-surface-variant)] last:border-0"
              >
                <div className="flex min-w-0 flex-1 items-center gap-4">
                  <div
                    className={cn(
                      "w-12 h-12 shrink-0 rounded-xl flex items-center justify-center",
                      tx.type === "receita"
                        ? "bg-[var(--rls-secondary-container)]/20"
                        : "bg-[var(--rls-error-container)]"
                    )}
                  >
                    <CategoryIcon
                      name={tx.name || tx.category}
                      size={24}
                      className={tx.type === "receita" ? "text-[var(--rls-secondary)]" : "text-[var(--rls-error)]"}
                    />
                  </div>
                  <div className="flex min-w-0 flex-1 flex-col">
                    <span className="rls-text-body-lg truncate text-sm text-[var(--rls-on-surface)]">
                      {tx.name}
                    </span>
                    <span className="rls-text-body-md text-[var(--rls-on-surface-variant)] text-xs">
                      {tx.date}
                    </span>
                  </div>
                </div>
                <span
                  className={cn(
                    "rls-text-title-lg shrink-0 whitespace-nowrap text-right text-sm font-semibold",
                    tx.type === "receita"
                      ? "text-[var(--rls-secondary)]"
                      : "text-[var(--rls-error)]"
                  )}
                  >
                    {tx.type === "receita" ? "+" : "-"}R${" "}
                    {formatCurrency(tx.amount).replace("R$", "").trim()}
                  </span>
                </div>
            ))}
          </div>
        </section>

        {/* Donut Chart */}
        <DonutChart
          segments={summary.categoryBreakdown.map((cat) => ({
            value: cat.percentage,
            amount: cat.amount,
            color: cat.color,
            label: cat.name,
            emoji: cat.emoji,
          }))}
          totalValue={summary.expenses}
          onOpen={onViewAllCategories}
        />

        {/* Goals & Budgets */}
        <section className="bg-[var(--rls-surface-container-lowest)] p-[var(--rls-inline-padding-md)] shadow-sm rounded-[var(--rls-radius)] flex flex-col gap-[var(--rls-stack-gap-md)] mb-4">
          <div className="flex justify-between items-center">
            <h3 className="rls-text-title-lg text-[var(--rls-on-surface)] text-base">
              Metas e Orçamentos
            </h3>
            {/* <button onClick={onAddGoal} className="text-[var(--rls-primary)]">
              <PlusCircle className="w-6 h-6" />
            </button> */}
          </div>

          <div className="flex flex-col gap-[var(--rls-stack-gap-md)]">
            <div className="flex flex-col gap-3">
              <span className="rls-text-label-lg text-[var(--rls-on-surface-variant)] uppercase">
                Metas
              </span>
              {summary.goals.length > 0 ? summary.goals.map((goal, i) => (
                <div key={i} className="flex flex-col gap-2">
                  <div className="flex justify-between items-end">
                    <div className="flex flex-col">
                      <span className="rls-text-body-lg text-[var(--rls-on-surface)] text-sm">
                        {goal.name}
                      </span>
                      <span className="rls-text-body-md text-[var(--rls-on-surface-variant)] text-xs">
                        {formatCurrency(goal.current)} de {formatCurrency(goal.target)}
                      </span>
                    </div>
                    <span className="rls-text-label-lg text-[var(--rls-primary)] text-[10px]">
                      {formatPercent(goal.percentage)}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-[var(--rls-surface-container-high)] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[var(--rls-primary-container)] rounded-full"
                      style={{ width: `${Math.min(goal.percentage, 100)}%` }}
                    />
                  </div>
                </div>
              )) : (
                <span className="rls-text-body-md text-[var(--rls-on-surface-variant)] text-sm">
                  Nenhuma meta cadastrada
                </span>
              )}
            </div>

            <div className="h-px bg-[var(--rls-surface-variant)]" />

            <div className="flex flex-col gap-3">
              <span className="rls-text-label-lg text-[var(--rls-on-surface-variant)] uppercase">
                Orçamentos
              </span>
              {summary.budgets.length > 0 ? summary.budgets.slice(0, 3).map((budget, i) => (
                <div key={`${budget.name}-${i}`} className="flex flex-col gap-2">
                  <div className="flex justify-between items-end">
                    <div className="flex flex-col">
                      <span className="rls-text-body-lg text-[var(--rls-on-surface)] text-sm">
                        {budget.name}
                      </span>
                      <span className="rls-text-body-md text-[var(--rls-on-surface-variant)] text-xs">
                        {formatCurrency(budget.spent)} de {formatCurrency(budget.total)}
                      </span>
                    </div>
                    <span className="rls-text-label-lg text-[var(--rls-error)] text-[10px]">
                      {formatPercent(budget.percentage)}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-[var(--rls-surface-container-high)] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[var(--rls-error)] rounded-full"
                      style={{ width: `${Math.min(budget.percentage, 100)}%` }}
                    />
                  </div>
                </div>
              )) : (
                <span className="rls-text-body-md text-[var(--rls-on-surface-variant)] text-sm">
                  Nenhum orçamento cadastrado
                </span>
              )}
            </div>
          </div>
        </section>
      </main>

      <BottomNavBar items={navItems} onNavigate={onNavigate} />
    </div>
  )
}
