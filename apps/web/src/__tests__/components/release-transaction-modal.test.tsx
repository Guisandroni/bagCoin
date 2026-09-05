import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { ReleaseTransactionDetailModal } from "@/components/release/transaction-detail-modal"
import type { ReleaseTransaction } from "@/components/release/types"

const transaction: ReleaseTransaction = {
  id: "1",
  name: "Supermercado",
  category: "Alimentação",
  categoryIcon: "shopping-cart",
  amount: 287.5,
  date: "09 mai",
  transactionDate: "2026-05-09",
  type: "despesa",
  source: "manual",
}

const categories = [
  {
    id: 1,
    name: "Alimentação",
    icon: "🍽️",
    color: "#ff9800",
    allocated: 0,
    type: "despesa" as const,
  },
]

describe("ReleaseTransactionDetailModal", () => {
  it("renderiza detalhes e salva campos editados", async () => {
    const onSave = vi.fn()
    const onDelete = vi.fn()
    const { container } = render(
      <ReleaseTransactionDetailModal
        open
        transaction={transaction}
        categories={categories}
        onOpenChange={() => {}}
        onSave={onSave}
        onDelete={onDelete}
      />
    )

    expect(screen.getByText("Detalhes da transação")).toBeInTheDocument()
    expect(screen.getByText("Supermercado")).toBeInTheDocument()
    expect(screen.getByText("09 de maio de 2026")).toBeInTheDocument()
    expect(screen.getByText("Não recorrente")).toBeInTheDocument()
    expect(container.innerHTML).toContain("z-[60]")
    expect(container.innerHTML).toContain("bottom-0")
    expect(container.innerHTML).toContain("w-[min(100%,28rem)]")
    expect(container.innerHTML).toContain("rounded-t-[12px]")
    expect(screen.getByText("Excluir")).toBeInTheDocument()
    expect(screen.getByText("Editar")).toBeInTheDocument()

    fireEvent.click(screen.getByText("Excluir"))
    expect(screen.getByText("Excluir transação?")).toBeInTheDocument()
    expect(screen.getByText("Esta ação não pode ser desfeita.")).toBeInTheDocument()
    expect(container.innerHTML).toContain("z-[70]")
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }))
    expect(screen.queryByText("Excluir transação?")).not.toBeInTheDocument()
    fireEvent.click(screen.getByText("Excluir"))
    fireEvent.click(screen.getAllByRole("button", { name: "Excluir" }).at(-1)!)
    expect(onDelete).toHaveBeenCalledWith(transaction)

    fireEvent.click(screen.getByText("Editar"))
    expect(screen.getByText("Salvar")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Alimentação/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByText("Ver categorias"))
    expect(screen.getByText("Ocultar categorias")).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Mercado atualizado" } })
    fireEvent.click(screen.getByLabelText("Transação recorrente"))
    expect(screen.getByText("Será repetida mensalmente.")).toBeInTheDocument()
    expect(screen.queryByText("Semanal")).not.toBeInTheDocument()
    expect(screen.queryByText("Anual")).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /Alimentação/ }))
    fireEvent.change(screen.getByLabelText("Valor"), { target: { value: "300,25" } })
    fireEvent.click(screen.getByLabelText("Data"))
    fireEvent.click(screen.getByRole("button", { name: "8" }))
    fireEvent.click(screen.getByText("Salvar"))

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith({
        id: "1",
        type: "EXPENSE",
        amount: 300.25,
        description: "Mercado atualizado",
        category_id: 1,
        category_name: "Alimentação",
        transaction_date: "2026-05-08",
        is_recurring: true,
        recurrence_frequency: "monthly",
      })
    })
  })
})
