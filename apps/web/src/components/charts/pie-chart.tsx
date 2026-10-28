"use client"

import { useId } from "react"

export interface PieSlice {
  name: string
  value: number
  color: string
}

interface DashboardPieChartProps {
  data: PieSlice[]
  size?: number
  className?: string
}

export function DashboardPieChart({ data, size = 160, className }: DashboardPieChartProps) {
  const gid = useId().replace(/:/g, "")
  const total = data.reduce((s, d) => s + d.value, 0)
  if (total <= 0) return null

  const slices = data.reduce<Array<PieSlice & { start: number; end: number }>>(
    (items, d) => {
      const start = items.at(-1)?.end ?? 0
      return [...items, { ...d, start, end: start + d.value }]
    },
    []
  )

  const cx = size / 2
  const cy = size / 2
  const r = size / 2 - 4

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      width={size}
      height={size}
      className={className}
      role="img"
      aria-label="Distribuição por categoria"
    >
      {slices.map((s, i) => {
        const a1 = (s.start / total) * Math.PI * 2 - Math.PI / 2
        const a2 = (s.end / total) * Math.PI * 2 - Math.PI / 2
        const x1 = cx + r * Math.cos(a1)
        const y1 = cy + r * Math.sin(a1)
        const x2 = cx + r * Math.cos(a2)
        const y2 = cy + r * Math.sin(a2)
        const large = s.end - s.start > total / 2 ? 1 : 0
        return (
          <path
            key={`${gid}-slice-${i}`}
            d={`M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${large} 1 ${x2},${y2} Z`}
            fill={s.color}
            stroke="var(--card)"
            strokeWidth="2"
          >
            <animate
              attributeName="opacity"
              from="0"
              to="1"
              dur="0.4s"
              begin={`${i * 0.1}s`}
              fill="freeze"
            />
          </path>
        )
      })}
    </svg>
  )
}
