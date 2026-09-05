"use client"

import { useState } from "react"
import { X } from "lucide-react"
import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

const storageKey = (id: string) => `bagcoin:promo-dismissed:${id}`

interface PromoBannerProps {
  id: string
  title: string
  description: string
  illustration?: ReactNode
  className?: string
}

export function PromoBanner({ id, title, description, illustration, className }: PromoBannerProps) {
  const [dismissed, setDismissed] = useState(() => {
    try {
      if (typeof window !== "undefined") {
        return localStorage.getItem(storageKey(id)) === "1"
      }
    } catch {
      /* ignore */
    }
    return false
  })

  if (dismissed) return null

  return (
    <div
      className={cn(
        "relative flex gap-3 overflow-hidden rounded-2xl border border-border bg-card p-4",
        className
      )}
    >
      <button
        type="button"
        onClick={() => {
          try {
            localStorage.setItem(storageKey(id), "1")
          } catch {
            /* ignore */
          }
          setDismissed(true)
        }}
        className="touch-target absolute right-2 top-2 rounded-full p-1 text-muted-foreground hover:bg-muted"
        aria-label="Fechar"
      >
        <X className="h-4 w-4" />
      </button>
      <div className="min-w-0 flex-1 pr-8">
        <p className="text-[15px] font-bold leading-snug">{title}</p>
        <p className="mt-1 text-[13px] text-muted-foreground">{description}</p>
      </div>
      {illustration ? (
        <div className="hidden shrink-0 sm:block" aria-hidden>
          {illustration}
        </div>
      ) : null}
    </div>
  )
}
