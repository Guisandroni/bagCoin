"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { SavingsGoalsView } from "@/components/release/savings-goals-view"
import {
  ReleaseCreateActionModal,
  type ReleaseCreateActionPayload,
} from "@/components/release/create-action-modal"
import { ReleaseGoalDetailModal } from "@/components/release/entity-detail-modals"
import { ToastBanner } from "@/components/release/toast-banner"
import { useCreateGoal, useDeleteGoal, useUpdateGoal } from "@/hooks/use-goals"
import { getReleaseNavItems } from "@/lib/adapters"
import type { ReleaseGoal } from "@/components/release/types"

interface Props {
  goals: ReleaseGoal[]
  totalCurrent: number
  totalTarget: number
  globalPercentage: number
}

export function MetasClient({
  goals,
  totalCurrent,
  totalTarget,
  globalPercentage,
}: Props) {
  const router = useRouter()
  const createGoal = useCreateGoal({ silent: true })
  const updateGoal = useUpdateGoal({ silent: true })
  const deleteGoal = useDeleteGoal({ silent: true })
  const [createOpen, setCreateOpen] = useState(false)
  const [selectedGoal, setSelectedGoal] = useState<ReleaseGoal | null>(null)
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null)
  const navItems = getReleaseNavItems("/app/metas")

  return (
    <div className="rls">
      <SavingsGoalsView
        goals={goals}
        totalCurrent={totalCurrent}
        totalTarget={totalTarget}
        globalPercentage={globalPercentage}
        onAddGoal={() => setCreateOpen(true)}
        onSelectGoal={setSelectedGoal}
        navItems={navItems}
        onNavigate={(href) => router.push(href)}
      />
      <ReleaseGoalDetailModal
        open={!!selectedGoal}
        goal={selectedGoal}
        isSaving={updateGoal.isPending}
        isDeleting={deleteGoal.isPending}
        onOpenChange={(open) => {
          if (!open) setSelectedGoal(null)
        }}
        onSave={async (data) => {
          await updateGoal.mutateAsync({
            id: Number(data.id),
            data: {
              title: data.title,
              target_amount: data.target_amount,
              current_amount: data.current_amount,
              deadline: data.deadline ? `${data.deadline}T00:00:00` : null,
              status: data.status,
            },
          })
          setSelectedGoal(null)
          setToast({ message: "Meta atualizada com sucesso.", variant: "success" })
          router.refresh()
        }}
        onDelete={async (goal) => {
          await deleteGoal.mutateAsync(Number(goal.id))
          setSelectedGoal(null)
          setToast({ message: "Meta excluída com sucesso.", variant: "error" })
          router.refresh()
        }}
      />
      <ReleaseCreateActionModal
        open={createOpen}
        kind="goal"
        isSaving={createGoal.isPending}
        onOpenChange={setCreateOpen}
        onSubmit={async (payload: ReleaseCreateActionPayload) => {
          if (payload.kind !== "goal") return
          try {
            await createGoal.mutateAsync({
              title: payload.title,
              target_amount: payload.target_amount,
              current_amount: payload.current_amount,
              deadline: payload.deadline ? `${payload.deadline}T00:00:00` : null,
              status: payload.status,
            })
            setCreateOpen(false)
            setToast({ message: "Meta criada com sucesso.", variant: "success" })
            router.refresh()
          } catch {
            setToast({ message: "Informe um valor alvo maior que zero.", variant: "error" })
          }
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
