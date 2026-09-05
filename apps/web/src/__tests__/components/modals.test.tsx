import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { NewTransactionModal } from "@/components/modals/new-transaction-modal"
import { TransactionDetailModal } from "@/components/modals/transaction-detail-modal"
import { FilterModal } from "@/components/modals/filter-modal"
import { CATEGORIES } from "@/lib/constants"

const mockCloseModal = vi.fn()
const mockOpenModal = vi.fn()
const mockSetFilter = vi.fn()

type StoreState = {
  activeModal: "new-transaction" | "transaction-detail" | "filter" | null
  selectedTransaction: typeof sampleTransaction | null
  closeModal: typeof mockCloseModal
  openModal: typeof mockOpenModal
  setFilter: typeof mockSetFilter
  filter: { type: "all"; categories: string[]; searchQuery: string }
}
type StoreSelector<T = unknown> = (state: StoreState) => T

const mockUseAppStore = vi.hoisted(() => ({
  useAppStore: (selector?: StoreSelector) => {
    const state: StoreState = {
      activeModal: null,
      selectedTransaction: null,
      closeModal: mockCloseModal,
      openModal: mockOpenModal,
      setFilter: mockSetFilter,
      filter: { type: "all", categories: CATEGORIES.map((c) => c.name), searchQuery: "" },
    }
    return selector ? selector(state) : state
  },
}))

vi.mock("@/lib/store", () => mockUseAppStore)

const mockMutateAsync = vi.fn()
const mockIsPending = false

vi.mock("@/hooks/use-transactions", () => ({
  useCreateTransaction: () => ({
    mutateAsync: mockMutateAsync,
    isPending: mockIsPending,
  }),
  useUpdateTransaction: () => ({
    mutateAsync: mockMutateAsync,
    isPending: mockIsPending,
  }),
  useDeleteTransaction: () => ({
    mutateAsync: mockMutateAsync,
    isPending: mockIsPending,
  }),
  useTransactionSummary: () => ({
    data: null,
    isLoading: true,
  }),
}))

vi.mock("next/navigation", () => ({
  usePathname: () => "/app",
}))

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

const sampleTransaction = {
  id: "1",
  name: "Supermercado Pão de Açúcar",
  category: "Alimentação",
  type: "despesa" as const,
  amount: 287.5,
  date: "30 Abr",
  source: "manual" as const,
  status: "confirmed" as const,
}

describe("NewTransactionModal", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("não renderiza quando activeModal não é 'new-transaction'", () => {
    mockUseAppStore.useAppStore = () => ({
      activeModal: null,
      selectedTransaction: null,
      closeModal: mockCloseModal,
      openModal: mockOpenModal,
      setFilter: mockSetFilter,
      filter: { type: "all", categories: CATEGORIES.map((c) => c.name), searchQuery: "" },
    })

    const { container } = render(<NewTransactionModal />)
    expect(container.textContent).toBe("")
  })

  it("renderiza titulo e campos quando modal está aberto", () => {
    mockUseAppStore.useAppStore = () => ({
      activeModal: "new-transaction",
      selectedTransaction: null,
      closeModal: mockCloseModal,
      openModal: mockOpenModal,
      setFilter: mockSetFilter,
      filter: { type: "all", categories: CATEGORIES.map((c) => c.name), searchQuery: "" },
    })

    render(<NewTransactionModal />)
    expect(screen.getByText("Novo lançamento")).toBeInTheDocument()
    expect(screen.getByText("Despesa")).toBeInTheDocument()
    expect(screen.getByText("Receita")).toBeInTheDocument()
    expect(screen.getByText("Valor")).toBeInTheDocument()
    expect(screen.getByText("Categoria")).toBeInTheDocument()
    expect(screen.getByText("Descrição")).toBeInTheDocument()
    expect(screen.getByText("Data")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /registrar despesa/i })).toBeInTheDocument()
  })

  it("submit chama createMutation com dados do formulario", async () => {
    mockMutateAsync.mockResolvedValueOnce({ id: "99" })

    mockUseAppStore.useAppStore = () => ({
      activeModal: "new-transaction",
      selectedTransaction: null,
      closeModal: mockCloseModal,
      openModal: mockOpenModal,
      setFilter: mockSetFilter,
      filter: { type: "all", categories: CATEGORIES.map((c) => c.name), searchQuery: "" },
    })

    render(<NewTransactionModal />)

    fireEvent.change(screen.getByPlaceholderText("R$ 0,00"), {
      target: { value: "150,00" },
    })

    fireEvent.change(screen.getByDisplayValue("2026-05-01"), {
      target: { value: "2026-05-15" },
    })

    fireEvent.click(screen.getByRole("button", { name: /registrar despesa/i }))

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "EXPENSE",
          amount: 150,
          source: "manual",
        })
      )
    })

    expect(mockCloseModal).toHaveBeenCalled()
  })

  it("altera para receita e mostra botao correto", () => {
    mockUseAppStore.useAppStore = () => ({
      activeModal: "new-transaction",
      selectedTransaction: null,
      closeModal: mockCloseModal,
      openModal: mockOpenModal,
      setFilter: mockSetFilter,
      filter: { type: "all", categories: CATEGORIES.map((c) => c.name), searchQuery: "" },
    })

    render(<NewTransactionModal />)
    fireEvent.click(screen.getByText("Receita"))
    expect(screen.getByRole("button", { name: /registrar receita/i })).toBeInTheDocument()
  })
})

