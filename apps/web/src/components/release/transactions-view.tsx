"use client"

import { useEffect, useState } from "react"
import { ChevronLeft, ChevronRight, Search, X } from "lucide-react"
import { FilterChips } from "./filter-chips"
import { PillInput } from "./pill-input"
import { BottomNavBar } from "./bottom-nav-bar"
import { FunctionHeader } from "./function-header"
import { cn } from "@/lib/utils"
import { CategoryIcon } from "@/lib/category"
import type { ReleaseTransaction, ReleaseFilterPeriod, ReleaseNavItem } from "./types"
import { formatCurrency } from "./format"

type ReleaseTransactionTypeFilter = "all" | "expense" | "income"

const MONTH_OPTIONS = Array.from({ length: 12 }, (_, month) => ({
  value: month,
  label: new Intl.DateTimeFormat("pt-BR", { month: "long" }).format(new Date(2026, month, 1)),
}))
const PRERENDER_SAFE_DATE = new Date(2000, 0, 1)

interface TransactionsViewProps {
  transactions: ReleaseTransaction[]
  totalSpent?: number
  totalReceived?: number
  navItems: ReleaseNavItem[]
  onNavigate: (href: string) => void
  onSearch?: (query: string) => void
  onSelectTransaction?: (transaction: ReleaseTransaction) => void
  onAddTransaction?: () => void
  currentDate?: Date
}

