"use client"

import { BottomNavBar } from "./bottom-nav-bar"
import { FunctionHeader } from "./function-header"
import { InfoCard } from "./info-card"
import type { ReleaseGoal, ReleaseNavItem } from "./types"
import { CategoryIcon } from "@/lib/category"
import { formatCurrency, formatPercent } from "./format"
import { cn } from "@/lib/utils"

interface SavingsGoalsViewProps {
  goals: ReleaseGoal[]
  totalCurrent: number
  totalTarget: number
  globalPercentage: number
  onAddGoal?: () => void
  onSelectGoal?: (goal: ReleaseGoal) => void
  navItems?: ReleaseNavItem[]
  onNavigate?: (href: string) => void
}

export function SavingsGoalsView({
  goals,
  totalCurrent,
  totalTarget,
  globalPercentage,
  onAddGoal,
  onSelectGoal,
  navItems,
  onNavigate,
}: SavingsGoalsViewProps) {
  return (
    <div className="rls mx-auto min-h-dvh w-full max-w-md bg-[var(--rls-background)] shadow-[0_0_48px_rgba(22,82,240,0.08)]">
      <FunctionHeader
        title="Metas"
        actionLabel="Adicionar Meta"
        onAction={onAddGoal ?? (() => {})}
      />

      <main className="px-[var(--rls-container-margin)] flex flex-col gap-[var(--rls-stack-gap-lg)] pt-[var(--rls-stack-gap-md)] pb-[120px]">
        {/* Summary Card */}
        <InfoCard
          title="Total em Metas"
          value={formatCurrency(totalCurrent)}
          variant="default"
        >
          {/* Circular Progress */}
          <div className="flex items-center gap-4 mt-2">
            <div className="relative w-20 h-20 shrink-0">
              <svg className="w-full h-full" viewBox="0 0 36 36">
                <circle
                  className="text-[var(--rls-surface-container-high)]"
                  cx="18"
                  cy="18"
                  fill="transparent"
                  r="16"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <circle
                  className="text-[var(--rls-primary-container)]"
                  cx="18"
                  cy="18"
                  fill="transparent"
                  r="16"
                  stroke="currentColor"
                  strokeDasharray={`${globalPercentage}, 100`}
                  strokeLinecap="round"
                  strokeWidth="4"
                  transform="rotate(-90 18 18)"
                  style={{ transition: "stroke-dasharray 0.5s ease" }}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="rls-text-title-lg text-[var(--rls-primary-container)]">
                  {formatPercent(globalPercentage)}%
                </span>
              </div>
            </div>
            <span className="rls-text-body-md text-[var(--rls-on-surface-variant)] px-3 py-1 bg-[var(--rls-primary-container)]/10 rounded-[var(--rls-radius-pill)] text-[var(--rls-primary-container)]">
              {formatCurrency(totalTarget)} Alvo Global
            </span>
          </div>
        </InfoCard>

        {/* Goals List */}
        <div className="flex flex-col gap-[var(--rls-stack-gap-md)]">
          {goals.map((goal) => {
            const percentage = goal.target > 0 ? Math.round((goal.current / goal.target) * 100) : 0
            const tone = getGoalTone(goal, percentage)
            const statusLabel = getGoalStatusLabel(goal.status, percentage)
            return (
              <button
                type="button"
                onClick={() => onSelectGoal?.(goal)}
                key={goal.id}
                className="bg-[var(--rls-surface-container-lowest)] p-[var(--rls-inline-padding-md)] rounded-[var(--rls-radius-lg)] shadow-sm flex flex-col gap-2 text-left"
              >
                <div className="flex justify-between items-end">
                    <div className="flex items-center gap-3">
                    <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center", tone.iconBg)}>
                      <CategoryIcon name={goal.category} size={24} className={tone.icon} />
                    </div>
                    <div className="flex flex-col">
                      <span className="rls-text-body-lg text-[var(--rls-on-surface)]">
                        {goal.name}
                      </span>
                      <span className="rls-text-body-md text-[var(--rls-on-surface-variant)]">
                        {formatCurrency(goal.current)} / {formatCurrency(goal.target)}
                      </span>
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <span
                      className={cn(
                        "rls-text-label-lg rounded-[var(--rls-radius-pill)] px-2 py-0.5",
                        tone.badge
                      )}
                    >
                      {formatPercent(percentage)}%
                    </span>
                    <span
                      className={cn(
                        "rls-text-label-md rounded-[var(--rls-radius-pill)] px-2 py-0.5",
                        tone.badge
                      )}
                    >
                      {statusLabel}
                    </span>
                  </div>
                </div>
                <div className="w-full h-2 bg-[var(--rls-surface-container-high)] rounded-full overflow-hidden">
                  <div
                    className={cn("h-full rounded-full transition-all", tone.bar)}
                    style={{ width: `${Math.min(percentage, 100)}%` }}
                  />
                </div>
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

function getGoalStatusLabel(status: ReleaseGoal["status"], percentage: number): string {
  if (status === "cancelled") return "Cancelada"
  if (status === "completed" || percentage >= 100) return "Concluída"
  return "Ativa"
}

function getGoalTone(goal: ReleaseGoal, percentage: number) {
  if (goal.status === "cancelled") {
    return {
      iconBg: "bg-[var(--rls-error-container)]",
      icon: "text-[var(--rls-error)]",
      badge: "bg-[var(--rls-error-container)] text-[var(--rls-error)]",
      bar: "bg-[var(--rls-error)]",
    }
  }

  if (goal.status === "completed" || percentage >= 100) {
    return {
      iconBg: "bg-[var(--rls-secondary-container)]",
      icon: "text-[var(--rls-secondary)]",
      badge: "bg-[var(--rls-secondary-container)] text-[var(--rls-secondary)]",
      bar: "bg-[var(--rls-secondary)]",
    }
  }

  return {
    iconBg: "bg-[var(--rls-surface-container)]",
    icon: "text-[var(--rls-primary-container)]",
    badge: "bg-[var(--rls-primary-container)]/10 text-[var(--rls-primary-container)]",
    bar: "bg-[var(--rls-primary-container)]",
  }
}
