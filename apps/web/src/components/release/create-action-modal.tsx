"use client"

import { useState } from "react"
import { DollarSign, Edit2, X } from "lucide-react"
import { PillInput } from "./pill-input"
import { ReleaseCategoryPicker } from "./category-picker"
import { ReleaseDatePicker } from "./date-picker"
import { cn } from "@/lib/utils"
import type { ReleaseCategory } from "./types"
import { parseMoneyInput, sanitizeMoneyInput } from "./format"

type CreateKind = "transaction" | "budget" | "goal" | "category"

export type ReleaseCreateActionPayload =
  | {
      kind: "transaction"
      type: "EXPENSE" | "INCOME"
      description: string
      amount: number
      category_id?: number
      category_name: string
      transaction_date: string
      source: "manual"
      status: "confirmed"
      is_recurring?: boolean
      recurrence_frequency?: "weekly" | "monthly" | "yearly"
    }
  | {
      kind: "budget"
      category_id: number
      name: string
      category_name: string
      period: "monthly" | "weekly" | "yearly"
      budget_date: string
      total_limit: number
      budget_type: "category"
    }
  | {
      kind: "goal"
      title: string
      target_amount: number
      current_amount: number
      deadline: string | null
      status: "active"
    }
  | {
      kind: "category"
      name: string
      type: "despesa" | "receita"
      color: string
    }

interface ReleaseCreateActionModalProps {
  open: boolean
  kind: CreateKind
  categories?: ReleaseCategory[]
  isSaving?: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (payload: ReleaseCreateActionPayload) => Promise<void> | void
}

const CATEGORY_COLORS = ["#1652F0", "#ef4444", "#22c55e", "#ff9800", "#a855f7", "#ec4899"]

const budgetLimitLabel: Record<"monthly" | "weekly" | "yearly", string> = {
  monthly: "Limite mensal",
  weekly: "Limite semanal",
  yearly: "Limite anual",
}


export function ReleaseCreateActionModal({
  open,
  kind,
  categories = [],
  isSaving = false,
  onOpenChange,
  onSubmit,
}: ReleaseCreateActionModalProps) {
  if (!open) return null

  return (
    <CreateActionModalContent
      key={kind}
      kind={kind}
      categories={categories}
      isSaving={isSaving}
      onOpenChange={onOpenChange}
      onSubmit={onSubmit}
    />
  )
}

