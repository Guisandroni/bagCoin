export const BRAND = {
  pre: "bag",
  suf: "Coin",
}

export const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: "LayoutGrid" },
  { id: "transacoes", label: "Transações", icon: "List" },
  { id: "orcamentos", label: "Orçamentos", icon: "Wallet" },
  { id: "metas", label: "Metas", icon: "Target" },
  { id: "categorias", label: "Categorias", icon: "LayoutGrid" },
  { id: "confirmacoes", label: "Confirmações", icon: "MessageSquare" },
]

/** Bottom bar: Início, Transações, Orçamentos, Metas, Categorias */
export const MOBILE_NAV_ITEMS = [
  { id: "dashboard", label: "Início", icon: "Home" },
  { id: "transacoes", label: "Transações", icon: "List" },
  { id: "orcamentos", label: "Orçamentos", icon: "Wallet" },
  { id: "metas", label: "Metas", icon: "Target" },
  { id: "categorias", label: "Categorias", icon: "LayoutGrid" },
]

/** DialogContent: anchor to bottom on small screens (sheet-like) */
export const DIALOG_SHEET_MOBILE =
  "max-sm:fixed max-sm:inset-x-0 max-sm:bottom-0 max-sm:top-auto max-sm:left-0 max-sm:max-h-[min(92dvh,800px)] max-sm:max-w-full max-sm:translate-x-0 max-sm:translate-y-0 max-sm:overflow-y-auto max-sm:rounded-b-none max-sm:rounded-t-2xl"

export { CATEGORY_LIST, CATEGORIES_WITH_EMOJI, EXPENSE_CATEGORIES, INCOME_CATEGORIES, CATEGORIES } from "@/lib/category"

export const PERIODS = [
  { value: "monthly", label: "Mensal" },
]

export const SOURCE_LABELS: Record<string, string> = {
  text: "Texto",
  audio: "Áudio",
  image: "Imagem",
  document: "Documento",
  api: "API",
}

export const STATUS_LABELS: Record<string, string> = {
  confirmed: "Confirmado",
  pending: "Pendente",
  cancelled: "Cancelado",
}
