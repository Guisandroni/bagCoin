"use client"

import { type ReactNode } from "react"
import { ArrowLeft, Menu, Search, MoreVertical } from "lucide-react"
import { cn } from "@/lib/utils"

interface AppBarAction {
  icon: ReactNode
  onClick: () => void
  label?: string
}

interface AppBarProps {
  title?: string
  titleClassName?: string
  className?: string
  onBack?: () => void
  onOpenDrawer?: () => void
  actions?: AppBarAction[]
  avatar?: ReactNode
  sticky?: boolean
}

export function AppBar({
  title,
  titleClassName,
  className,
  onBack,
  onOpenDrawer,
  actions,
  avatar,
  sticky = true,
}: AppBarProps) {
  return (
    <header
      className={cn(
        "flex items-center w-full px-[var(--rls-container-margin)] py-[var(--rls-stack-gap-md)] bg-[var(--rls-surface)] z-40",
        sticky && "sticky top-0",
        className
      )}
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center">
        {avatar ? (
          avatar
        ) : onOpenDrawer ? (
          <button
            type="button"
            onClick={onOpenDrawer}
            aria-label="Abrir menu"
            className="w-10 h-10 flex items-center justify-center rounded-[var(--rls-radius)] border border-[var(--rls-outline-variant)] bg-[var(--rls-surface-container-lowest)] text-[var(--rls-on-surface)] shadow-sm transition-colors active:scale-95"
          >
            <Menu className="w-6 h-6" />
          </button>
        ) : onBack ? (
          <button
            onClick={onBack}
            className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-[var(--rls-surface-container-high)] transition-colors active:scale-95"
          >
            <ArrowLeft className="w-6 h-6 text-[var(--rls-on-surface)]" />
          </button>
        ) : (
          <span aria-hidden className="block h-10 w-10" />
        )}
      </div>

      {title && (
        <h1
          className={cn(
            titleClassName
              ? "flex-1"
              : "rls-text-display-md text-[var(--rls-primary-container)] text-2xl flex-1 text-center",
            titleClassName
          )}
        >
          {title}
        </h1>
      )}

      <div className="flex h-10 w-10 shrink-0 items-center justify-center gap-2">
        {actions?.map((action, i) => (
          <button
            key={i}
            onClick={action.onClick}
            aria-label={action.label}
            className="w-10 h-10 flex items-center justify-center text-[var(--rls-primary)] hover:opacity-80 transition-opacity active:scale-95 rounded-full"
          >
            {action.icon}
          </button>
        ))}
        {!actions && <span aria-hidden className="block h-10 w-10" />}
      </div>
    </header>
  )
}

export function AppBarSearchAction(onClick: () => void): AppBarAction {
  return { icon: <Search className="w-6 h-6" />, onClick, label: "Buscar" }
}

export function AppBarMoreAction(onClick: () => void): AppBarAction {
  return {
    icon: <MoreVertical className="w-6 h-6" />,
    onClick,
    label: "Mais",
  }
}
