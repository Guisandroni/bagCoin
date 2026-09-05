"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { CATEGORIES, DIALOG_SHEET_MOBILE, SOURCE_LABELS, STATUS_LABELS } from "@/lib/constants"
import { useAppStore } from "@/lib/store"
import { useDeleteTransaction, useUpdateTransaction } from "@/hooks/use-transactions"
import { cn, formatCurrency } from "@/lib/utils"
import { MessageSquare } from "lucide-react"
import { toast } from "sonner"

export function TransactionDetailModal() {
  const { activeModal, selectedTransaction: t, closeModal } = useAppStore()
  const deleteMutation = useDeleteTransaction()
  const updateMutation = useUpdateTransaction()
  const open = activeModal === "transaction-detail" && !!t
  const [mode, setMode] = useState<"view" | "edit">("view")
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [editType, setEditType] = useState<"despesa" | "receita">("despesa")
  const [editAmount, setEditAmount] = useState("")
  const [editDescription, setEditDescription] = useState("")
  const [editCategory, setEditCategory] = useState("")
  const [editDate, setEditDate] = useState("2026-05-01")

  if (!t) return null

  const cat = CATEGORIES.find((c) => c.name === t.category)
  const isExpense = t.type === "despesa"
  const signedAmount = isExpense ? -Math.abs(t.amount) : Math.abs(t.amount)

  function handleEdit() {
    setMode("edit")
    setEditType(t!.type)
    setEditAmount(formatCurrency(Math.abs(t!.amount)).replace("R$ ", ""))
    setEditDescription(t!.name)
    setEditCategory(t!.category)
  }

  async function handleSaveEdit() {
    const cleanAmount = editAmount.replace(/[^\d,]/g, "").replace(",", ".")
    const amount = Number.parseFloat(cleanAmount) || 0

    try {
      await updateMutation.mutateAsync({
        id: t!.id,
        type: editType === "receita" ? "INCOME" : "EXPENSE",
        amount,
        description: editDescription,
        category_name: editCategory,
        transaction_date: editDate,
      })
      setMode("view")
      closeModal()
      toast.success("Transação atualizada com sucesso!")
    } catch {
      toast.error("Erro ao atualizar transação. Tente novamente.")
    }
  }

  async function handleDelete() {
    try {
      await deleteMutation.mutateAsync(t!.id)
      setShowDeleteConfirm(false)
      closeModal()
      toast.success("Transação excluída com sucesso!")
    } catch {
      toast.error("Erro ao excluir transação. Tente novamente.")
    }
  }

  if (showDeleteConfirm) {
    return (
      <Dialog open={open} onOpenChange={() => { setShowDeleteConfirm(false); closeModal() }}>
        <DialogContent className={cn("max-w-md rounded-2xl", DIALOG_SHEET_MOBILE)}>
          <DialogHeader>
            <DialogTitle className="font-heading">Excluir transação</DialogTitle>
          </DialogHeader>
          <div className="rounded-xl border border-danger/30 bg-danger/5 px-4 py-4 text-center">
            <p className="font-semibold">Tem certeza que deseja excluir esta transação?</p>
            <p className="mt-1 text-[13px] text-muted-foreground">
              {t.name} — {formatCurrency(signedAmount)}
            </p>
            <p className="mt-1 text-[12px] text-muted-foreground">
              Essa ação não pode ser desfeita.
            </p>
          </div>
          <DialogFooter className="gap-2">
            <Button variant="secondary" size="sm" onClick={() => setShowDeleteConfirm(false)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Excluindo..." : "Excluir permanentemente"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    )
  }

  if (mode === "edit") {
    const filteredCategories = editType === "despesa"
      ? CATEGORIES.filter((c) => c.name !== "Salário")
      : CATEGORIES.filter((c) => c.name === "Salário" || c.name === "Educação")

    return (
      <Dialog open={open} onOpenChange={(v) => !v && closeModal()}>
        <DialogContent className={cn("max-w-md rounded-2xl", DIALOG_SHEET_MOBILE)}>
          <DialogHeader>
            <DialogTitle className="font-heading">Editar transação</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="flex overflow-hidden rounded-xl border border-border">
              <button
                className={cn(
                  "flex-1 py-2.5 text-[14px] font-semibold",
                  editType === "despesa" ? "bg-danger/10 text-danger" : ""
                )}
                onClick={() => setEditType("despesa")}
              >
                Despesa
              </button>
              <button
                className={cn(
                  "flex-1 py-2.5 text-[14px] font-semibold",
                  editType === "receita" ? "bg-success/10 text-success" : ""
                )}
                onClick={() => setEditType("receita")}
              >
                Receita
              </button>
            </div>
            <div className="space-y-1.5">
              <Label className="text-[11px] uppercase tracking-[0.05em] font-semibold">Valor</Label>
              <Input
                type="text"
                value={editAmount}
                onChange={(e) => setEditAmount(e.target.value)}
                className="font-heading"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-[11px] uppercase tracking-[0.05em] font-semibold">Descrição</Label>
              <Input
                type="text"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-[11px] uppercase tracking-[0.05em] font-semibold">Categoria</Label>
              <select
                value={editCategory}
                onChange={(e) => setEditCategory(e.target.value)}
                className="flex h-10 w-full rounded-xl border border-border bg-card px-3 text-[14px]"
              >
                {filteredCategories.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.emoji} {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-[11px] uppercase tracking-[0.05em] font-semibold">Data</Label>
              <Input
                type="date"
                value={editDate}
                onChange={(e) => setEditDate(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter className="gap-2">
            <Button variant="secondary" size="sm" onClick={() => setMode("view")}>Cancelar</Button>
            <Button size="sm" onClick={handleSaveEdit} disabled={updateMutation.isPending}>
              {updateMutation.isPending ? "Salvando..." : "Salvar alterações"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && closeModal()}>
      <DialogContent className={cn("max-w-md rounded-2xl", DIALOG_SHEET_MOBILE)}>
        <DialogHeader>
          <DialogTitle className="font-heading">Detalhes da transação</DialogTitle>
        </DialogHeader>

        <div className="flex items-center gap-3 rounded-xl bg-muted/80 p-4">
          <span
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-2xl"
            style={{ backgroundColor: `${cat?.color}18` }}
          >
            {cat?.emoji}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[16px] font-semibold">{t.name}</p>
            <p className="mt-0.5 text-[13px] text-muted-foreground">
              {t.category} · {t.date}
            </p>
          </div>
          <p
            className={cn(
              "font-heading text-[22px] font-semibold tracking-tight",
              isExpense ? "text-danger" : "text-success"
            )}
          >
            {formatCurrency(signedAmount)}
          </p>
        </div>

        {t.source === "whatsapp" && (
          <div className="flex items-center gap-2 rounded-lg bg-[#25d366]/8 px-3.5 py-2.5">
            <div className="flex h-5 w-5 items-center justify-center rounded bg-[#25d366]">
              <MessageSquare className="h-3 w-3 text-white" />
            </div>
            <span className="text-[13px] font-semibold text-[#25d366]">
              Origem: WhatsApp
            </span>
          </div>
        )}

        <div className="divide-y divide-border">
          {[
            { label: "Valor", value: formatCurrency(signedAmount), className: isExpense ? "text-danger" : "text-success" },
            {
              label: "Categoria",
              value: (
                <span
                  className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[12px] font-semibold"
                  style={{ backgroundColor: `${cat?.color}18`, color: cat?.color }}
                >
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: cat?.color }} />
                  {t.category}
                </span>
              ),
            },
            { label: "Data", value: `${t.date} 2026` },
            { label: "Origem", value: SOURCE_LABELS[t.source] || t.source },
            {
              label: "Status",
              value: (
                <Badge
                  className={cn(
                    "border-0",
                    t.status === "pending"
                      ? "bg-warning/15 text-warning"
                      : "bg-success/15 text-success"
                  )}
                >
                  {STATUS_LABELS[t.status]}
                </Badge>
              ),
            },
          ].map((row) => (
            <div key={row.label} className="flex items-center justify-between py-3">
              <span className="text-[12px] font-semibold uppercase tracking-[0.05em] text-muted-foreground">
                {row.label}
              </span>
              <span className={cn("text-[14px] font-medium", row.className)}>
                {row.value}
              </span>
            </div>
          ))}
        </div>

        <DialogFooter className="gap-2">
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setShowDeleteConfirm(true)}
          >
            Excluir
          </Button>
          <Button variant="secondary" size="sm" onClick={handleEdit}>
            Editar
          </Button>
          <Button size="sm" onClick={closeModal}>
            Fechar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
