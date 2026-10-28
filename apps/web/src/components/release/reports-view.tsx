"use client"

import type { ReactNode } from "react"
import { BarChart3, CalendarDays, TrendingDown, TrendingUp, Wallet } from "lucide-react"
import { AppBar } from "./app-bar"
import { formatCurrency } from "./format"
import { cn } from "@/lib/utils"
import type { ReleaseReportAnalytics } from "./types"

interface ReportsViewProps {
  analytics: ReleaseReportAnalytics
  onOpenDrawer?: () => void
}

export function ReportsView({ analytics, onOpenDrawer }: ReportsViewProps) {
  return (
    <div className="rls mx-auto min-h-dvh w-full max-w-md bg-[var(--rls-background)] shadow-[0_0_48px_rgba(22,82,240,0.08)]">
      <AppBar
        onOpenDrawer={onOpenDrawer}
        title="Relatórios"
        titleClassName="rls-text-title-lg text-[var(--rls-primary)]"
      />

      <main className="flex flex-col gap-[var(--rls-stack-gap-md)] px-[var(--rls-container-margin)] py-[var(--rls-stack-gap-md)]">
        <section className="grid grid-cols-2 gap-3">
          <SummaryCard
            title="Receitas"
            value={analytics.income}
            icon={<TrendingUp className="h-5 w-5" />}
            tone="green"
          />
          <SummaryCard
            title="Despesas"
            value={analytics.expenses}
            icon={<TrendingDown className="h-5 w-5" />}
            tone="red"
          />
          <SummaryCard
            title="Saldo"
            value={analytics.balance}
            icon={<Wallet className="h-5 w-5" />}
            tone="blue"
            className="col-span-2"
          />
        </section>

        <BarSection
          title="Maiores gastos por categoria"
          icon={<BarChart3 className="h-5 w-5" />}
          items={analytics.categoryExpenses}
          emptyLabel="Sem gastos por categoria ainda."
        />
        <BarSection
          title="Gastos por mês"
          icon={<CalendarDays className="h-5 w-5" />}
          items={analytics.monthlyExpenses}
          emptyLabel="Sem histórico mensal suficiente."
        />
        <BarSection
          title="Gastos por semana"
          icon={<CalendarDays className="h-5 w-5" />}
          items={analytics.weeklyExpenses}
          emptyLabel="Sem gastos nas últimas semanas."
        />
        <BarSection
          title="Gastos por dia"
          icon={<CalendarDays className="h-5 w-5" />}
          items={analytics.dailyExpenses}
          emptyLabel="Sem gastos diários recentes."
        />
      </main>
    </div>
  )
}

function SummaryCard({
  title,
  value,
  icon,
  tone,
  className,
}: {
  title: string
  value: number
  icon: ReactNode
  tone: "blue" | "green" | "red"
  className?: string
}) {
  const tones = {
    blue: "bg-[var(--rls-primary-container)]/10 text-[var(--rls-primary-container)]",
    green: "bg-[var(--rls-secondary-container)]/20 text-[var(--rls-on-secondary-container)]",
    red: "bg-[var(--rls-error-container)]/50 text-[var(--rls-error)]",
  }

  return (
    <div className={cn("rounded-[var(--rls-radius-lg)] border border-[var(--rls-outline-variant)] bg-[var(--rls-surface-container-lowest)] p-4 shadow-sm", className)}>
      <div className="mb-3 flex items-center gap-2">
        <span className={cn("flex h-9 w-9 items-center justify-center rounded-[var(--rls-radius)]", tones[tone])}>
          {icon}
        </span>
        <span className="text-sm font-semibold text-[var(--rls-on-surface-variant)]">{title}</span>
      </div>
      <p className="text-2xl font-bold leading-8 text-[var(--rls-on-surface)]">{formatCurrency(value)}</p>
    </div>
  )
}

function BarSection({
  title,
  icon,
  items,
  emptyLabel,
}: {
  title: string
  icon: ReactNode
  items: Array<{ name?: string; label?: string; amount: number; color?: string }>
  emptyLabel: string
}) {
  const max = Math.max(...items.map((item) => item.amount), 0)

  return (
    <section className="rounded-[var(--rls-radius-lg)] border border-[var(--rls-outline-variant)] bg-[var(--rls-surface-container-lowest)] p-4 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <span className="text-[var(--rls-primary-container)]">{icon}</span>
        <h2 className="text-base font-bold text-[var(--rls-on-surface)]">{title}</h2>
      </div>

      {items.length === 0 ? (
        <p className="text-sm text-[var(--rls-on-surface-variant)]">{emptyLabel}</p>
      ) : (
        <div className="flex flex-col gap-3">
          {items.slice(0, 6).map((item, index) => {
            const label = item.name || item.label || "Sem nome"
            const width = max > 0 ? Math.max(6, Math.round((item.amount / max) * 100)) : 0
            return (
              <div key={`${label}-${index}`} className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between gap-3">
                  <span className="truncate text-sm font-semibold text-[var(--rls-on-surface)]">{label}</span>
                  <span className="shrink-0 text-sm font-bold text-[var(--rls-on-surface)]">{formatCurrency(item.amount)}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-[var(--rls-surface-container)]">
                  <div
                    className="h-full rounded-full bg-[var(--rls-primary-container)]"
                    style={{
                      width: `${width}%`,
                      backgroundColor: item.color?.startsWith("#") ? item.color : undefined,
                    }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}