describe("TransactionDetailModal", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("não renderiza quando selectedTransaction é null", () => {
    mockUseAppStore.useAppStore = () => ({
      activeModal: "transaction-detail",
      selectedTransaction: null,
      closeModal: mockCloseModal,
      openModal: mockOpenModal,
      setFilter: mockSetFilter,
      filter: { type: "all", categories: CATEGORIES.map((c) => c.name), searchQuery: "" },
    })

    const { container } = render(<TransactionDetailModal />)
    expect(container.textContent).toBe("")
  })

  it("renderiza em modo view com detalhes da transacao", () => {
    mockUseAppStore.useAppStore = () => ({
      activeModal: "transaction-detail",
      selectedTransaction: sampleTransaction,
      closeModal: mockCloseModal,
      openModal: mockOpenModal,
      setFilter: mockSetFilter,
      filter: { type: "all", categories: CATEGORIES.map((c) => c.name), searchQuery: "" },
    })

    render(<TransactionDetailModal />)
    expect(screen.getByText("Detalhes da transação")).toBeInTheDocument()
    expect(screen.getByText(sampleTransaction.name)).toBeInTheDocument()
    const alimentacaoElements = screen.getAllByText(/Alimentação/)
    expect(alimentacaoElements.length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("Excluir")).toBeInTheDocument()
    expect(screen.getByText("Editar")).toBeInTheDocument()
    expect(screen.getByText("Fechar")).toBeInTheDocument()
  })

  it("renderiza modo edit ao clicar em Editar", () => {
    mockUseAppStore.useAppStore = () => ({
      activeModal: "transaction-detail",
      selectedTransaction: sampleTransaction,
      closeModal: mockCloseModal,
      openModal: mockOpenModal,
      setFilter: mockSetFilter,
      filter: { type: "all", categories: CATEGORIES.map((c) => c.name), searchQuery: "" },
    })

    render(<TransactionDetailModal />)
    fireEvent.click(screen.getByText("Editar"))
    expect(screen.getByText("Editar transação")).toBeInTheDocument()
    expect(screen.getByText("Salvar alterações")).toBeInTheDocument()
  })

  it("renderiza confirmacao de delete ao clicar em Excluir", () => {
    mockUseAppStore.useAppStore = () => ({
      activeModal: "transaction-detail",
      selectedTransaction: sampleTransaction,
      closeModal: mockCloseModal,
      openModal: mockOpenModal,
      setFilter: mockSetFilter,
      filter: { type: "all", categories: CATEGORIES.map((c) => c.name), searchQuery: "" },
    })

    render(<TransactionDetailModal />)
    fireEvent.click(screen.getByText("Excluir"))
    expect(screen.getByText("Excluir transação")).toBeInTheDocument()
    expect(screen.getByText(/Tem certeza/)).toBeInTheDocument()
    expect(screen.getByText("Excluir permanentemente")).toBeInTheDocument()
  })

  it("chama deleteMutation ao confirmar exclusao", async () => {
    mockMutateAsync.mockResolvedValueOnce(undefined)

    mockUseAppStore.useAppStore = () => ({
      activeModal: "transaction-detail",
      selectedTransaction: sampleTransaction,
      closeModal: mockCloseModal,
      openModal: mockOpenModal,
      setFilter: mockSetFilter,
      filter: { type: "all", categories: CATEGORIES.map((c) => c.name), searchQuery: "" },
    })

    render(<TransactionDetailModal />)
    fireEvent.click(screen.getByText("Excluir"))
    fireEvent.click(screen.getByText("Excluir permanentemente"))

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith("1")
    })
  })
})

