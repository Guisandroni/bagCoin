export type TransactionSource = "whatsapp" | "auto" | "manual"
export type TransactionStatus = "confirmed" | "pending"
export type TransactionType = "despesa" | "receita"

export interface Category {
  name: string
  color: string
  emoji: string
}

export interface Transaction {
  id: string
  name: string
  category: string
  type: TransactionType
  amount: number
  date: string
  source: TransactionSource
  status: TransactionStatus
}

export interface Account {
  id: string
  name: string
  bank: string
  balance: number
  icon: string
}

export interface Card {
  id: string
  name: string
  last4: string
  limit: number
  used: number
  closingDay: number
  dueDay: number
  color: string
}

export interface Goal {
  id: string
  name: string
  target: number
  current: number
  deadline: string
  color: string
}

export interface Budget {
  category: string
  budget: number
  spent: number
  color: string
}

export interface Report {
  id: string
  name: string
  period: string
  date: string
  size: string
  type: "full" | "expenses" | "quarterly" | "comparison"
}

export type ModalType = "new-transaction" | "transaction-detail" | "filter" | null

export interface FilterState {
  type: "all" | "despesa" | "receita"
  categories: string[]
  searchQuery: string
}
