"use client"

export function formatCurrency(value: number, options?: { sign?: "auto" | "none" }) {
  const amount = Math.abs(Number.isFinite(value) ? value : 0)
  const formatted = new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)

  if (options?.sign === "auto") {
    if (value > 0) return `+${formatted}`
    if (value < 0) return `-${formatted}`
  }

  return formatted
}

export function formatPercent(value: number) {
  const amount = Number.isFinite(value) ? value : 0
  return new Intl.NumberFormat("pt-BR", {
    maximumFractionDigits: amount % 1 === 0 ? 0 : 1,
  }).format(amount)
}

export function sanitizeMoneyInput(value: string): string {
  const cleaned = value.replace(/[^\d,.]/g, "")
  const separatorIndex = cleaned.search(/[,.]/)

  if (separatorIndex === -1) {
    return cleaned
  }

  const integer = cleaned.slice(0, separatorIndex).replace(/[,.]/g, "")
  const decimal = cleaned.slice(separatorIndex + 1).replace(/[,.]/g, "").slice(0, 2)
  return `${integer}${cleaned[separatorIndex]}${decimal}`
}

export function parseMoneyInput(value: string): number {
  const cleaned = value.replace(/[^\d,.]/g, "")
  const normalized = cleaned.includes(",")
    ? cleaned.replace(/\./g, "").replace(",", ".")
    : cleaned.split(".").length === 2 && (cleaned.split(".")[1]?.length ?? 0) <= 2
      ? cleaned
      : cleaned.replace(/\./g, "")
  return Math.abs(Number.parseFloat(normalized) || 0)
}
