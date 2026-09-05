"use client"

import { useState } from "react"
import { CalendarDays, Check, Pencil, Tag, Trash2, WalletCards, X } from "lucide-react"
import { Input } from "@/components/ui/input"
import { CategoryIcon } from "@/lib/category"
import { cn } from "@/lib/utils"
import { ReleaseConfirmActionModal } from "./confirm-action-modal"
import { ReleaseCategoryPicker } from "./category-picker"
import { ReleaseDatePicker } from "./date-picker"
import type { ReleaseCategory, ReleaseTransaction, ReleaseTransactionUpdateInput } from "./types"
import { formatCurrency, parseMoneyInput, sanitizeMoneyInput } from "./format"

interface ReleaseTransactionDetailModalProps {
  open: boolean
  transaction: ReleaseTransaction | null
  categories?: ReleaseCategory[]
  onOpenChange: (open: boolean) => void
  onSave: (data: ReleaseTransactionUpdateInput) => Promise<void> | void
  onDelete?: (transaction: ReleaseTransaction) => Promise<void> | void
  isSaving?: boolean
  isDeleting?: boolean
}

export function ReleaseTransactionDetailModal({
  open,
  transaction,
  categories = [],
  onOpenChange,
  onSave,
  onDelete,
  isSaving = false,
  isDeleting = false,
}: ReleaseTransactionDetailModalProps) {
  if (!open || !transaction) return null

  return (
    <ReleaseTransactionDetailModalContent
      key={transaction.id}
      transaction={transaction}
      categories={categories}
      onOpenChange={onOpenChange}
      onSave={onSave}
      onDelete={onDelete}
      isSaving={isSaving}
      isDeleting={isDeleting}
    />
  )
}

interface ReleaseTransactionDetailModalContentProps {
  transaction: ReleaseTransaction
  categories: ReleaseCategory[]
  onOpenChange: (open: boolean) => void
  onSave: (data: ReleaseTransactionUpdateInput) => Promise<void> | void
  onDelete?: (transaction: ReleaseTransaction) => Promise<void> | void
  isSaving: boolean
  isDeleting: boolean
}

