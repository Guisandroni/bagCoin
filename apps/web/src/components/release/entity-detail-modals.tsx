"use client"

import { useState } from "react"
import type { ReactNode } from "react"
import { CalendarDays, Check, Pencil, Tag, Target, Trash2, WalletCards, X } from "lucide-react"
import { Input } from "@/components/ui/input"
import { CategoryIcon } from "@/lib/category"
import { cn } from "@/lib/utils"
import { ReleaseConfirmActionModal } from "./confirm-action-modal"
import { ReleaseCategoryPicker } from "./category-picker"
import { ReleaseDatePicker } from "./date-picker"
import { formatCurrency, parseMoneyInput, sanitizeMoneyInput } from "./format"
import type { ReleaseBudget, ReleaseCategory, ReleaseGoal } from "./types"

type BudgetSaveInput = {
  id: string
  category_id?: number | null
  category_name: string
  period: "monthly" | "weekly" | "yearly"
  budget_date: string
  total_limit: number
  budget_type: "category"
}

type GoalSaveInput = {
  id: string
  title: string
  target_amount: number
  current_amount: number
  deadline: string | null
  status: "active" | "completed" | "cancelled"
}

type CategorySaveInput = {
  id: number
  name: string
  type: ReleaseCategory["type"]
  color: string
}

interface BudgetModalProps {
  open: boolean
  budget: ReleaseBudget | null
  categories: ReleaseCategory[]
  onOpenChange: (open: boolean) => void
  onSave: (data: BudgetSaveInput) => Promise<void> | void
  onDelete: (budget: ReleaseBudget) => Promise<void> | void
  isSaving?: boolean
  isDeleting?: boolean
}

export function ReleaseBudgetDetailModal({
  open,
  budget,
  categories,
  onOpenChange,
  onSave,
  onDelete,
  isSaving = false,
  isDeleting = false,
}: BudgetModalProps) {
  if (!open || !budget) return null
  return (
    <BudgetContent
      key={budget.id}
      budget={budget}
      categories={categories}
      isDeleting={isDeleting}
      isSaving={isSaving}
      onDelete={onDelete}
      onOpenChange={onOpenChange}
      onSave={onSave}
    />
  )
}

