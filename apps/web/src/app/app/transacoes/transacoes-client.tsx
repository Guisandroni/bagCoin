"use client"

import { useState } from "react"
import { TransactionsView } from "@/components/release/transactions-view"
import {
  ReleaseCreateActionModal,
  type ReleaseCreateActionPayload,
} from "@/components/release/create-action-modal"
import { ReleaseTransactionDetailModal } from "@/components/release/transaction-detail-modal"
import { ToastBanner } from "@/components/release/toast-banner"
import { usePathname, useRouter } from "next/navigation"
import { getReleaseNavItems } from "@/lib/adapters"
import { useCreateTransaction, useDeleteTransaction, useUpdateTransaction } from "@/hooks/use-transactions"
import type { ReleaseCategory, ReleaseTransaction, ReleaseTransactionUpdateInput } from "@/components/release/types"

type ReleaseToastState = {
  message: string
  variant: "success" | "error"
} | null

interface Props {
  transactions: ReleaseTransaction[]
  categories?: ReleaseCategory[]
}

export function TransacoesClient({ transactions, categories = [] }: Props) {
  const pathname = usePathname()
  const router = useRouter()
  const createTransaction = useCreateTransaction({ silent: true })
  const updateTransaction = useUpdateTransaction({ silent: true })
  const deleteTransaction = useDeleteTransaction({ silent: true })
  const [selectedTransaction, setSelectedTransaction] = useState<ReleaseTransaction | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [toast, setToast] = useState<ReleaseToastState>(null)
  const navItems = getReleaseNavItems(pathname)
  const modalCategories = categories.length > 0
    ? categories
    : Array.from(
        new Map(
          transactions.map((transaction) => [
            transaction.category,
            {
              name: transaction.category,
              icon: transaction.categoryIcon,
              color: transaction.type === "receita" ? "#22c55e" : "#ef4444",
              allocated: 0,
              type: transaction.type,
              id: undefined,
            } satisfies ReleaseCategory,
          ])
        ).values()
      )
  return (
    <>
      <TransactionsView
        transactions={transactions}
        navItems={navItems}
        onSelectTransaction={setSelectedTransaction}
        onAddTransaction={() => setCreateOpen(true)}
        onNavigate={(href) => {
          if (href === "#settings") return
          router.push(href)
        }}
      />
      <ReleaseCreateActionModal
        open={createOpen}
        kind="transaction"
        categories={modalCategories}
        isSaving={createTransaction.isPending}
        onOpenChange={setCreateOpen}
        onSubmit={async (payload: ReleaseCreateActionPayload) => {
          if (payload.kind !== "transaction") return
          await createTransaction.mutateAsync({
            type: payload.type,
            description: payload.description,
            amount: payload.amount,
            category_id: payload.category_id,
            category_name: payload.category_name,
            transaction_date: payload.transaction_date,
            source: payload.source,
            status: payload.status,
            is_recurring: payload.is_recurring,
            recurrence_frequency: payload.recurrence_frequency,
          })
          setCreateOpen(false)
          setToast({ message: "Transação criada com sucesso.", variant: "success" })
          router.refresh()
        }}
      />
      <ReleaseTransactionDetailModal
        open={!!selectedTransaction}
        transaction={selectedTransaction}
        categories={modalCategories}
        onOpenChange={(open) => {
          if (!open) setSelectedTransaction(null)
        }}
        isSaving={updateTransaction.isPending}
        isDeleting={deleteTransaction.isPending}
        onSave={async (data: ReleaseTransactionUpdateInput) => {
          await updateTransaction.mutateAsync(data)
          setSelectedTransaction(null)
          setToast({ message: "Transação atualizada com sucesso.", variant: "success" })
          router.refresh()
        }}
        onDelete={async (transaction) => {
          try {
            await deleteTransaction.mutateAsync(transaction.id)
            setSelectedTransaction(null)
            setToast({ message: "Transação excluída com sucesso.", variant: "error" })
            router.refresh()
          } catch (error) {
            setToast({ message: "Erro ao excluir transação. Tente novamente.", variant: "error" })
            throw error
          }
        }}
      />
      <ToastBanner
        isOpen={!!toast}
        message={toast?.message ?? ""}
        variant={toast?.variant ?? "success"}
        onClose={() => setToast(null)}
      />
    </>
  )
}
