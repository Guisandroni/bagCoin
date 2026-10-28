"use client"

import { useMemo, useState } from "react"
import { CalendarDays, ChevronLeft, ChevronRight, X } from "lucide-react"
import { cn } from "@/lib/utils"

const MONTH_OPTIONS = Array.from({ length: 12 }, (_, month) => ({
  value: month,
  label: new Intl.DateTimeFormat("pt-BR", { month: "long" }).format(new Date(2026, month, 1)),
}))

interface ReleaseDatePickerProps {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export function ReleaseDatePicker({
  label,
  value,
  onChange,
  placeholder = "Selecionar data",
}: ReleaseDatePickerProps) {
  const [open, setOpen] = useState(false)
  const [month, setMonth] = useState(() => getInitialCalendarMonth(value))
  const displayValue = value ? formatFullDate(value) : placeholder

  return (
    <div className="flex flex-col gap-1">
      <span className="rls-text-label-lg ml-4 text-[var(--rls-on-background)]">
        {label}
      </span>
      <button
        type="button"
        aria-label={label}
        onClick={() => {
          setMonth(value ? getInitialCalendarMonth(value) : getCurrentCalendarMonth())
          setOpen(true)
        }}
        className={cn(
          "flex h-14 w-full items-center gap-3 rounded-[var(--rls-radius-pill)] bg-[var(--rls-surface-container)] px-4 text-left",
          "rls-text-body-lg text-[var(--rls-on-surface)] transition-all",
          "focus:bg-[var(--rls-surface-container-lowest)] focus:outline-none focus:ring-2 focus:ring-[var(--rls-primary)]",
          !value && "text-[var(--rls-on-surface-variant)]/60"
        )}
      >
        <CalendarDays className="h-5 w-5 shrink-0 text-[var(--rls-outline)]" />
        <span className="truncate">{displayValue}</span>
      </button>

      <DatePickerSheet
        open={open}
        month={month}
        selectedDate={value}
        onClose={() => setOpen(false)}
        onMonthChange={setMonth}
        onSelect={(nextValue) => {
          onChange(nextValue)
          setOpen(false)
        }}
      />
    </div>
  )
}

interface DatePickerSheetProps {
  open: boolean
  month: Date
  selectedDate: string
  onClose: () => void
  onMonthChange: (date: Date) => void
  onSelect: (value: string) => void
}

function DatePickerSheet({
  open,
  month,
  selectedDate,
  onClose,
  onMonthChange,
  onSelect,
}: DatePickerSheetProps) {
  const cells = useMemo(() => {
    return getCalendarCells(month)
  }, [month])
  const yearOptions = getYearOptions(month.getFullYear())

  if (!open) return null

  return (
    <div className="rls">
      <button
        type="button"
        aria-label="Fechar calendário"
        className="fixed inset-0 z-[70] bg-[rgba(27,28,30,0.4)] backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="fixed bottom-0 left-1/2 z-[70] flex w-[min(100%,28rem)] -translate-x-1/2 justify-center">
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
            {["D", "S", "T", "Q", "Q", "S", "S"].map((weekday, index) => (
              <span
                key={`${weekday}-${index}`}
                className="rls-text-label-md text-[var(--rls-on-surface-variant)]"
              >
                {weekday}
              </span>
            ))}
            {cells.map((date, index) => {
              const iso = date ? toIsoDate(date) : ""
              const isSelected = iso && iso === selectedDate
              return (
                <button
                  key={iso || `empty-${index}`}
                  type="button"
                  disabled={!date}
                  onClick={() => iso && onSelect(iso)}
                  className={cn(
                    "flex h-11 items-center justify-center rounded-[var(--rls-radius)] text-sm font-semibold text-[var(--rls-on-surface)]",
                    !date && "pointer-events-none opacity-0",
                    isSelected && "bg-[var(--rls-primary-container)] text-white"
                  )}
                >
                  {date?.getDate()}
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

function getInitialCalendarMonth(value: string): Date {
  const date = parseLocalDate(value)
  return date ? new Date(date.getFullYear(), date.getMonth(), 1) : new Date(2026, 0, 1)
}

function getCurrentCalendarMonth(): Date {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), 1)
}

function parseLocalDate(value: string): Date | null {
  const [year, month, day] = value.split("-").map(Number)
  if (!year || !month || !day) return null
  return new Date(year, month - 1, day)
}

function toIsoDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

function formatFullDate(value: string): string {
  const date = parseLocalDate(value)
  if (!date) return value
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(date)
}