function BudgetContent({
  budget,
  categories,
  onOpenChange,
  onSave,
  onDelete,
  isSaving,
  isDeleting,
}: {
  budget: ReleaseBudget
  categories: ReleaseCategory[]
  onOpenChange: (open: boolean) => void
  onSave: (data: BudgetSaveInput) => Promise<void> | void
  onDelete: (budget: ReleaseBudget) => Promise<void> | void
  isSaving: boolean
  isDeleting: boolean
}) {
  const currentCategory = categories.find((item) => item.id === budget.categoryId || item.name === budget.category)
  const [isEditing, setIsEditing] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<ReleaseCategory | null>(currentCategory ?? null)
  const [period, setPeriod] = useState<"monthly" | "weekly" | "yearly">(normalizePeriod(budget.period))
  const [limit, setLimit] = useState(formatCurrency(budget.total).replace("R$", "").trim())
  const [budgetDate, setBudgetDate] = useState(budget.budgetDate ?? getTodayIso())
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false)
  const remainingLabel = budget.remaining < 0
    ? `${formatCurrency(Math.abs(budget.remaining))} acima do limite`
    : `${formatCurrency(budget.remaining)} restantes`

  const handleSave = async () => {
    if (!selectedCategory) return
    await onSave({
      id: budget.id,
      category_id: selectedCategory.id,
      category_name: selectedCategory.name,
      period,
      budget_date: budgetDate || getTodayIso(),
      total_limit: parseMoneyInput(limit),
      budget_type: "category",
    })
    setIsEditing(false)
  }

  return (
    <ReleaseEntitySheet
      title={isEditing ? "Editar Orçamento" : "Detalhes do orçamento"}
      onClose={() => onOpenChange(false)}
      footer={
        <EntityFooter
          isDeleting={isDeleting}
          isEditing={isEditing}
          isSaving={isSaving}
          saveDisabled={!selectedCategory || parseMoneyInput(limit) <= 0}
          onCancel={() => setIsEditing(false)}
          onDelete={() => setConfirmDeleteOpen(true)}
          onEdit={() => setIsEditing(true)}
          onSave={handleSave}
        />
      }
    >
      <SummaryRow
        iconName={budget.category}
        title={budget.category}
        subtitle={`${formatCurrency(budget.spent)} / ${formatCurrency(budget.total)} utilizados`}
        value={`${budget.percentage}%`}
        valueClassName="text-[var(--rls-primary-container)]"
      />

      {isEditing ? (
        <div className="flex flex-col gap-4">
          <ReleaseCategoryPicker
            label="Categoria"
            categories={categories}
            selectedCategory={selectedCategory}
            onSelect={setSelectedCategory}
            collapsible
          />

          <p className="rls-text-body-md rounded-[var(--rls-radius)] bg-[var(--rls-surface-container)] px-4 py-3 text-[var(--rls-on-surface-variant)]">
            Orçamento mensal.
          </p>

          <label className="flex flex-col gap-2">
            <span className="rls-text-label-lg text-[var(--rls-on-surface-variant)]">Limite</span>
            <Input
              value={limit}
              inputMode="decimal"
              placeholder="0,00"
              onChange={(event) => setLimit(sanitizeMoneyInput(event.target.value))}
              className="h-14 rounded-[var(--rls-radius-pill)] border-none bg-[var(--rls-surface-container)] px-5 text-base"
            />
          </label>

          <ReleaseDatePicker
            label="Data"
            value={budgetDate}
            onChange={setBudgetDate}
          />
        </div>
      ) : (
        <DetailRows
          rows={[
            { icon: Tag, label: "Categoria", value: budget.category },
            { icon: CalendarDays, label: "Data", value: formatDate(budget.budgetDate) },
            { icon: CalendarDays, label: "Período", value: periodLabel(normalizePeriod(budget.period)) },
            { icon: WalletCards, label: "Restante", value: remainingLabel },
          ]}
        />
      )}

      <ReleaseConfirmActionModal
        open={confirmDeleteOpen}
        title="Excluir orçamento?"
        description="Esta ação não pode ser desfeita."
        confirmLabel="Excluir"
        isLoading={isDeleting}
        onCancel={() => setConfirmDeleteOpen(false)}
        onConfirm={async () => {
          await onDelete(budget)
          setConfirmDeleteOpen(false)
        }}
      />
    </ReleaseEntitySheet>
  )
}

interface GoalModalProps {
  open: boolean
  goal: ReleaseGoal | null
  onOpenChange: (open: boolean) => void
  onSave: (data: GoalSaveInput) => Promise<void> | void
  onDelete: (goal: ReleaseGoal) => Promise<void> | void
  isSaving?: boolean
  isDeleting?: boolean
}

export function ReleaseGoalDetailModal({
  open,
  goal,
  onOpenChange,
  onSave,
  onDelete,
  isSaving = false,
  isDeleting = false,
}: GoalModalProps) {
  if (!open || !goal) return null
  return (
    <GoalContent
      key={goal.id}
      goal={goal}
      isDeleting={isDeleting}
      isSaving={isSaving}
      onDelete={onDelete}
      onOpenChange={onOpenChange}
      onSave={onSave}
    />
  )
}