function ReleaseTransactionDetailModalContent({
  transaction,
  categories,
  onOpenChange,
  onSave,
  onDelete,
  isSaving,
  isDeleting,
}: ReleaseTransactionDetailModalContentProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [type, setType] = useState<ReleaseTransaction["type"]>(transaction.type)
  const [description, setDescription] = useState(transaction.name)
  const initialCategory = categories.find(
    (item) => item.id === transaction.categoryId || item.name === transaction.category
  ) ?? null
  const [selectedCategory, setSelectedCategory] = useState<ReleaseCategory | null>(initialCategory)
  const [amount, setAmount] = useState(formatCurrency(transaction.amount).replace("R$", "").trim())
  const [date, setDate] = useState(transaction.transactionDate ?? "")
  const [isRecurring, setIsRecurring] = useState(transaction.isRecurring ?? false)
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false)

  const selectedIsIncome = transaction.type === "receita"
  const signedAmount = transaction.type === "receita"
    ? Math.abs(transaction.amount)
    : -Math.abs(transaction.amount)
  const fullDate = formatFullDate(transaction.transactionDate, transaction.date)
  const recurrenceLabel = formatRecurrence(transaction.isRecurring, transaction.recurrenceFrequency)
  const filteredCategories = categories.filter((item) =>
    type === "receita" ? item.type === "receita" || item.type === "investimento" : item.type === "despesa"
  )

  const handleSave = async () => {
    await onSave({
      id: transaction.id,
      type: type === "receita" ? "INCOME" : "EXPENSE",
      amount: parseMoneyInput(amount),
      description: description.trim() || transaction.name,
      category_id: selectedCategory?.id,
      category_name: selectedCategory?.name || transaction.category,
      transaction_date: date || transaction.transactionDate || getTodayIso(),
      is_recurring: isRecurring,
      recurrence_frequency: isRecurring ? "monthly" : undefined,
    })
    setIsEditing(false)
  }

  const handleConfirmDelete = async () => {
    if (!onDelete) return
    try {
      await onDelete(transaction)
      setConfirmDeleteOpen(false)
    } catch {
      // Parent controls the visible error toast; keep the confirmation open.
    }
  }

  return (
    <div className="rls">
      <button
        type="button"
        aria-label="Fechar detalhes"
        className="fixed inset-0 z-[60] bg-[rgba(27,28,30,0.4)] backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
      />

      <div className="fixed bottom-0 left-1/2 z-[60] flex w-[min(100%,28rem)] -translate-x-1/2 justify-center">
        <div className="flex h-dvh w-full max-w-[480px] flex-col rounded-t-[12px] bg-[var(--rls-surface-container-lowest)] shadow-sheet">
          <div className="flex justify-center pb-2 pt-3">
            <div className="h-1 w-10 rounded-full bg-[var(--rls-outline-variant)]" />
          </div>

          <div className="flex items-center justify-between border-b border-[var(--rls-outline-variant)] px-[var(--rls-inline-padding-md)] pb-4">
            <h2 className="rls-text-headline-sm text-[var(--rls-on-surface)]">
              {isEditing ? "Editar Transação" : "Detalhes da transação"}
            </h2>
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="flex h-10 w-10 items-center justify-center rounded-full text-[var(--rls-on-surface)] transition-colors hover:bg-[var(--rls-surface-container-high)]"
              aria-label="Fechar"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          <div className="flex min-h-0 flex-1 flex-col gap-[var(--rls-stack-gap-md)] overflow-y-auto px-[var(--rls-inline-padding-md)] py-[var(--rls-stack-gap-md)]">
            <div className="flex items-center gap-4 rounded-[var(--rls-radius)] bg-[var(--rls-surface-container)] p-4">
              <div
                className={cn(
                  "flex h-12 w-12 shrink-0 items-center justify-center rounded-[var(--rls-radius-lg)]",
                  transaction.type === "receita"
                    ? "bg-[var(--rls-secondary-container)]/20"
                    : "bg-[var(--rls-error-container)]"
                )}
              >
                <CategoryIcon
                  name={transaction.name || transaction.category}
                  size={24}
                  className={transaction.type === "receita" ? "text-[var(--rls-secondary)]" : "text-[var(--rls-error)]"}
                />
              </div>
              <div className="min-w-0 flex-1">
                <p className="rls-text-body-lg truncate text-[var(--rls-on-surface)]">
                  {transaction.name}
                </p>
                <p className="rls-text-body-md text-[var(--rls-on-surface-variant)]">
                  {transaction.category} · {fullDate}
                </p>
              </div>
              <span
                className={cn(
                  "rls-text-title-lg font-semibold",
                  transaction.type === "receita" ? "text-[var(--rls-secondary)]" : "text-[var(--rls-error)]"
                )}
              >
                {formatCurrency(signedAmount, { sign: "auto" })}
              </span>
            </div>

            {isEditing ? (
              <div className="flex flex-col gap-4">
                <div className="grid grid-cols-2 gap-2 rounded-[var(--rls-radius-pill)] bg-[var(--rls-surface-container)] p-1">
                  <button
                    type="button"
                    onClick={() => {
                      setType("despesa")
                      setSelectedCategory(null)
                    }}
                    className={cn(
                      "h-11 rounded-[var(--rls-radius-pill)] rls-text-label-lg transition-colors",
                      type === "despesa" ? "bg-[var(--rls-error-container)] text-[var(--rls-error)]" : "text-[var(--rls-on-surface-variant)]"
                    )}
                  >
                    Despesa
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setType("receita")
                      setSelectedCategory(null)
                    }}
                    className={cn(
                      "h-11 rounded-[var(--rls-radius-pill)] rls-text-label-lg transition-colors",
                      type === "receita" ? "bg-[var(--rls-secondary-container)]/25 text-[var(--rls-secondary)]" : "text-[var(--rls-on-surface-variant)]"
                    )}
                  >
                    Receita
                  </button>
                </div>

                <label className="flex flex-col gap-2">
                  <span className="rls-text-label-lg text-[var(--rls-on-surface-variant)]">Nome</span>
                  <Input
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    className="h-14 rounded-[var(--rls-radius-pill)] border-none bg-[var(--rls-surface-container)] px-5 text-base"
                  />
                </label>

                <RecurringTransactionFields
                  isRecurring={isRecurring}
                  onRecurringChange={setIsRecurring}
                />

                <ReleaseCategoryPicker
                  label="Categoria"
                  categories={filteredCategories}
                  selectedCategory={selectedCategory}
                  onSelect={setSelectedCategory}
                  collapsible
                />

                <div className="grid grid-cols-2 gap-3">
                  <label className="flex flex-col gap-2">
                    <span className="rls-text-label-lg text-[var(--rls-on-surface-variant)]">Valor</span>
                    <Input
                      value={amount}
                      inputMode="decimal"
                      placeholder="0,00"
                      onChange={(event) => setAmount(sanitizeMoneyInput(event.target.value))}
                      className="h-14 rounded-[var(--rls-radius-pill)] border-none bg-[var(--rls-surface-container)] px-5 text-base"
                    />
                  </label>
                  <ReleaseDatePicker
                    label="Data"
                    value={date}
                    onChange={setDate}
                  />
                </div>
              </div>
            ) : (
              <div className="divide-y divide-[var(--rls-surface-variant)]">
                {[
                  { icon: Tag, label: "Categoria", value: transaction.category },
                  { icon: CalendarDays, label: "Data", value: fullDate },
                  { icon: WalletCards, label: "Tipo", value: selectedIsIncome ? "Receita" : "Despesa" },
                  { icon: CalendarDays, label: "Recorrência", value: recurrenceLabel },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between gap-3 py-3">
                    <div className="flex items-center gap-2 text-[var(--rls-on-surface-variant)]">
                      <item.icon className="h-4 w-4" />
                      <span className="rls-text-label-lg">{item.label}</span>
                    </div>
                    <span className="rls-text-body-lg text-right text-[var(--rls-on-surface)]">
                      {item.value}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="border-t border-[var(--rls-outline-variant)] px-[var(--rls-inline-padding-md)] py-4">
            {isEditing ? (
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setIsEditing(false)}
                  disabled={isSaving}
                  className="h-14 flex-1 rounded-[var(--rls-radius-pill)] bg-[var(--rls-surface-container)] text-[var(--rls-on-surface)] rls-text-title-lg transition-colors disabled:opacity-50"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={isSaving || parseMoneyInput(amount) <= 0 || !selectedCategory?.id}
                  className="flex h-14 flex-1 items-center justify-center gap-2 rounded-[var(--rls-radius-pill)] bg-[var(--rls-primary-container)] text-white rls-text-title-lg shadow-md shadow-[var(--rls-primary-container)]/20 transition-colors active:scale-[0.98] disabled:opacity-50"
                >
                  <Check className="h-5 w-5" />
                  {isSaving ? "Salvando..." : "Salvar"}
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setConfirmDeleteOpen(true)}
                  disabled={!onDelete || isDeleting}
                  className="flex h-14 items-center justify-center gap-2 rounded-[var(--rls-radius-pill)] bg-[var(--rls-error)] text-white rls-text-title-lg shadow-md shadow-[var(--rls-error)]/20 transition-colors active:scale-[0.98] disabled:opacity-50"
                >
                  <Trash2 className="h-5 w-5" />
                  {isDeleting ? "Excluindo..." : "Excluir"}
                </button>
                <button
                  type="button"
                  onClick={() => setIsEditing(true)}
                  className="flex h-14 items-center justify-center gap-2 rounded-[var(--rls-radius-pill)] bg-[#111318] text-white rls-text-title-lg shadow-md shadow-black/15 transition-colors active:scale-[0.98]"
                >
                  <Pencil className="h-5 w-5" />
                  Editar
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
      <ReleaseConfirmActionModal
        open={confirmDeleteOpen}
        title="Excluir transação?"
        description="Esta ação não pode ser desfeita."
        confirmLabel="Excluir"
        cancelLabel="Cancelar"
        isLoading={isDeleting}
        onCancel={() => setConfirmDeleteOpen(false)}
        onConfirm={handleConfirmDelete}
      />
    </div>
  )
}

function formatRecurrence(
  isRecurring?: boolean,
  recurrenceFrequency?: "weekly" | "monthly" | "yearly"
): string {
  if (!isRecurring) return "Não recorrente"
  if (recurrenceFrequency === "weekly") return "Semanal"
  if (recurrenceFrequency === "yearly") return "Anual"
  return "Mensal"
}

function RecurringTransactionFields({
  isRecurring,
  onRecurringChange,
}: {
  isRecurring: boolean
  onRecurringChange: (value: boolean) => void
}) {
  return (
    <div className="flex flex-col gap-3 rounded-[var(--rls-radius)] bg-[var(--rls-surface-container-lowest)] p-3">
      <label className="flex items-center justify-between gap-3">
        <span className="rls-text-body-lg text-[var(--rls-on-surface)]">
          Transação recorrente
        </span>
        <input
          type="checkbox"
          checked={isRecurring}
          onChange={(event) => onRecurringChange(event.target.checked)}
          className="h-5 w-5 accent-[var(--rls-primary-container)]"
        />
      </label>
      {isRecurring ? (
        <p className="rls-text-body-md rounded-[var(--rls-radius)] bg-[var(--rls-surface-container)] px-4 py-3 text-[var(--rls-on-surface-variant)]">
          Será repetida mensalmente.
        </p>
      ) : null}
    </div>
  )
}

function formatFullDate(value: string | undefined, fallback: string): string {
  if (!value) return fallback
  const [year, month, day] = value.split("-").map(Number)
  if (!year || !month || !day) return fallback
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(new Date(year, month - 1, day))
}

function getTodayIso(): string {
  const today = new Date()
  const year = today.getFullYear()
  const month = String(today.getMonth() + 1).padStart(2, "0")
  const day = String(today.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}
