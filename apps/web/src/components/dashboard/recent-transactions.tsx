"use client"

import Link from "next/link"
import { ArrowRight } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useAppStore } from "@/lib/store"
import { useTransactionSummary } from "@/hooks/use-transactions"
import { CATEGORIES } from "@/lib/constants"
import { cn, formatCurrency } from "@/lib/utils"

export function RecentTransactions() {
  const openModal = useAppStore((s) => s.openModal)
  const { data, isLoading } = useTransactionSummary()
  const recent = data?.recent_transactions ?? []

  if (isLoading) {
    return (
      <Card className="rounded-2xl border-border/60 shadow-none">
        <CardHeader className="pb-2">
          <CardTitle className="text-[14px] font-semibold">Últimas transações</CardTitle>
        </CardHeader>
        <CardContent className="p-5">
          <p className="text-[13px] text-muted-foreground">Carregando...</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="rounded-2xl border-border/60 shadow-none">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-[14px] font-semibold">Últimas transações</CardTitle>
        <Link
          href="/transacoes"
          className="flex items-center gap-1 text-[11px] font-semibold text-muted-foreground hover:text-foreground"
        >
          Ver todas
          <ArrowRight className="h-3 w-3" />
        </Link>
      </CardHeader>
      <CardContent className="space-y-0 p-0">
        {recent.map((t) => {
          const cat = CATEGORIES.find((c) => c.name === t.category)
          return (
            <button
              key={t.id}
              onClick={() =>
                openModal("transaction-detail", {
                  id: t.id,
                  name: t.name,
                  category: t.category,
                  type: t.type === "INCOME" ? "receita" : "despesa",
                  amount: Math.abs(t.amount),
                  date: t.date,
                  source: t.source as "manual" | "auto" | "whatsapp",
                  status: t.status as "confirmed" | "pending",
                })
              }
              className="flex w-full items-center gap-3 border-b border-border/60 px-5 py-3 text-left transition-colors hover:bg-muted/50 last:border-0"
            >
              <span
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[16px]"
                style={{ backgroundColor: `${cat?.color}14` }}
              >
                {cat?.emoji}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13px] font-semibold">{t.name}</p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">
                  {t.category} · {t.date}
                  {t.source === "whatsapp" && " · via WhatsApp"}
                </p>
              </div>
              <div className="shrink-0 text-right">
                <p
                  className={cn(
                    "font-heading text-[14px] font-semibold tracking-tight",
                    t.type === "EXPENSE" ? "text-danger" : "text-success"
                  )}
                >
                  {t.type === "EXPENSE" ? "-" : "+"}
                  {formatCurrency(t.amount)}
                </p>
                {t.status === "pending" && (
                  <Badge className="mt-1 border-0 bg-warning/15 text-warning hover:bg-warning/25 [&]:text-[9px] [&]:px-1.5 [&]:py-0">
                    pendente
                  </Badge>
                )}
              </div>
            </button>
          )
        })}
        {recent.length === 0 && (
          <div className="px-5 py-8 text-center">
            <p className="text-[13px] text-muted-foreground">Nenhuma transação ainda</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