function GoalContent({
  goal,
  onOpenChange,
  onSave,
  onDelete,
  isSaving,
  isDeleting,
}: {
  goal: ReleaseGoal
  onOpenChange: (open: boolean) => void
  onSave: (data: GoalSaveInput) => Promise<void> | void
  onDelete: (goal: ReleaseGoal) => Promise<void> | void
  isSaving: boolean
  isDeleting: boolean
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [title, setTitle] = useState(goal.name)
  const [target, setTarget] = useState(formatCurrency(goal.target).replace("R$", "").trim())
  const [current, setCurrent] = useState(formatCurrency(goal.current).replace("R$", "").trim())
  const [deadline, setDeadline] = useState((goal.deadline ?? "").slice(0, 10))
  const [status, setStatus] = useState<"active" | "completed" | "cancelled">(goal.status ?? "active")
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false)
  const percentage = goal.target > 0 ? Math.round((goal.current / goal.target) * 100) : 0
  const statusMeta = getGoalStatusMeta(status)

  const handleSave = async () => {
    await onSave({
      id: goal.id,
      title: title.trim() || goal.name,
      target_amount: parseMoneyInput(target),
      current_amount: parseMoneyInput(current),
      deadline: deadline || null,
      status,
    })
    setIsEditing(false)
  }

  return (
    <ReleaseEntitySheet
      title={isEditing ? "Editar Meta" : "Detalhes da meta"}
      onClose={() => onOpenChange(false)}
      footer={
        <EntityFooter
          isDeleting={isDeleting}
          isEditing={isEditing}
          isSaving={isSaving}
          saveDisabled={parseMoneyInput(target) <= 0}
          onCancel={() => setIsEditing(false)}
          onDelete={() => setConfirmDeleteOpen(true)}
          onEdit={() => setIsEditing(true)}
          onSave={handleSave}
        />
      }
    >
      <SummaryRow
        iconName={goal.name}
        title={goal.name}
        subtitle={`${statusMeta.label} · ${formatCurrency(goal.current)} / ${formatCurrency(goal.target)}`}
        value={`${percentage}%`}
        valueClassName={statusMeta.valueClassName}
      />

      {isEditing ? (
        <div className="flex flex-col gap-4">
          <EditInput label="Nome" value={title} onChange={setTitle} />
          <div className="grid grid-cols-2 gap-3">
            <EditInput label="Atual" value={current} onChange={setCurrent} money />
            <EditInput label="Alvo" value={target} onChange={setTarget} money />
          </div>
          <ReleaseDatePicker
            label="Prazo"
            value={deadline}
            onChange={setDeadline}
          />
          <GoalStatusPicker
            value={status}
            onChange={setStatus}
          />
        </div>
      ) : (
        <DetailRows
          rows={[
            { icon: Target, label: "Status", value: statusMeta.label },
            { icon: Target, label: "Alvo", value: formatCurrency(goal.target) },
            { icon: WalletCards, label: "Atual", value: formatCurrency(goal.current) },
            { icon: CalendarDays, label: "Prazo", value: formatDate(goal.deadline) },
          ]}
        />
      )}

      <ReleaseConfirmActionModal
        open={confirmDeleteOpen}
        title="Excluir meta?"
        description="Esta ação não pode ser desfeita."
        confirmLabel="Excluir"
        isLoading={isDeleting}
        onCancel={() => setConfirmDeleteOpen(false)}
        onConfirm={async () => {
          await onDelete(goal)
          setConfirmDeleteOpen(false)
        }}
      />
    </ReleaseEntitySheet>
  )
}

interface CategoryModalProps {
  open: boolean
  category: ReleaseCategory | null
  onOpenChange: (open: boolean) => void
  onSave: (data: CategorySaveInput) => Promise<void> | void
  onDelete: (category: ReleaseCategory) => Promise<void> | void
  isSaving?: boolean
  isDeleting?: boolean
}

export function ReleaseCategoryDetailModal({
  open,
  category,
  onOpenChange,
  onSave,
  onDelete,
  isSaving = false,
  isDeleting = false,
}: CategoryModalProps) {
  if (!open || !category) return null
  return (
    <CategoryContent
      key={category.id ?? category.name}
      category={category}
      isDeleting={isDeleting}
      isSaving={isSaving}
      onDelete={onDelete}
      onOpenChange={onOpenChange}
      onSave={onSave}
    />
  )
}