export function TransactionsView({
  transactions,
  navItems,
  onNavigate,
  onSelectTransaction,
  onAddTransaction,
  currentDate,
}: TransactionsViewProps) {
  const [resolvedCurrentDate, setResolvedCurrentDate] = useState(
    () => currentDate ?? PRERENDER_SAFE_DATE
  )
  const [activeFilter, setActiveFilter] = useState<ReleaseFilterPeriod>("todo")
  const [typeFilter, setTypeFilter] = useState<ReleaseTransactionTypeFilter>("all")
  const [searchQuery, setSearchQuery] = useState("")
  const [calendarOpen, setCalendarOpen] = useState(false)
  const [selectedCalendarDate, setSelectedCalendarDate] = useState<string>("")
  const [calendarMonth, setCalendarMonth] = useState(
    () => new Date(resolvedCurrentDate.getFullYear(), resolvedCurrentDate.getMonth(), 1)
  )

  useEffect(() => {
    const nextDate = currentDate ?? new Date()
    queueMicrotask(() => {
      setResolvedCurrentDate(nextDate)
      setCalendarMonth(new Date(nextDate.getFullYear(), nextDate.getMonth(), 1))
    })
  }, [currentDate])

  const filterOptions: { label: string; value: ReleaseFilterPeriod }[] = [
    { label: "Todas", value: "todo" },
    { label: "Por semana", value: "week" },
    { label: "Por mês", value: "month" },
    { label: "Calendário", value: "calendar" },
  ]

  const typeFilterOptions: { label: string; value: ReleaseTransactionTypeFilter }[] = [
    { label: "Todas", value: "all" },
    { label: "Despesas", value: "expense" },
    { label: "Receitas", value: "income" },
  ]

  const filteredTransactions = transactions.filter((tx) => {
    const query = normalizeSearch(searchQuery)
    const matchesSearch = query
      ? normalizeSearch(tx.name).includes(query) || normalizeSearch(tx.category).includes(query)
      : true
    if (!matchesSearch) return false
    if (!matchesType(tx.type, typeFilter)) return false
    return matchesPeriod(tx.transactionDate, activeFilter, resolvedCurrentDate, selectedCalendarDate)
  })

  const totalFilteredExpenses = filteredTransactions
    .filter((tx) => tx.type === "despesa")
    .reduce((sum, tx) => sum + Math.abs(tx.amount), 0)

  const totalFilteredIncome = filteredTransactions
    .filter((tx) => tx.type === "receita")
    .reduce((sum, tx) => sum + Math.abs(tx.amount), 0)

  const transactionDates = new Set(
    transactions
      .map((tx) => tx.transactionDate)
      .filter((value): value is string => Boolean(value))
  )

  const grouped = filteredTransactions.reduce<Record<string, ReleaseTransaction[]>>(
    (acc, tx) => {
      const group = getGroupLabel(tx, activeFilter, resolvedCurrentDate)
      if (!acc[group]) acc[group] = []
      acc[group].push(tx)
      return acc
    },
    {}
  )

  return (
    <div className="rls mx-auto min-h-dvh w-full max-w-md bg-[var(--rls-background)] shadow-[0_0_48px_rgba(22,82,240,0.08)]">
      <FunctionHeader
        title="Transações"
        actionLabel="Adicionar Transação"
        onAction={onAddTransaction ?? (() => {})}
      />

      <main className="px-[var(--rls-container-margin)] flex flex-col gap-[var(--rls-stack-gap-md)] pt-[var(--rls-stack-gap-sm)] pb-[120px]">
        {/* Search Bar */}
        <PillInput
          icon={<Search className="w-5 h-5" />}
          placeholder="Buscar transações..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />

        {/* Filter Chips */}
        <div className="flex flex-col gap-2">
          <div className="flex flex-col gap-1">
            <span className="rls-text-label-md text-[var(--rls-on-surface-variant)]">Período</span>
            <FilterChips
              options={filterOptions}
              selected={activeFilter}
              onChange={(value) => {
                let nextSelectedDate = currentDate ?? resolvedCurrentDate
                if (!currentDate) {
                  const nextDate = new Date()
                  nextSelectedDate = nextDate
                  setResolvedCurrentDate(nextDate)
                  setCalendarMonth(new Date(nextDate.getFullYear(), nextDate.getMonth(), 1))
                }
                setActiveFilter(value)
                if (value === "calendar") {
                  const todayIso = toIsoDate(nextSelectedDate)
                  setSelectedCalendarDate((selected) => selected || todayIso)
                  setCalendarOpen(true)
                }
              }}
            />
          </div>
          <div className="flex flex-col gap-1">
            <span className="rls-text-label-md text-[var(--rls-on-surface-variant)]">Tipo</span>
            <FilterChips
              options={typeFilterOptions}
              selected={typeFilter}
              onChange={setTypeFilter}
            />
          </div>
        </div>

        {/* Insights Banner */}
        <div className="bg-[var(--rls-surface-container-lowest)] rounded-[var(--rls-radius-lg)] p-[var(--rls-inline-padding-md)] shadow-sm">
          <div className="grid grid-cols-2 divide-x divide-[var(--rls-outline-variant)]">
            <div className="flex flex-col items-center gap-1 pr-4">
              <span className="rls-text-label-lg text-[var(--rls-on-surface-variant)]">Total Despesas</span>
              <span className="rls-text-headline-sm text-[var(--rls-error)]">
                {formatCurrency(totalFilteredExpenses)}
              </span>
            </div>
            <div className="flex flex-col items-center gap-1 pl-4">
              <span className="rls-text-label-lg text-[var(--rls-on-surface-variant)]">Total Receitas</span>
              <span className="rls-text-headline-sm text-[var(--rls-secondary)]">
                {formatCurrency(totalFilteredIncome)}
              </span>
            </div>
          </div>
        </div>

        {/* Transaction Groups */}
        {Object.entries(grouped).length > 0 ? Object.entries(grouped).map(([dateLabel, txs]) => (
          <div key={dateLabel} className="flex flex-col gap-2">
            <h3 className="rls-text-label-lg text-[var(--rls-on-surface-variant)] sticky top-0 bg-[var(--rls-background)]/90 backdrop-blur-sm py-2 z-10 uppercase">
              {dateLabel}
            </h3>
            <div className="flex flex-col">
              {txs.map((tx) => (
                <button
                  type="button"
                  key={tx.id}
                  onClick={() => onSelectTransaction?.(tx)}
                  className="flex h-[72px] w-full items-center justify-between border-b border-[var(--rls-surface-variant)] text-left transition-colors hover:bg-[var(--rls-surface-container-low)] last:border-0"
                >
                  <div className="flex items-center gap-4">
                    <div
                      className={cn(
                        "w-12 h-12 rounded-xl flex items-center justify-center",
                        tx.type === "receita"
                          ? "bg-[var(--rls-secondary-container)]/20"
                          : "bg-[var(--rls-error-container)]"
                      )}
                    >
                      <CategoryIcon
                        name={tx.name || tx.category}
                        size={24}
                        className={tx.type === "receita" ? "text-[var(--rls-secondary)]" : "text-[var(--rls-error)]"}
                      />
                    </div>
                    <div className="flex flex-col">
                      <span className="rls-text-body-lg text-[var(--rls-on-surface)]">
                        {tx.name}
                      </span>
                      <span className="rls-text-body-md text-[var(--rls-on-surface-variant)]">
                        {tx.category}
                      </span>
                    </div>
                  </div>
                  <span
                    className={cn(
                      "rls-text-body-lg font-semibold",
                      tx.type === "receita"
                        ? "text-[var(--rls-secondary)]"
                        : "text-[var(--rls-error)]"
                    )}
                  >
                    {tx.type === "receita" ? "+" : "-"}
                    {formatCurrency(tx.amount)}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )) : (
          <div className="rounded-[var(--rls-radius)] bg-[var(--rls-surface-container-lowest)] p-6 text-center shadow-sm">
            <p className="rls-text-body-lg text-[var(--rls-on-surface)]">
              Nenhuma transação encontrada
            </p>
            <p className="rls-text-body-md mt-1 text-[var(--rls-on-surface-variant)]">
              Ajuste a busca ou o período para ver outros lançamentos.
            </p>
          </div>
        )}
      </main>

      <BottomNavBar items={navItems} onNavigate={onNavigate} />
      <TransactionCalendarModal
        open={calendarOpen}
        month={calendarMonth}
        selectedDate={selectedCalendarDate}
        transactionDates={transactionDates}
        onClose={() => setCalendarOpen(false)}
        onMonthChange={setCalendarMonth}
        onSelect={(value) => {
          setSelectedCalendarDate(value)
          setActiveFilter("calendar")
          setCalendarOpen(false)
        }}
      />
    </div>
  )
}

function matchesType(
  transactionType: ReleaseTransaction["type"],
  filter: ReleaseTransactionTypeFilter
): boolean {
  if (filter === "all") return true
  return filter === "income" ? transactionType === "receita" : transactionType === "despesa"
}

function normalizeSearch(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
}

function matchesPeriod(
  transactionDate: string | undefined,
  filter: ReleaseFilterPeriod,
  currentDate: Date,
  selectedCalendarDate: string
): boolean {
  if (filter === "todo") return true
  if (!transactionDate) return false

  const date = parseLocalDate(transactionDate)
  if (!date) return false
  const today = startOfDay(currentDate)

  if (filter === "week") {
    const diffMs = today.getTime() - date.getTime()
    return diffMs >= 0 && diffMs <= 6 * 24 * 60 * 60 * 1000
  }

  if (filter === "month") {
    return date.getFullYear() === today.getFullYear() && date.getMonth() === today.getMonth()
  }

  return selectedCalendarDate ? transactionDate === selectedCalendarDate : true
}

function parseLocalDate(value: string): Date | null {
  const [year, month, day] = value.split("-").map(Number)
  if (!year || !month || !day) return null
  return new Date(year, month - 1, day)
}

function startOfDay(value: Date): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate())
}

function getGroupLabel(
  tx: ReleaseTransaction,
  filter: ReleaseFilterPeriod,
  currentDate: Date
): string {
  const date = tx.transactionDate ? parseLocalDate(tx.transactionDate) : null
  if (filter === "month" && date) {
    return new Intl.DateTimeFormat("pt-BR", {
      month: "long",
      year: "numeric",
    }).format(date)
  }

  if (date) {
    const today = startOfDay(currentDate)
    const yesterday = new Date(today)
    yesterday.setDate(today.getDate() - 1)
    if (date.getTime() === today.getTime()) return "Hoje"
    if (date.getTime() === yesterday.getTime()) return "Ontem"
  }

  return tx.date
}

function toIsoDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

function TransactionCalendarModal({
  open,
  month,
  selectedDate,
  transactionDates,
  onClose,
  onMonthChange,
  onSelect,
}: {
  open: boolean
  month: Date
  selectedDate: string
  transactionDates: Set<string>
  onClose: () => void
  onMonthChange: (date: Date) => void
  onSelect: (value: string) => void
}) {
  if (!open) return null

  const cells = getCalendarCells(month)
  const yearOptions = getYearOptions(month.getFullYear())

  return (
    <div className="rls">
      <button
        type="button"
        aria-label="Fechar calendário"
        className="fixed inset-0 z-[60] bg-[rgba(27,28,30,0.4)] backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="fixed bottom-0 left-1/2 z-[60] flex w-[min(100%,28rem)] -translate-x-1/2 justify-center">
        <div className="w-full rounded-t-[12px] bg-[var(--rls-surface-container-lowest)] p-4 shadow-sheet">
          <div className="flex items-center justify-between border-b border-[var(--rls-outline-variant)] pb-3">
            <button
              type="button"
              onClick={() => onMonthChange(new Date(month.getFullYear(), month.getMonth() - 1, 1))}
              className="flex h-10 w-10 items-center justify-center rounded-[var(--rls-radius)] text-[var(--rls-on-surface)]"
              aria-label="Mês anterior"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <div className="flex min-w-0 flex-1 items-center justify-center gap-2 px-2">
              <select
                aria-label="Selecionar mês"
                value={month.getMonth()}
                onChange={(event) => onMonthChange(new Date(month.getFullYear(), Number(event.target.value), 1))}
                className="h-10 min-w-0 flex-1 rounded-[var(--rls-radius)] border border-[var(--rls-outline-variant)] bg-[var(--rls-surface-container-lowest)] px-2 text-sm font-semibold capitalize text-[var(--rls-on-surface)] outline-none"
              >
                {MONTH_OPTIONS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
              <select
                aria-label="Selecionar ano"
                value={month.getFullYear()}
                onChange={(event) => onMonthChange(new Date(Number(event.target.value), month.getMonth(), 1))}
                className="h-10 w-24 rounded-[var(--rls-radius)] border border-[var(--rls-outline-variant)] bg-[var(--rls-surface-container-lowest)] px-2 text-sm font-semibold text-[var(--rls-on-surface)] outline-none"
              >
                {yearOptions.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center">
              <button
                type="button"
                onClick={() => onMonthChange(new Date(month.getFullYear(), month.getMonth() + 1, 1))}
                className="flex h-10 w-10 items-center justify-center rounded-[var(--rls-radius)] text-[var(--rls-on-surface)]"
                aria-label="Próximo mês"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
              <button
                type="button"
                onClick={onClose}
                className="flex h-10 w-10 items-center justify-center rounded-[var(--rls-radius)] text-[var(--rls-on-surface)]"
                aria-label="Fechar"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-7 grid-rows-[repeat(7,2.75rem)] gap-1 text-center">
            {["D", "S", "T", "Q", "Q", "S", "S"].map((label, index) => (
              <span key={`${label}-${index}`} className="rls-text-label-md text-[var(--rls-on-surface-variant)]">
                {label}
              </span>
            ))}
            {cells.map((date, index) => {
              const iso = date ? toIsoDate(date) : ""
              const hasTransaction = transactionDates.has(iso)
              const isSelected = iso && iso === selectedDate
              return (
                <button
                  key={iso || `empty-${index}`}
                  type="button"
                  disabled={!date}
                  onClick={() => iso && onSelect(iso)}
                  className={cn(
                    "relative flex h-11 items-center justify-center rounded-[var(--rls-radius)] text-sm font-semibold text-[var(--rls-on-surface)]",
                    !date && "pointer-events-none opacity-0",
                    isSelected && "bg-[var(--rls-primary-container)] text-white"
                  )}
                >
                  {date?.getDate()}
                  {hasTransaction ? (
                    <span
                      className={cn(
                        "absolute bottom-1 h-1.5 w-1.5 rounded-full bg-[var(--rls-primary-container)]",
                        isSelected && "bg-white"
                      )}
                    />
                  ) : null}
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

function getCalendarCells(month: Date): Array<Date | null> {
  const firstDay = new Date(month.getFullYear(), month.getMonth(), 1)
  const startOffset = firstDay.getDay()
  const daysInMonth = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate()
  return Array.from({ length: 42 }, (_, index) => {
    const day = index - startOffset + 1
    return day > 0 && day <= daysInMonth
      ? new Date(month.getFullYear(), month.getMonth(), day)
      : null
  })
}

function getYearOptions(currentYear: number): number[] {
  return Array.from({ length: 21 }, (_, index) => currentYear - 10 + index)
}