describe("FilterModal", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("não renderiza quando activeModal não é 'filter'", () => {
    mockUseAppStore.useAppStore = () => ({
      activeModal: null,
      selectedTransaction: null,
      closeModal: mockCloseModal,
      openModal: mockOpenModal,
      setFilter: mockSetFilter,
      filter: { type: "all", categories: CATEGORIES.map((c) => c.name), searchQuery: "" },
    })

    const { container } = render(<FilterModal />)
    expect(container.textContent).toBe("")
  })

  it("renderiza opcoes de tipo e categorias", () => {
    mockUseAppStore.useAppStore = () => ({
      activeModal: "filter",
      selectedTransaction: null,
      closeModal: mockCloseModal,
      openModal: mockOpenModal,
      setFilter: mockSetFilter,
      filter: { type: "all", categories: CATEGORIES.map((c) => c.name), searchQuery: "" },
    })

    render(<FilterModal />)
    expect(screen.getByText("Filtros")).toBeInTheDocument()
    expect(screen.getByText("Tipo de transação")).toBeInTheDocument()
    expect(screen.getByText("Todas")).toBeInTheDocument()
    expect(screen.getByText("Despesas")).toBeInTheDocument()
    expect(screen.getByText("Receitas")).toBeInTheDocument()
    expect(screen.getByText("Categorias")).toBeInTheDocument()
    expect(screen.getByText("Aplicar filtros")).toBeInTheDocument()
    expect(screen.getByText("Limpar")).toBeInTheDocument()
  })

  it("renderiza categorias do CATEGORIES", () => {
    mockUseAppStore.useAppStore = () => ({
      activeModal: "filter",
      selectedTransaction: null,
      closeModal: mockCloseModal,
      openModal: mockOpenModal,
      setFilter: mockSetFilter,
      filter: { type: "all", categories: CATEGORIES.map((c) => c.name), searchQuery: "" },
    })

    render(<FilterModal />)
    CATEGORIES.forEach((c) => {
      const elements = screen.getAllByText(new RegExp(c.name))
      expect(elements.length).toBeGreaterThanOrEqual(1)
    })
  })

  it("chama setFilter e closeModal ao aplicar filtros", () => {
    mockUseAppStore.useAppStore = () => ({
      activeModal: "filter",
      selectedTransaction: null,
      closeModal: mockCloseModal,
      openModal: mockOpenModal,
      setFilter: mockSetFilter,
      filter: { type: "all", categories: CATEGORIES.map((c) => c.name), searchQuery: "" },
    })

    render(<FilterModal />)
    fireEvent.click(screen.getByText("Aplicar filtros"))

    expect(mockSetFilter).toHaveBeenCalledWith({
      type: "all",
      categories: CATEGORIES.map((c) => c.name),
    })
    expect(mockCloseModal).toHaveBeenCalled()
  })
})