function CreateActionModalContent({
  kind,
  categories,
  isSaving,
  onOpenChange,
  onSubmit,
}: Required<Omit<ReleaseCreateActionModalProps, "open">>) {
  const [transactionType, setTransactionType] = useState<"EXPENSE" | "INCOME">("EXPENSE")
  const [categoryType, setCategoryType] = useState<"despesa" | "receita">("despesa")
  const [name, setName] = useState("")
  const [amount, setAmount] = useState("")
  const [initialAmount, setInitialAmount] = useState("")
  const [amountTouched, setAmountTouched] = useState(false)
  const [categoryName, setCategoryName] = useState(categories[0]?.name ?? "")
  const [selectedTransactionCategory, setSelectedTransactionCategory] = useState<ReleaseCategory | null>(null)
  const [selectedBudgetCategory, setSelectedBudgetCategory] = useState<ReleaseCategory | null>(null)
  const [budgetPeriod, setBudgetPeriod] = useState<"monthly" | "weekly" | "yearly">("monthly")
  const [isRecurring, setIsRecurring] = useState(false)
  const [date, setDate] = useState(() =>
    kind === "transaction" || kind === "budget" || kind === "goal" ? getTodayIso() : ""
  )
  const [color, setColor] = useState(CATEGORY_COLORS[0])

  const title = {
    transaction: "Nova Transação",
    budget: "Novo Orçamento",
    goal: "Nova Meta",
    category: "Nova Categoria",
  }[kind]

  const description = {
    transaction: "Adicione uma movimentação manual",
    budget: "Defina um limite por categoria",
    goal: "Crie um objetivo financeiro",
    category: "Organize seus lançamentos",
  }[kind]

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const cleanName = name.trim()
    const cleanCategory = (selectedTransactionCategory?.name || categoryName || cleanName).trim()
    const parsedAmount = parseMoneyInput(amount)

    if (kind === "transaction" && selectedTransactionCategory?.id) {
      await onSubmit({
        kind,
        type: transactionType,
        description: cleanName,
        amount: parsedAmount,
        category_id: selectedTransactionCategory.id,
        category_name: cleanCategory,
        transaction_date: date || getTodayIso(),
        source: "manual",
        status: "confirmed",
        is_recurring: isRecurring,
        recurrence_frequency: isRecurring ? "monthly" : undefined,
      })
    } else if (kind === "budget" && selectedBudgetCategory?.id) {
      await onSubmit({
        kind,
        category_id: selectedBudgetCategory.id,
        name: selectedBudgetCategory.name,
        category_name: selectedBudgetCategory.name,
        period: budgetPeriod,
        budget_date: date || getTodayIso(),
        total_limit: parsedAmount,
        budget_type: "category",
      })
    } else if (kind === "goal") {
      await onSubmit({
        kind,
        title: cleanName,
        target_amount: parsedAmount,
        current_amount: parseMoneyInput(initialAmount),
        deadline: date || null,
        status: "active",
      })
    } else if (kind === "category") {
      await onSubmit({
        kind,
        name: cleanName,
        type: categoryType,
        color,
      })
    }
  }

  const parsedAmount = parseMoneyInput(amount)
  const goalAmountError = kind === "goal" && amountTouched && parsedAmount <= 0
    ? "Informe um valor alvo maior que zero."
    : undefined
  const disabled =
    isSaving ||
    (kind === "category"
      ? !name.trim() || isDuplicateCategory(name, categories)
      : kind === "budget"
        ? !selectedBudgetCategory?.id || parsedAmount <= 0
        : kind === "goal"
          ? !name.trim() || parsedAmount <= 0
          : !name.trim() || parsedAmount <= 0 || !selectedTransactionCategory?.id)

  return (
    <div className="rls">
      <button
        type="button"
        aria-label="Fechar criação"
        className="fixed inset-0 z-[60] bg-[rgba(27,28,30,0.4)] backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
      />
      <div className="fixed bottom-0 left-1/2 z-[60] flex w-[min(100%,28rem)] -translate-x-1/2 justify-center">
        <form
          onSubmit={handleSubmit}
          className="flex h-dvh w-full flex-col rounded-t-[12px] bg-[var(--rls-surface-container-lowest)] shadow-sheet"
        >
          <div className="flex items-start justify-between border-b border-[var(--rls-outline-variant)] px-[var(--rls-inline-padding-md)] py-4">
            <div>
              <h2 className="text-[26px] font-semibold leading-8 text-[var(--rls-on-surface)]">
                {title}
              </h2>
              <p className="rls-text-body-md mt-1 text-[var(--rls-on-surface-variant)]">
                {description}
              </p>
            </div>
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--rls-radius)] text-[var(--rls-on-surface-variant)]"
              aria-label="Fechar"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-[var(--rls-inline-padding-md)] py-5">
            {kind === "transaction" ? (
              <Segment
                value={transactionType}
                options={[
                  { label: "Despesa", value: "EXPENSE" },
                  { label: "Receita", value: "INCOME" },
                ]}
                onChange={(value) => {
                  setTransactionType(value)
                  setSelectedTransactionCategory(null)
                  setCategoryName("")
                }}
              />
            ) : null}

            {kind === "category" ? (
              <Segment
                value={categoryType}
                options={[
                  { label: "Despesa", value: "despesa" },
                  { label: "Receita", value: "receita" },
                ]}
                onChange={setCategoryType}
              />
            ) : null}

            {kind === "budget" ? (
              <p className="rls-text-body-md rounded-[var(--rls-radius)] bg-[var(--rls-surface-container)] px-4 py-3 text-[var(--rls-on-surface-variant)]">
                Orçamento mensal.
              </p>
            ) : null}

            {kind !== "budget" ? (
              <PillInput
                label={kind === "transaction" ? "Descrição" : kind === "goal" ? "Nome da Meta" : "Nome da Categoria"}
                icon={<Edit2 className="h-5 w-5" />}
                placeholder={kind === "transaction" ? "Ex: Supermercado" : "Digite o nome"}
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            ) : null}

            {kind === "transaction" ? (
              <RecurringTransactionFields
                isRecurring={isRecurring}
                onRecurringChange={setIsRecurring}
              />
            ) : null}

            {kind === "transaction" ? (
              <ReleaseCategoryPicker
                label="Categoria"
                categories={categories.filter((category) =>
                  transactionType === "INCOME"
                    ? category.type === "receita" || category.type === "investimento"
                    : category.type === "despesa"
                )}
                selectedCategory={selectedTransactionCategory}
                onSelect={(category) => {
                  setSelectedTransactionCategory(category)
                  setCategoryName(category.name)
                }}
                collapsible
              />
            ) : null}

            {kind === "budget" ? (
              <ReleaseCategoryPicker
                label="Categoria"
                categories={categories}
                selectedCategory={selectedBudgetCategory}
                onSelect={setSelectedBudgetCategory}
                collapsible
              />
            ) : null}

            {kind !== "category" ? (
              <PillInput
                label={kind === "budget" ? budgetLimitLabel[budgetPeriod] : kind === "goal" ? "Valor Alvo" : "Valor"}
                icon={<DollarSign className="h-5 w-5" />}
                placeholder="0,00"
                inputMode="decimal"
                value={amount}
                error={goalAmountError}
                onBlur={() => setAmountTouched(true)}
                onChange={(event) => {
                  setAmountTouched(true)
                  setAmount(sanitizeMoneyInput(event.target.value))
                }}
              />
            ) : null}

            {kind === "goal" ? (
              <PillInput
                label="Valor Inicial"
                icon={<DollarSign className="h-5 w-5" />}
                placeholder="0,00"
                inputMode="decimal"
                value={initialAmount}
                onChange={(event) => setInitialAmount(sanitizeMoneyInput(event.target.value))}
              />
            ) : null}

            {kind === "transaction" || kind === "budget" || kind === "goal" ? (
              <ReleaseDatePicker
                label={kind === "goal" ? "Prazo" : "Data"}
                value={date}
                onChange={setDate}
              />
            ) : null}

            {kind === "category" ? (
              <>
                {isDuplicateCategory(name, categories) ? (
                  <p className="rls-text-body-md -mt-2 px-4 text-[var(--rls-error)]">
                    {`Categoria "${name.trim()}" já existe.`}
                  </p>
                ) : null}
                <div className="flex flex-col gap-2">
                  <span className="rls-text-label-lg ml-4 text-[var(--rls-on-background)]">
                    Cor
                  </span>
                  <div className="flex gap-2">
                    {CATEGORY_COLORS.map((item) => (
                      <button
                        key={item}
                        type="button"
                        onClick={() => setColor(item)}
                        className={cn(
                          "h-10 w-10 rounded-full border-2",
                          color === item ? "border-[var(--rls-on-surface)]" : "border-transparent"
                        )}
                        style={{ backgroundColor: item }}
                        aria-label={`Selecionar cor ${item}`}
                      />
                    ))}
                  </div>
                </div>
              </>
            ) : null}
          </div>

          <div className="border-t border-[var(--rls-outline-variant)] px-[var(--rls-inline-padding-md)] py-4">
            <button
              type="submit"
              disabled={disabled}
              className="h-14 w-full rounded-[var(--rls-radius)] bg-[var(--rls-primary-container)] text-lg font-bold text-white shadow-md shadow-[var(--rls-primary-container)]/20 transition-colors active:scale-[0.98] disabled:bg-[var(--rls-surface-container-high)] disabled:text-[var(--rls-on-surface-variant)]"
            >
              {isSaving ? "Salvando..." : "Salvar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function Segment<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T
  options: { label: string; value: T }[]
  onChange: (value: T) => void
}) {
  return (
    <div className="grid gap-1 rounded-[var(--rls-radius)] bg-[var(--rls-surface-container)] p-1" style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={cn(
            "h-11 rounded-[var(--rls-radius)] text-sm font-semibold transition-colors",
            value === option.value
              ? "bg-[var(--rls-primary-container)] text-white shadow-sm"
              : "text-[var(--rls-on-surface-variant)]"
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
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
        <span className="rls-text-body-md text-[var(--rls-on-surface-variant)]">
          Será repetida mensalmente.
        </span>
      ) : null}
    </div>
  )
}

function getTodayIso(): string {
  const today = new Date()
  const year = today.getFullYear()
  const month = String(today.getMonth() + 1).padStart(2, "0")
  const day = String(today.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

function normalizeSearch(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
}

function isDuplicateCategory(name: string, categories: ReleaseCategory[]): boolean {
  const normalized = normalizeSearch(name)
  if (!normalized) return false
  return categories.some((category) => normalizeSearch(category.name) === normalized)
}
