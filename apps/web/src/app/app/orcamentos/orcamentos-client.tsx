"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { MonthlyBudgetsView } from "@/components/release/monthly-budgets-view"
import {
  ReleaseCreateActionModal,
  type ReleaseCreateActionPayload,
} from "@/components/release/create-action-modal"
import { ReleaseBudgetDetailModal } from "@/components/release/entity-detail-modals"
import { ToastBanner } from "@/components/release/toast-banner"
import { useCreateBudget, useDeleteBudget, useUpdateBudget } from "@/hooks/use-budgets"
import { getReleaseNavItems } from "@/lib/adapters"
import type { ReleaseBudget, ReleaseCategory } from "@/components/release/types"

interface Props {
  budgets: ReleaseBudget[]
  categories?: ReleaseCategory[]
  totalSpent: number
  totalBudget: number
}

export function OrcamentosClient({ budgets, categories = [], totalSpent, totalBudget }: Props) {
  const router = useRouter()
  const createBudget = useCreateBudget({ silent: true })
  const updateBudget = useUpdateBudget({ silent: true })
  const deleteBudget = useDeleteBudget({ silent: true })
  const [createOpen, setCreateOpen] = useState(false)
  const [selectedBudget, setSelectedBudget] = useState<ReleaseBudget | null>(null)
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null)
  const navItems = getReleaseNavItems("/app/orcamentos")
  const now = new Date()
  const month = now.toLocaleDateString("pt-BR", { month: "long", year: "numeric" })
  const modalCategories = categories.length > 0
    ? categories
    : budgets.map((budget) => ({
        name: budget.category,
        icon: budget.categoryIcon,
        color: budget.categoryColor,
        allocated: budget.spent,
        type: "despesa" as const,
        id: undefined,
      }))

  return (
    <div className="rls">
      <MonthlyBudgetsView
        budgets={budgets}
        totalSpent={totalSpent}
        totalBudget={totalBudget}
        month={month}
        onAddBudget={() => setCreateOpen(true)}
        onSelectBudget={setSelectedBudget}
        navItems={navItems}
        onNavigate={(href) => router.push(href)}
      />
      <ReleaseBudgetDetailModal
        open={!!selectedBudget}
        budget={selectedBudget}
        categories={modalCategories.filter((category) => Boolean(category.id))}
        isSaving={updateBudget.isPending}
        isDeleting={deleteBudget.isPending}
        onOpenChange={(open) => {
          if (!open) setSelectedBudget(null)
        }}
        onSave={async (data) => {
          await updateBudget.mutateAsync({
            id: Number(data.id),
            data: {
              category_id: data.category_id,
              category_name: data.category_name,
              period: data.period,
              budget_date: data.budget_date,
              total_limit: data.total_limit,
              budget_type: data.budget_type,
            },
          })
          setSelectedBudget(null)
          setToast({ message: "Orçamento atualizado com sucesso.", variant: "success" })
          router.refresh()
        }}
        onDelete={async (budget) => {
          await deleteBudget.mutateAsync(Number(budget.id))
          setSelectedBudget(null)
          setToast({ message: "Orçamento excluído com sucesso.", variant: "error" })
          router.refresh()
        }}
      />
      <ReleaseCreateActionModal
        open={createOpen}
        kind="budget"
        categories={modalCategories}
        isSaving={createBudget.isPending}
        onOpenChange={setCreateOpen}
        onSubmit={async (payload: ReleaseCreateActionPayload) => {
          if (payload.kind !== "budget") return
          await createBudget.mutateAsync({
            name: payload.name,
            category_id: payload.category_id,
            category_name: payload.category_name,
            period: payload.period,
            budget_date: payload.budget_date,
            total_limit: payload.total_limit,
            budget_type: payload.budget_type,
          })
          setCreateOpen(false)
          setToast({ message: "Orçamento criado com sucesso.", variant: "success" })
          router.refresh()
        }}
      />
      <ToastBanner
        isOpen={!!toast}
        message={toast?.message ?? ""}
        variant={toast?.variant ?? "success"}
        onClose={() => setToast(null)}
      />
    </div>
  )
}
