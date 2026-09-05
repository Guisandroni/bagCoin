"use client"

import { useEffect } from "react"
import { usePathname, useRouter } from "next/navigation"

const ACTIVE_REFRESH_MS = 3000
const BACKGROUND_REFRESH_MS = 30000

const FINANCIAL_PATHS = new Set([
  "/app",
  "/app/transacoes",
  "/app/orcamentos",
  "/app/metas",
  "/app/categorias",
  "/app/relatorios",
])

function refreshDelay() {
  if (typeof document === "undefined") return ACTIVE_REFRESH_MS
  return document.visibilityState === "visible" ? ACTIVE_REFRESH_MS : BACKGROUND_REFRESH_MS
}

export function FinancialRouteRefresher() {
  const pathname = usePathname()
  const router = useRouter()
  const shouldRefresh = FINANCIAL_PATHS.has(pathname)

  useEffect(() => {
    if (!shouldRefresh) return

    let timeoutId: number | undefined

    const schedule = () => {
      timeoutId = window.setTimeout(() => {
        router.refresh()
        schedule()
      }, refreshDelay())
    }

    const handleVisibilityChange = () => {
      if (document.visibilityState !== "visible") return
      router.refresh()
      if (timeoutId) window.clearTimeout(timeoutId)
      schedule()
    }

    schedule()
    document.addEventListener("visibilitychange", handleVisibilityChange)

    return () => {
      if (timeoutId) window.clearTimeout(timeoutId)
      document.removeEventListener("visibilitychange", handleVisibilityChange)
    }
  }, [router, shouldRefresh])

  return null
}
