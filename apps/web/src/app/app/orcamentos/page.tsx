import dynamic from "next/dynamic"
import { getBudgets, getCategories } from "@/lib/api-server"
import { categoriesFromSources, serverBudgetToRelease } from "@/lib/adapters"
import OrcamentosLoading from "./loading"

const OrcamentosClient = dynamic(() => import("./orcamentos-client").then((m) => m.OrcamentosClient), {
  loading: () => <OrcamentosLoading />,
})

export default async function OrcamentosPage() {
  const [budgets, serverCategories] = await Promise.all([
    getBudgets(),
    getCategories(),
  ])
  const releaseBudgets = (budgets ?? []).map((budget) =>
    serverBudgetToRelease(budget, serverCategories)
  )
  const categories = categoriesFromSources(null, serverCategories)

  const totalSpent = releaseBudgets.reduce((sum, b) => sum + b.spent, 0)
  const totalBudget = releaseBudgets.reduce((sum, b) => sum + b.total, 0)

  return (
    <OrcamentosClient
      budgets={releaseBudgets}
      categories={categories}
      totalSpent={totalSpent}
      totalBudget={totalBudget}
    />
  )
}
