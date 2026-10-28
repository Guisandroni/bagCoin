"use client"

import { useState } from "react"
import { FilterChips } from "./filter-chips"
import { InfoCard } from "./info-card"
import { BottomNavBar } from "./bottom-nav-bar"
import { FunctionHeader } from "./function-header"
import type { ReleaseCategory, ReleaseNavItem } from "./types"
import { cn } from "@/lib/utils"
import { formatCurrency } from "./format"

interface CategoriesViewProps {
  categories: ReleaseCategory[]
  totalAllocated: number
  navItems: ReleaseNavItem[]
  onNavigate: (href: string) => void
  onSearch?: (query: string) => void
  onAddCategory?: () => void
  onSelectCategory?: (category: ReleaseCategory) => void
}

export function CategoriesView({
  categories,
  totalAllocated,
  navItems,
  onNavigate,
  onAddCategory,
  onSelectCategory,
}: CategoriesViewProps) {
  const [activeFilter, setActiveFilter] = useState("todas")

  const filterOptions = [
    { label: "Todas", value: "todas" as const },
    { label: "Despesas", value: "despesa" as const },
    { label: "Receitas", value: "receita" as const },
    { label: "Investimentos", value: "investimento" as const },
    { label: "Criadas", value: "criadas" as const },
  ]

  const categoryBgColors: Record<string, string> = {
    alimentacao: "bg-[var(--rls-tertiary-container)]/20",
    moradia: "bg-[var(--rls-primary-container)]/10",
    transporte: "bg-[var(--rls-secondary-container)]/20",
    lazer: "bg-[var(--rls-tertiary-container)]/10",
    saude: "bg-[var(--rls-primary-container)]/10",
  }

  return (
    <div className="rls mx-auto min-h-dvh w-full max-w-md bg-[var(--rls-background)] shadow-[0_0_48px_rgba(22,82,240,0.08)]">
      <FunctionHeader
        title="Categorias"
        actionLabel="Adicionar Categoria"
        onAction={onAddCategory ?? (() => {})}
      />

      <main className="px-[var(--rls-container-margin)] flex flex-col gap-[var(--rls-stack-gap-lg)] pt-[var(--rls-stack-gap-md)] pb-[120px]">
        {/* Summary Hero */}
        <InfoCard
          variant="primary"
          title="Total Alocado"
          value={formatCurrency(totalAllocated)}
        />

        {/* Filter Chips */}
        <FilterChips
          options={filterOptions}
          selected={activeFilter}
          onChange={setActiveFilter}
        />

        {/* Category List */}
        <div className="flex flex-col gap-3">
          {categories
            .filter((cat) =>
              activeFilter === "todas"
              || (activeFilter === "criadas" ? cat.isUserCreated : cat.type === activeFilter)
            )
            .map((cat) => (
            <button
              type="button"
              onClick={() => onSelectCategory?.(cat)}
              key={cat.name}
              className="bg-[var(--rls-surface-container-lowest)] p-4 rounded-[var(--rls-radius-lg)] shadow-sm flex items-center gap-4 text-left"
            >
              <div
                className={cn(
                  "w-12 h-12 rounded-xl flex items-center justify-center text-xl",
                  categoryBgColors[cat.name.toLowerCase()] || "bg-[var(--rls-surface-container)]"
                )}
                style={{ backgroundColor: cat.color ? `${cat.color}20` : undefined }}
              >
                <span aria-hidden="true">{cat.icon || cat.emoji || "💳"}</span>
              </div>
              <div className="flex-1 min-w-0">
                <span className="rls-text-body-lg text-[var(--rls-on-surface)] block">
                  {cat.name}
                </span>
                <span className="rls-text-label-md text-[var(--rls-on-surface-variant)]">
                  {cat.type === "despesa"
                    ? `${cat.percentage}% utilizado`
                    : cat.type === "investimento"
                      ? "Investimento"
                      : cat.isFixed ? "Fixo" : ""}
                </span>
              </div>
              <span className="rls-text-body-lg text-[var(--rls-on-surface)] font-semibold">
                {formatCurrency(cat.allocated)}
              </span>
            </button>
          ))}
        </div>
      </main>

      <BottomNavBar items={navItems} onNavigate={onNavigate} />
    </div>
  )
}
