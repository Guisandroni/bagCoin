import { describe, it, expect, beforeEach } from "vitest"
import { useAppStore } from "@/lib/store"
import type { Transaction } from "@/types"

const mockTransaction: Transaction = {
  id: "1",
  name: "Supermercado Pão de Açúcar",
  category: "Alimentação",
  type: "despesa",
  amount: 287.5,
  date: "30 Abr",
  source: "manual",
  status: "confirmed",
}

beforeEach(() => {
  useAppStore.setState({
    transactions: [],
    activeModal: null,
    selectedTransaction: null,
    filter: {
      type: "all",
      categories: [
        "Alimentação",
        "Transporte",
        "Moradia",
        "Saúde",
        "Lazer",
        "Educação",
        "Compras",
        "Salário",
      ],
      searchQuery: "",
    },
  })
})

describe("Zustand Store — Estado Inicial", () => {
  it("activeModal deve ser null", () => {
    const { activeModal } = useAppStore.getState()
    expect(activeModal).toBeNull()
  })

  it("selectedTransaction deve ser null", () => {
    const { selectedTransaction } = useAppStore.getState()
    expect(selectedTransaction).toBeNull()
  })

  it("transactions deve ser array vazio", () => {
    const { transactions } = useAppStore.getState()
    expect(transactions).toHaveLength(0)
  })

  it("filter type deve ser 'all'", () => {
    const { filter } = useAppStore.getState()
    expect(filter.type).toBe("all")
    expect(filter.categories).toHaveLength(8)
    expect(filter.searchQuery).toBe("")
  })
})

describe("Zustand Store — openModal", () => {
  it("com transacao: seta activeModal + selectedTransaction", () => {
    useAppStore.getState().openModal("transaction-detail", mockTransaction)

    const state = useAppStore.getState()
    expect(state.activeModal).toBe("transaction-detail")
    expect(state.selectedTransaction).toEqual(mockTransaction)
  })

  it("sem transacao: seta activeModal, selectedTransaction = null", () => {
    useAppStore.getState().openModal("new-transaction")

    const state = useAppStore.getState()
    expect(state.activeModal).toBe("new-transaction")
    expect(state.selectedTransaction).toBeNull()
  })

  it("com transacao undefined: selectedTransaction fica null", () => {
    useAppStore.getState().openModal("filter", undefined)

    const state = useAppStore.getState()
    expect(state.activeModal).toBe("filter")
    expect(state.selectedTransaction).toBeNull()
  })
})

describe("Zustand Store — closeModal", () => {
  it("reseta activeModal e selectedTransaction para null", () => {
    // primeiro abre um modal
    useAppStore.getState().openModal("transaction-detail", mockTransaction)
    expect(useAppStore.getState().activeModal).toBe("transaction-detail")
    expect(useAppStore.getState().selectedTransaction).toEqual(mockTransaction)

    // depois fecha
    useAppStore.getState().closeModal()

    const state = useAppStore.getState()
    expect(state.activeModal).toBeNull()
    expect(state.selectedTransaction).toBeNull()
  })
})

describe("Zustand Store — setFilter", () => {
  it("merge parcial: muda type, mantem categories", () => {
    useAppStore.getState().setFilter({ type: "despesa" })

    const state = useAppStore.getState()
    expect(state.filter.type).toBe("despesa")
    // categories devem ser mantidas
    expect(state.filter.categories).toEqual([
      "Alimentação",
      "Transporte",
      "Moradia",
      "Saúde",
      "Lazer",
      "Educação",
      "Compras",
      "Salário",
    ])
    expect(state.filter.searchQuery).toBe("")
  })

  it("replace completo: sobrescreve filtro", () => {
    useAppStore.getState().setFilter({
      type: "receita",
      categories: ["Salário"],
      searchQuery: "salario",
    })

    const state = useAppStore.getState()
    expect(state.filter.type).toBe("receita")
    expect(state.filter.categories).toEqual(["Salário"])
    expect(state.filter.searchQuery).toBe("salario")
  })
})

describe("Zustand Store — resetFilter", () => {
  it("volta ao filtro default", () => {
    // altera o filtro primeiro
    useAppStore.getState().setFilter({
      type: "receita",
      categories: ["Salário"],
      searchQuery: "salario",
    })

    // reseta
    useAppStore.getState().resetFilter()

    const state = useAppStore.getState()
    expect(state.filter.type).toBe("all")
    expect(state.filter.categories).toHaveLength(8)
    expect(state.filter.categories).toContain("Alimentação")
    expect(state.filter.categories).toContain("Salário")
    expect(state.filter.searchQuery).toBe("")
  })
})

describe("Zustand Store — setTransactions", () => {
  it("atualiza lista de transacoes", () => {
    const transactions = [mockTransaction, { ...mockTransaction, id: "2", name: "Salário" }]

    useAppStore.getState().setTransactions(transactions)

    const state = useAppStore.getState()
    expect(state.transactions).toHaveLength(2)
    expect(state.transactions[0].id).toBe("1")
    expect(state.transactions[1].name).toBe("Salário")
  })

  it("substitui lista anterior", () => {
    // primeira lista
    useAppStore.getState().setTransactions([mockTransaction])
    expect(useAppStore.getState().transactions).toHaveLength(1)

    // segunda lista substitui
    useAppStore.getState().setTransactions([])
    expect(useAppStore.getState().transactions).toHaveLength(0)
  })
})
