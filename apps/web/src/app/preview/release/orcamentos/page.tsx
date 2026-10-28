"use client"

import { MonthlyBudgetsView } from "@/components/release"
import { mockBudgets } from "@/components/release/__preview__/mock-data"

export default function OrcamentosPreview() {
  return (
    <MonthlyBudgetsView
      budgets={mockBudgets}
      totalSpent={1730}
      totalBudget={2400}
      month="Abril de 2024"
      onAddBudget={() => {}}
    />
  )
}
