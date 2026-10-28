import dynamic from "next/dynamic"
import { getTransactionSummary, getTransactions } from "@/lib/api-server"
import RelatoriosLoading from "./loading"

const RelatoriosClient = dynamic(() => import("./relatorios-client").then((m) => m.RelatoriosClient), {
  loading: () => <RelatoriosLoading />,
})

export default async function RelatoriosPage() {
  const [summary, transactions] = await Promise.all([
    getTransactionSummary(),
    getTransactions({ limit: 100 }),
  ])

  return (
    <RelatoriosClient
      summary={summary}
      transactions={transactions?.items ?? []}
    />
  )
}