function CategoryContent({
  category,
  onOpenChange,
  onSave,
  onDelete,
  isSaving,
  isDeleting,
}: {
  category: ReleaseCategory
  onOpenChange: (open: boolean) => void
  onSave: (data: CategorySaveInput) => Promise<void> | void
  onDelete: (category: ReleaseCategory) => Promise<void> | void
  isSaving: boolean
  isDeleting: boolean
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [name, setName] = useState(category.name)
  const [type, setType] = useState<"despesa" | "receita">(
    category.type === "receita" ? "receita" : "despesa"
  )
  const [color, setColor] = useState(category.color)
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false)
  const canEdit = Boolean(category.id && category.isUserCreated && !category.isFixed)

  const handleSave = async () => {
    if (!category.id) return
    await onSave({ id: category.id, name: name.trim() || category.name, type, color })
    setIsEditing(false)
  }

  return (
    <ReleaseEntitySheet
      title={isEditing ? "Editar Categoria" : "Detalhes da categoria"}
      onClose={() => onOpenChange(false)}
      footer={
        <EntityFooter
          isDeleting={isDeleting}
          isEditing={isEditing}
          isSaving={isSaving}
          showEdit={canEdit}
          showDelete={category.canDelete ?? false}
          saveDisabled={!category.id || !name.trim()}
          onCancel={() => setIsEditing(false)}
          onDelete={() => setConfirmDeleteOpen(true)}
          onEdit={() => setIsEditing(true)}
          onSave={handleSave}
        />
      }
    >
      <SummaryRow
        iconName={category.name}
        title={category.name}
        subtitle={category.type === "despesa" ? "Despesa" : category.type === "receita" ? "Receita" : "Investimento"}
        value={formatCurrency(category.allocated)}
        valueClassName="text-[var(--rls-on-surface)]"
      />

      {isEditing ? (
        <div className="flex flex-col gap-4">
          <EditInput label="Nome" value={name} onChange={setName} />
          <select
            value={type}
            onChange={(event) => setType(event.target.value as "despesa" | "receita")}
            className="h-14 rounded-[var(--rls-radius-pill)] border-none bg-[var(--rls-surface-container)] px-4 text-base text-[var(--rls-on-surface)] outline-none"
          >
            <option value="despesa">Despesa</option>
            <option value="receita">Receita</option>
          </select>
          <label className="flex flex-col gap-2">
            <span className="rls-text-label-lg text-[var(--rls-on-surface-variant)]">Cor</span>
            <Input
              type="color"
              value={color}
              onChange={(event) => setColor(event.target.value)}
              className="h-14 rounded-[var(--rls-radius-pill)] border-none bg-[var(--rls-surface-container)] px-3"
            />
          </label>
        </div>
      ) : (
        <DetailRows
          rows={[
            { icon: Tag, label: "Tipo", value: category.type },
            { icon: WalletCards, label: "Valor", value: formatCurrency(category.allocated) },
            { icon: Target, label: "Padrão", value: category.isFixed ? "Sim" : "Não" },
          ]}
        />
      )}

      <ReleaseConfirmActionModal
        open={confirmDeleteOpen}
        title="Excluir categoria?"
        description="Categorias em uso por transações ou orçamentos não podem ser excluídas."
        confirmLabel="Excluir"
        isLoading={isDeleting}
        onCancel={() => setConfirmDeleteOpen(false)}
        onConfirm={async () => {
          await onDelete(category)
          setConfirmDeleteOpen(false)
        }}
      />
    </ReleaseEntitySheet>
  )
}

function ReleaseEntitySheet({
  title,
  children,
  footer,
  onClose,
}: {
  title: string
  children: ReactNode
  footer: ReactNode
  onClose: () => void
}) {
  return (
    <div className="rls">
      <button
        type="button"
        aria-label="Fechar detalhes"
        className="fixed inset-0 z-[60] bg-[rgba(27,28,30,0.4)] backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="fixed bottom-0 left-1/2 z-[60] flex w-[min(100%,28rem)] -translate-x-1/2 justify-center">
        <div className="flex h-dvh w-full max-w-[480px] flex-col rounded-t-[12px] bg-[var(--rls-surface-container-lowest)] shadow-sheet">
          <div className="flex justify-center pb-2 pt-3">
            <div className="h-1 w-10 rounded-full bg-[var(--rls-outline-variant)]" />
          </div>
          <div className="flex items-center justify-between border-b border-[var(--rls-outline-variant)] px-[var(--rls-inline-padding-md)] pb-4">
            <h2 className="rls-text-headline-sm text-[var(--rls-on-surface)]">{title}</h2>
            <button
              type="button"
              onClick={onClose}
              className="flex h-10 w-10 items-center justify-center rounded-full text-[var(--rls-on-surface)] transition-colors hover:bg-[var(--rls-surface-container-high)]"
              aria-label="Fechar"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
          <div className="flex min-h-0 flex-1 flex-col gap-[var(--rls-stack-gap-md)] overflow-y-auto px-[var(--rls-inline-padding-md)] py-[var(--rls-stack-gap-md)]">
            {children}
          </div>
          <div className="border-t border-[var(--rls-outline-variant)] px-[var(--rls-inline-padding-md)] py-4">
            {footer}
          </div>
        </div>
      </div>
    </div>
  )
}

