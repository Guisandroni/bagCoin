"use client"

import { BottomNavBar } from "./bottom-nav-bar"
import { FunctionHeader } from "./function-header"
import { ProgressCard } from "./progress-card"
import type { ReleaseBudget, ReleaseNavItem } from "./types"
import { getCategoryLucideIcon } from "@/lib/category"
import { formatCurrency, formatPercent } from "./format"

interface MonthlyBudgetsViewProps {
  budgets: ReleaseBudget[]
  totalSpent: number
  totalBudget: number
  month: string
  onAddBudget?: () => void
  onSelectBudget?: (budget: ReleaseBudget) => void
  navItems?: ReleaseNavItem[]
  onNavigate?: (href: string) => void
}

export function MonthlyBudgetsView({
  budgets,
  totalSpent,
  totalBudget,
  month,
  onAddBudget,
  onSelectBudget,
  navItems,
  onNavigate,
}: MonthlyBudgetsViewProps) {
  const percentage = totalBudget > 0 ? Math.round((totalSpent / totalBudget) * 100) : 0
  const remaining = totalBudget - totalSpent
  const progressWidth = Math.min(Math.max(percentage, 0), 100)

  return (
    <div className="rls mx-auto min-h-dvh w-full max-w-md bg-[var(--rls-background)] shadow-[0_0_48px_rgba(22,82,240,0.08)]">
      <FunctionHeader
        title="Orçamentos"
        actionLabel="Adicionar Orçamento"
        onAction={onAddBudget ?? (() => {})}
      />

      <main className="px-[var(--rls-container-margin)] flex flex-col gap-[var(--rls-stack-gap-lg)] pt-[var(--rls-stack-gap-md)] pb-[120px]">
        {/* Total Budget Card */}
        <div className="bg-[var(--rls-surface-container-lowest)] rounded-[var(--rls-radius-lg)] p-[var(--rls-inline-padding-md)] shadow-sm flex flex-col gap-3">
          <div className="flex justify-between items-start">
            <div>
              <span className="rls-text-body-md text-[var(--rls-on-surface-variant)]">
                Orçamento Total
              </span>
              <p className="rls-text-label-md text-[var(--rls-on-surface-variant)]">
                {month}
              </p>
            </div>
          </div>

          <div className="flex items-baseline gap-2">
            <span className="rls-text-display-md text-[var(--rls-on-surface)]">
              {formatCurrency(totalSpent)}
            </span>
            <span className="rls-text-body-md text-[var(--rls-on-surface-variant)]">
              / {formatCurrency(totalBudget)} utilizados
            </span>
          </div>

          <div className="w-full h-2 bg-[var(--rls-surface-container-high)] rounded-full overflow-hidden">
            <div
              className="h-full bg-[var(--rls-primary-container)] rounded-full"
              style={{ width: `${progressWidth}%` }}
            />
          </div>

          <div className="flex justify-between">
            <span className="rls-text-label-md text-[var(--rls-primary-container)]">
              {formatPercent(percentage)}% utilizado
            </span>
            <span className="rls-text-label-md text-[var(--rls-on-surface-variant)]">
              {formatBudgetRemaining(remaining)}
            </span>
          </div>
        </div>

        {/* Budget Category Cards */}
        <div className="flex flex-col gap-[var(--rls-stack-gap-md)]">
          {budgets.map((budget) => {
            const Icon = getCategoryLucideIcon(budget.category)
            const remainingText = formatBudgetRemaining(budget.remaining)
            return (
              <button
                key={budget.id}
                type="button"
                onClick={() => onSelectBudget?.(budget)}
                className="text-left"
              >
                <ProgressCard
                  title={budget.category}
                  subtitle={`${formatCurrency(budget.spent)} / ${formatCurrency(budget.total)}`}
                  current={budget.spent}
                  target={budget.total}
                  percentage={budget.percentage}
                  color="blue"
                  remainingText={remainingText}
                  icon={<Icon className="w-5 h-5" />}
                  iconBg="bg-[var(--rls-surface-container)]"
                  iconColor={budget.categoryColor}
                  percentageClassName="text-[var(--rls-primary-container)]"
                  remainingClassName="text-[var(--rls-on-surface-variant)]"
                  titleTrailing={
                    <BudgetDateMeta date={budget.budgetDate} period={budget.period} />
                  }
                />
              </button>
            )
          })}
        </div>
      </main>

      {navItems && onNavigate ? (
        <BottomNavBar items={navItems} onNavigate={onNavigate} />
      ) : null}
    </div>
  )
}

function BudgetDateMeta({ date, period }: { date?: string; period?: string }) {
  return (
    <div className="flex flex-col items-end">
      <span className="rls-text-label-lg text-[var(--rls-on-surface)]">
        {formatBudgetDate(date)}
      </span>
      <span className="rls-text-label-md text-[var(--rls-on-surface-variant)]">
        {formatBudgetPeriod(period)}
      </span>
    </div>
  )
}

function formatBudgetDate(value?: string): string {
  if (!value) return "--/--"
  const [year, month, day] = value.slice(0, 10).split("-").map(Number)
  if (!year || !month || !day) return "--/--"
  const date = new Date(year, month - 1, day)
  const monthName = new Intl.DateTimeFormat("pt-BR", { month: "long" }).format(date)
  return `${day}/${monthName}`
}

function formatBudgetPeriod(period?: string): string {
  return period === "monthly" || !period ? "mensal" : period
}

function formatBudgetRemaining(value: number): string {
  if (value < 0) return `${formatCurrency(Math.abs(value))} acima do limite`
  return `${formatCurrency(value)} restantes`
}
