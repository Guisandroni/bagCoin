"use client"

import { cn } from "@/lib/utils"
import { formatCurrency, formatPercent } from "./format"

interface DonutSegment {
  value: number
  amount?: number
  color: string
  label: string
  emoji?: string
}

interface DonutChartProps {
  segments: DonutSegment[]
  centerLabel?: string
  centerValue?: string
  totalValue?: number
  periodLabel?: string
  title?: string
  openLabel?: string
  maxItems?: number
  onOpen?: () => void
  className?: string
}

export function DonutChart({
  segments,
  centerLabel,
  centerValue,
  totalValue,
  periodLabel,
  title = "Distribuição das despesas",
  openLabel = "Ver mais",
  maxItems = 5,
  onOpen,
  className,
}: DonutChartProps) {
  const visibleSegments = segments
    .filter((segment) => segment.value > 0)
    .slice(0, maxItems)
  const chartSegments = normalizeSegments(visibleSegments)
  const totalAmount = totalValue ?? visibleSegments.reduce((sum, item) => sum + (item.amount ?? 0), 0)
  const displayCenterValue = centerValue ?? formatCurrency(totalAmount)
  const displayCenterLabel = centerLabel ?? (periodLabel ? `Total em ${periodLabel}` : "Total no mês")

  return (
    <section
      className={cn(
        "rounded-[var(--rls-radius)] bg-[var(--rls-surface-container-lowest)] p-[var(--rls-inline-padding-md)] shadow-sm",
        className
      )}
    >
      <div className="mb-[var(--rls-stack-gap-md)] flex items-center justify-between gap-4">
        <h3 className="rls-text-title-lg text-base font-semibold text-[var(--rls-on-surface)]">
          {title}
        </h3>
        {onOpen ? (
          <button
            type="button"
            aria-label={openLabel}
            onClick={onOpen}
            className="rls-text-label-lg shrink-0 text-[var(--rls-primary)] transition-opacity hover:opacity-80"
          >
            {openLabel}
          </button>
        ) : null}
      </div>

      <div className="flex flex-col gap-[var(--rls-stack-gap-md)]">
        <div className="flex justify-center">
          <div className="relative h-36 w-36">
            <svg
              className="h-full w-full overflow-visible"
              viewBox="0 0 120 120"
              aria-label="Distribuição por categoria"
              role="img"
            >
              <circle
                cx="60"
                cy="60"
                fill="transparent"
                pathLength={100}
                r="48"
                stroke="var(--rls-surface-container-high)"
                strokeWidth="13"
              />
              {chartSegments.map((segment) => (
                <circle
                  key={segment.label}
                  cx="60"
                  cy="60"
                  fill="transparent"
                  pathLength={100}
                  r="48"
                  stroke="currentColor"
                  strokeDasharray={`${formatDash(segment.visibleValue)}, ${formatDash(
                    100 - segment.visibleValue
                  )}`}
                  strokeDashoffset={formatDash(-segment.offset)}
                  strokeLinecap="round"
                  strokeWidth="13"
                  transform="rotate(-90 60 60)"
                  style={{ color: segment.color, transition: "stroke-dasharray 0.5s ease" }}
                />
              ))}
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
              <span className="text-[9px] leading-3 text-[var(--rls-on-surface-variant)]">
                {displayCenterLabel}
              </span>
              <span className="mt-0.5 whitespace-nowrap text-[12px] font-bold leading-tight tracking-tight text-[var(--rls-on-surface)] tabular-nums">
                {displayCenterValue}
              </span>
            </div>
          </div>
        </div>

        <div className="flex min-w-0 flex-col gap-3">
          {visibleSegments.length > 0 ? (
            visibleSegments.map((segment) => (
              <div
                key={segment.label}
                className="flex min-h-10 items-center justify-between gap-3 px-0 py-1.5"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center text-sm">
                    {segment.emoji ?? "📦"}
                  </span>
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <span className="truncate text-sm font-semibold text-[var(--rls-on-surface)]">
                      {segment.label}
                    </span>
                    <span className="rounded-[var(--rls-radius-pill)] bg-[var(--rls-surface-container-high)] px-2 py-0.5 text-xs font-semibold text-[var(--rls-on-surface-variant)]">
                      {formatPercent(segment.value)}%
                    </span>
                  </div>
                </div>
                {segment.amount !== undefined ? (
                  <span className="shrink-0 text-sm font-semibold text-[var(--rls-on-surface)] tabular-nums">
                    {formatCurrency(segment.amount)}
                  </span>
                ) : null}
              </div>
            ))
          ) : (
            <div className="rounded-2xl border border-dashed border-[var(--rls-outline-variant)] px-4 py-6 text-center text-sm text-[var(--rls-on-surface-variant)]">
              Nenhuma despesa no período.
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

function normalizeSegments(segments: DonutSegment[]) {
  const total = segments.reduce((sum, segment) => sum + segment.value, 0)
  const gap = segments.length > 1 ? 3 : 0
  let cumulative = 0

  return segments.map((segment) => {
    const normalizedValue = total > 0 ? (segment.value / total) * 100 : 0
    const visibleValue = Math.max(normalizedValue - gap, 0)
    const offset = cumulative + gap / 2
    cumulative += normalizedValue

    return {
      ...segment,
      visibleValue,
      offset,
    }
  })
}

function formatDash(value: number): string {
  return Number(value.toFixed(2)).toString()
}
