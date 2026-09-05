"use client"

const ACTIVE_REFETCH_MS = 3000
const BACKGROUND_REFETCH_MS = 30000

export function financialPollingInterval() {
  if (typeof document === "undefined") return ACTIVE_REFETCH_MS
  return document.visibilityState === "visible" ? ACTIVE_REFETCH_MS : BACKGROUND_REFETCH_MS
}

export const financialPollingOptions = {
  staleTime: 0,
  refetchOnWindowFocus: true,
  refetchOnReconnect: true,
  refetchInterval: financialPollingInterval,
}
