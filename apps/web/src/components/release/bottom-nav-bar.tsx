"use client"

import { type ReactNode } from "react"
import { cn } from "@/lib/utils"
import type { ReleaseNavItem } from "./types"
import {
  Home,
  Wallet,
  ArrowLeftRight,
  BarChart3,
  Target,
  LayoutGrid,
} from "lucide-react"

const iconMap: Record<string, ReactNode> = {
  home: <Home className="w-5 h-5" />,
  portfolio: <ArrowLeftRight className="w-5 h-5" />,
  wallet: <Wallet className="w-5 h-5" />,
  mercado: <BarChart3 className="w-5 h-5" />,
  ajustes: <BarChart3 className="w-5 h-5" />,
  target: <Target className="w-5 h-5" />,
  categorias: <LayoutGrid className="w-5 h-5" />,
}

interface BottomNavBarProps {
  items: ReleaseNavItem[]
  onNavigate: (href: string) => void
  className?: string
}

export function BottomNavBar({ items, onNavigate, className }: BottomNavBarProps) {
  return (
    <nav
      className={cn(
        "rls-floating-bottom-nav",
        "flex justify-around items-center px-2 py-3",
        className
      )}
    >
      {items.map((item) => (
        <button
          key={item.href}
          onClick={() => onNavigate(item.href)}
          className={cn(
            "flex min-w-0 flex-1 flex-col items-center justify-center gap-1 px-1 py-1.5 text-[10px] transition-all",
            item.isActive
              ? "text-[var(--rls-primary-container)]"
              : "text-[var(--rls-on-surface-variant)] hover:text-[var(--rls-primary)]"
          )}
        >
          <span
            className={cn(
              "flex h-9 w-9 items-center justify-center rounded-full transition-all",
              item.isActive
                ? "bg-[var(--rls-primary-container)] text-white shadow-md shadow-[var(--rls-primary-container)]/20"
                : "bg-transparent"
            )}
          >
            {iconMap[item.icon] || iconMap.ajustes}
          </span>
          <span
            className={cn(
              "max-w-full truncate font-medium leading-3",
              item.isActive && "font-bold"
            )}
          >
            {item.label}
          </span>
        </button>
      ))}
    </nav>
  )
}
