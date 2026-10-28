import { getCategories, getTransactionSummary } from "@/lib/api-server"
import { categoriesFromSources } from "@/lib/adapters"
import { CategoriasClient } from "./categorias-client"

export default async function CategoriasPage() {
  const [summary, serverCategories] = await Promise.all([
    getTransactionSummary(),
    getCategories(),
  ])
  const categories = categoriesFromSources(summary, serverCategories)
  const totalAllocated = categories.reduce((s, c) => s + c.allocated, 0)

  return (
    <CategoriasClient
      categories={categories}
      totalAllocated={totalAllocated}
    />
  )
}
