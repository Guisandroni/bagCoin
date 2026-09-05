"use client"

import { useState } from "react"
import { DollarSign, Edit2 } from "lucide-react"
import { AppBar } from "./app-bar"
import { PillInput } from "./pill-input"
import { ReleaseDatePicker } from "./date-picker"
import { SegmentToggle } from "./segment-toggle"
import { CategoryIconGrid } from "./category-icon-grid"
import { sanitizeMoneyInput } from "./format"
import type { ReleaseBudgetType, ReleaseCategoryType } from "./types"

interface CreateGoalBudgetProps {
  onBack?: () => void
  onSubmit?: (data: {
    type: ReleaseBudgetType
    name: string
    target: string
    initial?: string
    category: ReleaseCategoryType
    deadline: string
  }) => void
  initialType?: ReleaseBudgetType
}

export function CreateGoalBudget({
  onBack,
  onSubmit,
  initialType = "meta",
}: CreateGoalBudgetProps) {
  const [type, setType] = useState<ReleaseBudgetType>(initialType)
  const [name, setName] = useState("")
  const [target, setTarget] = useState("")
  const [initial, setInitial] = useState("")
  const [category, setCategory] = useState<ReleaseCategoryType>("viagem")
  const [deadline, setDeadline] = useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const data = {
      type,
      name,
      target,
      category,
      deadline,
    }
    onSubmit?.(type === "meta" ? { ...data, initial } : data)
  }

  return (
    <div className="rls mx-auto min-h-dvh w-full max-w-md bg-[var(--rls-background)] shadow-[0_0_48px_rgba(22,82,240,0.08)]">
      <AppBar title="Criar Novo Objetivo" onBack={onBack} />

      <main className="px-[var(--rls-container-margin)] flex flex-col gap-[var(--rls-stack-gap-md)] pt-[var(--rls-stack-gap-md)] pb-8">
        {/* Segment Toggle */}
        <SegmentToggle value={type} onChange={setType} />

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className="bg-[var(--rls-surface-container-lowest)] rounded-[var(--rls-radius-lg)] shadow-sm p-[var(--rls-inline-padding-md)] flex flex-col gap-[var(--rls-stack-gap-md)]"
        >
          <PillInput
            label={type === "meta" ? "Nome do Objetivo" : "Nome do Orçamento"}
            icon={<Edit2 className="w-5 h-5" />}
            placeholder={type === "meta" ? "Ex: Viagem para o Japão" : "Ex: Mercado Mensal"}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />

          <PillInput
            label="Valor Alvo"
            icon={<DollarSign className="w-5 h-5" />}
            placeholder="0,00"
            inputMode="decimal"
            value={target}
            onChange={(e) => setTarget(sanitizeMoneyInput(e.target.value))}
          />

          {type === "meta" && (
            <PillInput
              label="Valor Inicial"
              icon={<DollarSign className="w-5 h-5" />}
              placeholder="0,00"
              inputMode="decimal"
              value={initial}
              onChange={(e) => setInitial(sanitizeMoneyInput(e.target.value))}
            />
          )}

          <CategoryIconGrid value={category} onChange={setCategory} />

          <ReleaseDatePicker
            label="Data Limite"
            value={deadline}
            onChange={setDeadline}
          />

          <button
            type="submit"
            className="w-full h-14 bg-[var(--rls-primary-container)] text-white rls-text-title-lg rounded-[var(--rls-radius-pill)] hover:bg-[var(--rls-primary)] transition-colors active:scale-[0.98] shadow-md shadow-[var(--rls-primary-container)]/20 flex items-center justify-center gap-2 mt-2"
          >
            {type === "meta" ? "Criar Meta" : "Criar Orçamento"}
          </button>
        </form>
      </main>
    </div>
  )
}