function SummaryRow({
  iconName,
  title,
  subtitle,
  value,
  valueClassName,
}: {
  iconName: string
  title: string
  subtitle: string
  value: string
  valueClassName: string
}) {
  return (
    <div className="flex items-center gap-4 rounded-[var(--rls-radius)] bg-[var(--rls-surface-container)] p-4">
      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[var(--rls-radius-lg)] bg-[var(--rls-primary-container)]/10">
        <CategoryIcon name={iconName} size={24} className="text-[var(--rls-primary-container)]" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="rls-text-body-lg truncate text-[var(--rls-on-surface)]">{title}</p>
        <p className="rls-text-body-md text-[var(--rls-on-surface-variant)]">{subtitle}</p>
      </div>
      <span className={cn("rls-text-title-lg font-semibold", valueClassName)}>{value}</span>
    </div>
  )
}

function DetailRows({
  rows,
}: {
  rows: Array<{ icon: typeof Tag; label: string; value: string }>
}) {
  return (
    <div className="divide-y divide-[var(--rls-surface-variant)]">
      {rows.map((item) => (
        <div key={item.label} className="flex items-center justify-between gap-3 py-3">
          <div className="flex items-center gap-2 text-[var(--rls-on-surface-variant)]">
            <item.icon className="h-4 w-4" />
            <span className="rls-text-label-lg">{item.label}</span>
          </div>
          <span className="rls-text-body-lg text-right text-[var(--rls-on-surface)]">{item.value}</span>
        </div>
      ))}
    </div>
  )
}

