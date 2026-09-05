"use client"

import { Menu, Plus } from "lucide-react"
import { useAppStore } from "@/lib/store"
import { cn } from "@/lib/utils"

interface FunctionHeaderProps {
  title: string
  actionLabel: string
  onAction: () => void
  className?: string
}

export function FunctionHeader({
  title,
  actionLabel,
  onAction,
  className,
}: FunctionHeaderProps) {
  const toggleDrawer = useAppStore((state) => state.toggleDrawer)

  return (
    <header
      className={cn(
        "sticky top-0 z-40 flex w-full items-center gap-3 border-b border-[var(--rls-outline-variant)] bg-[var(--rls-surface)] px-[var(--rls-container-margin)] py-3",
        className
      )}
    >
      <button
        type="button"
        aria-label="Abrir menu"
        onClick={toggleDrawer}
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[var(--rls-radius)] border border-[var(--rls-outline-variant)] bg-[var(--rls-surface-container-lowest)] text-[var(--rls-on-surface)] shadow-sm"
      >
        <Menu className="h-6 w-6" />
      </button>

      <h1 className="min-w-0 flex-1 truncate text-[22px] font-semibold leading-7 text-[var(--rls-on-surface)]">
        {title}
      </h1>

      <button
        type="button"
        onClick={onAction}
        className="flex h-11 shrink-0 items-center justify-center gap-2 rounded-[var(--rls-radius)] bg-[var(--rls-primary-container)] px-3 text-sm font-bold text-white shadow-md shadow-[var(--rls-primary-container)]/20 transition-colors active:scale-[0.98]"
      >
        <Plus className="h-5 w-5" />
        <span className="max-w-[118px] truncate sm:max-w-none">{actionLabel}</span>
      </button>
    </header>
  )
}
