import dynamic from "next/dynamic"
import { getCategories, getTransactions } from "@/lib/api-server"
import { categoriesFromSources, serverTransactionToRelease } from "@/lib/adapters"
import TransacoesLoading from "./loading"

const TransacoesClient = dynamic(() => import("./transacoes-client").then((m) => m.TransacoesClient), {
  loading: () => <TransacoesLoading />,
})

export default async function TransacoesPage() {
  const [result, serverCategories] = await Promise.all([
    getTransactions(),
    getCategories(),
  ])
  const serverTransactions = result?.items ?? []
  const transactions = serverTransactions.map(serverTransactionToRelease)
  const categories = categoriesFromSources(null, serverCategories)

  return <TransacoesClient transactions={transactions} categories={categories} />
}