function GoalStatusPicker({
  value,
  onChange,
}: {
  value: "active" | "completed" | "cancelled"
  onChange: (value: "active" | "completed" | "cancelled") => void
}) {
  return (
    <div className="flex flex-col gap-2">
      <span className="rls-text-label-lg text-[var(--rls-on-surface-variant)]">Status</span>
      <div className="grid grid-cols-1 gap-2">
        {(["active", "completed", "cancelled"] as const).map((option) => {
          const meta = getGoalStatusMeta(option)
          const selected = value === option
          return (
            <button
              key={option}
              type="button"
              onClick={() => onChange(option)}
              className={cn(
                "flex min-h-14 items-center justify-between rounded-[var(--rls-radius)] border px-4 py-3 text-left transition-colors",
                selected
                  ? `${meta.selectedClassName} border-transparent`
                  : "border-[var(--rls-outline-variant)] bg-[var(--rls-surface-container-lowest)] text-[var(--rls-on-surface)]"
              )}
            >
              <span className="rls-text-title-md">{meta.label}</span>
              <span className={cn("rls-text-label-md rounded-[var(--rls-radius-pill)] px-2 py-0.5", meta.badgeClassName)}>
                {meta.hint}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function EntityFooter({
  isEditing,
  isSaving,
  isDeleting,
  saveDisabled,
  showEdit = true,
  showDelete = true,
  onCancel,
  onDelete,
  onEdit,
  onSave,
}: {
  isEditing: boolean
  isSaving: boolean
  isDeleting: boolean
  saveDisabled?: boolean
  showEdit?: boolean
  showDelete?: boolean
  onCancel: () => void
  onDelete: () => void
  onEdit: () => void
  onSave: () => void
}) {
  if (isEditing) {
    return (
      <div className="flex gap-3">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSaving}
          className="h-14 flex-1 rounded-[var(--rls-radius-pill)] bg-[var(--rls-surface-container)] text-[var(--rls-on-surface)] rls-text-title-lg transition-colors disabled:opacity-50"
        >
          Cancelar
        </button>
        <button
          type="button"
          onClick={onSave}
          disabled={isSaving || saveDisabled}
          className="flex h-14 flex-1 items-center justify-center gap-2 rounded-[var(--rls-radius-pill)] bg-[var(--rls-primary-container)] text-white rls-text-title-lg shadow-md shadow-[var(--rls-primary-container)]/20 transition-colors active:scale-[0.98] disabled:opacity-50"
        >
          <Check className="h-5 w-5" />
          {isSaving ? "Salvando..." : "Salvar"}
        </button>
      </div>
    )
  }
  if (!showDelete && !showEdit) {
    return (
      <div className="rounded-[var(--rls-radius)] bg-[var(--rls-surface-container)] px-4 py-3 text-center">
        <span className="rls-text-body-md text-[var(--rls-on-surface-variant)]">
          Categoria padrão do sistema
        </span>
      </div>
    )
  }

  return (
    <div className={cn("grid gap-3", showDelete && showEdit ? "grid-cols-2" : "grid-cols-1")}>
      {showDelete ? (
        <button
          type="button"
          onClick={onDelete}
          disabled={isDeleting}
          className="flex h-14 items-center justify-center gap-2 rounded-[var(--rls-radius-pill)] bg-[var(--rls-error)] text-white rls-text-title-lg shadow-md shadow-[var(--rls-error)]/20 transition-colors active:scale-[0.98] disabled:opacity-50"
        >
          <Trash2 className="h-5 w-5" />
          {isDeleting ? "Excluindo..." : "Excluir"}
        </button>
      ) : null}
      {showEdit ? (
        <button
          type="button"
          onClick={onEdit}
          className="flex h-14 items-center justify-center gap-2 rounded-[var(--rls-radius-pill)] bg-[#111318] text-white rls-text-title-lg shadow-md shadow-black/15 transition-colors active:scale-[0.98]"
        >
          <Pencil className="h-5 w-5" />
          Editar
        </button>
      ) : null}
    </div>
  )
}

function EditInput({
  label,
  value,
  onChange,
  money = false,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  money?: boolean
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className="rls-text-label-lg text-[var(--rls-on-surface-variant)]">{label}</span>
      <Input
        value={value}
        inputMode={money ? "decimal" : undefined}
        placeholder={money ? "0,00" : undefined}
        onChange={(event) => onChange(money ? sanitizeMoneyInput(event.target.value) : event.target.value)}
        className="h-14 rounded-[var(--rls-radius-pill)] border-none bg-[var(--rls-surface-container)] px-5 text-base"
      />
    </label>
  )
}

function normalizePeriod(period: ReleaseBudget["period"]): "monthly" | "weekly" | "yearly" {
  if (period === "weekly" || period === "yearly") return period
  return "monthly"
}

function periodLabel(period: "monthly" | "weekly" | "yearly"): string {
  if (period === "weekly") return "Semanal"
  if (period === "yearly") return "Anual"
  return "Mensal"
}

function formatDate(value: string | undefined): string {
  if (!value) return "Sem prazo"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(date)
}

function getGoalStatusMeta(status: "active" | "completed" | "cancelled") {
  if (status === "completed") {
    return {
      label: "Concluída",
      hint: "finalizada",
      valueClassName: "text-[var(--rls-secondary)]",
      badgeClassName: "bg-[var(--rls-secondary-container)] text-[var(--rls-secondary)]",
      selectedClassName: "bg-[var(--rls-secondary-container)] text-[var(--rls-secondary)]",
    }
  }
  if (status === "cancelled") {
    return {
      label: "Cancelada",
      hint: "pausada",
      valueClassName: "text-[var(--rls-error)]",
      badgeClassName: "bg-[var(--rls-error-container)] text-[var(--rls-error)]",
      selectedClassName: "bg-[var(--rls-error-container)] text-[var(--rls-error)]",
    }
  }
  return {
    label: "Ativa",
    hint: "em andamento",
    valueClassName: "text-[var(--rls-primary-container)]",
    badgeClassName: "bg-[var(--rls-primary-container)]/10 text-[var(--rls-primary-container)]",
    selectedClassName: "bg-[var(--rls-primary-container)]/10 text-[var(--rls-primary-container)]",
  }
}

function getTodayIso(): string {
  const today = new Date()
  const year = today.getFullYear()
  const month = String(today.getMonth() + 1).padStart(2, "0")
  const day = String(today.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}
