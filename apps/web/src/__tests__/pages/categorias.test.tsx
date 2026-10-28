import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { CategoriasClient } from "@/app/app/categorias/categorias-client"
import type { ReleaseCategory } from "@/components/release/types"
import type { ReactNode } from "react"

const mockCategories: ReleaseCategory[] = [
  {
    name: "Alimentação",
    icon: "🍔",
    color: "#ff9800",
    allocated: 404.1,
    percentage: 67,
    type: "despesa",
    isFixed: true,
    isUserCreated: false,
    canDelete: false,
  },
  {
    name: "Salário",
    icon: "💰",
    color: "#22c55e",
    allocated: 0,
    percentage: 0,
    type: "receita",
    isFixed: true,
    isUserCreated: false,
    canDelete: false,
  },
  {
    name: "Investimentos",
    icon: "📈",
    color: "#3f51b5",
    allocated: 0,
    percentage: 0,
    type: "investimento",
    isFixed: true,
    isUserCreated: false,
    canDelete: false,
  },
  {
    id: 99,
    name: "Colecionáveis",
    icon: "💳",
    color: "#1652f0",
    allocated: 0,
    percentage: 0,
    type: "despesa",
    isFixed: false,
    isUserCreated: true,
    canDelete: true,
  },
]

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn(), prefetch: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/app/categorias",
}))

vi.mock("@/hooks/use-categories", () => ({
  useCreateCategory: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateCategory: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteCategory: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), dismiss: vi.fn() },
}))

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

describe("CategoriasClient", () => {
  it("renderiza header funcional de categorias", () => {
    render(
      <CategoriasClient categories={mockCategories} totalAllocated={404.1} />,
      { wrapper: createWrapper() }
    )

    expect(screen.getByRole("heading", { name: "Categorias" })).toBeInTheDocument()
    expect(screen.getByText("Adicionar Categoria")).toBeInTheDocument()
    expect(screen.getByLabelText("Abrir menu")).toBeInTheDocument()
  })

  it("abre modal ao clicar em Adicionar Categoria", () => {
    render(
      <CategoriasClient categories={mockCategories} totalAllocated={404.1} />,
      { wrapper: createWrapper() }
    )

    fireEvent.click(screen.getByText("Adicionar Categoria"))

    expect(screen.getByText("Nova Categoria")).toBeInTheDocument()
    expect(screen.getByText("Organize seus lançamentos")).toBeInTheDocument()
  })

  it("filtra categorias por tipo", () => {
    render(
      <CategoriasClient categories={mockCategories} totalAllocated={404.1} />,
      { wrapper: createWrapper() }
    )

    fireEvent.click(screen.getByText("Receitas"))

    expect(screen.getByText("Salário")).toBeInTheDocument()
    expect(screen.queryByText("Alimentação")).not.toBeInTheDocument()
  })

  it("filtra categorias criadas pelo usuário", () => {
    render(
      <CategoriasClient categories={mockCategories} totalAllocated={404.1} />,
      { wrapper: createWrapper() }
    )

    fireEvent.click(screen.getByText("Criadas"))

    expect(screen.getByText("Colecionáveis")).toBeInTheDocument()
    expect(screen.queryByText("Alimentação")).not.toBeInTheDocument()
    expect(screen.queryByText("Salário")).not.toBeInTheDocument()
  })

  it("exibe e filtra categorias de investimento", () => {
    render(
      <CategoriasClient categories={mockCategories} totalAllocated={404.1} />,
      { wrapper: createWrapper() }
    )

    expect(screen.getAllByText("Investimentos").length).toBeGreaterThan(0)

    fireEvent.click(screen.getAllByText("Investimentos")[0])

    expect(screen.getByText("Investimento")).toBeInTheDocument()
    expect(screen.queryByText("Alimentação")).not.toBeInTheDocument()
    expect(screen.queryByText("Salário")).not.toBeInTheDocument()
  })

  it("bloqueia categoria duplicada inline e remove investimento da criação", () => {
    render(
      <CategoriasClient categories={mockCategories} totalAllocated={404.1} />,
      { wrapper: createWrapper() }
    )

    fireEvent.click(screen.getByText("Adicionar Categoria"))
    expect(screen.queryByRole("button", { name: "Investimento" })).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText("Nome da Categoria"), {
      target: { value: "alimentacao" },
    })

    expect(screen.getByText('Categoria "alimentacao" já existe.')).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Salvar" })).toBeDisabled()
  })

  it("categoria padrão é somente visualização e categoria criada permite editar", () => {
    render(
      <CategoriasClient categories={mockCategories} totalAllocated={404.1} />,
      { wrapper: createWrapper() }
    )

    fireEvent.click(screen.getByText("Alimentação"))
    expect(screen.getByText("Detalhes da categoria")).toBeInTheDocument()
    expect(screen.queryByText("Editar")).not.toBeInTheDocument()
    expect(screen.getByText("Categoria padrão do sistema")).toBeInTheDocument()

    fireEvent.click(screen.getByLabelText("Fechar"))
    fireEvent.click(screen.getByText("Colecionáveis"))
    expect(screen.getByText("Editar")).toBeInTheDocument()
    expect(screen.getByText("Excluir")).toBeInTheDocument()
  })
})
