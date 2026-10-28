"use client"

import { cn } from "@/lib/utils"
import type { ReactNode } from "react"
import { formatCurrency, formatPercent } from "./format"

interface ProgressCardProps {
  title: string
  subtitle?: string
  current: number
  target: number
  percentage: number
  color?: string
  remainingText?: string
  icon?: ReactNode
  iconBg?: string
  iconColor?: string
  percentageClassName?: string
  remainingClassName?: string
  titleTrailing?: ReactNode
  className?: string
}

const defaultColors: Record<string, string> = {
  blue: "bg-[var(--rls-primary-container)]",
  red: "bg-[var(--rls-error)]",
  green: "bg-[var(--rls-secondary-container)]",
  pink: "bg-[var(--rls-tertiary-container)]",
  gray: "bg-[var(--rls-outline)]",
}

export function ProgressCard({
  title,
  subtitle,
  current,
  target,
  percentage,
  color = "blue",
  remainingText,
  icon,
  iconBg,
  iconColor,
  percentageClassName,
  remainingClassName,
  titleTrailing,
  className,
}: ProgressCardProps) {
  const barColor = defaultColors[color] || defaultColors.blue
  const progressWidth = Math.min(Math.max(percentage, 0), 100)

  return (
    <div
      className={cn(
        "bg-[var(--rls-surface-container-lowest)] p-[var(--rls-inline-padding-md)] rounded-[var(--rls-radius-lg)]",
        "shadow-sm flex flex-col gap-[var(--rls-stack-gap-sm)]",
        className
      )}
    >
      {(title || icon) && (
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            {icon && (
              <div
                className={cn(
                  "w-12 h-12 rounded-xl flex items-center justify-center",
                  iconBg || "bg-[var(--rls-surface-container)]"
                )}
                style={iconColor ? { color: iconColor } : undefined}
              >
                {icon}
              </div>
            )}
            <div className="flex min-w-0 flex-col">
              <span className="rls-text-body-lg text-[var(--rls-on-surface)]">{title}</span>
              {subtitle && (
                <span className="rls-text-body-md text-[var(--rls-on-surface-variant)]">
                  {subtitle}
                </span>
              )}
            </div>
          </div>
          {titleTrailing ? <div className="shrink-0 text-right">{titleTrailing}</div> : null}
        </div>
      )}

      <div className="flex justify-between items-end">
        <span className="rls-text-body-lg text-[var(--rls-on-surface)]">
          {formatCurrency(current)}{" "}
          <span className="text-[var(--rls-on-surface-variant)]">
            / {formatCurrency(target)}
          </span>
        </span>
        <span
          className={cn(
            "rls-text-label-lg",
            percentageClassName ||
              (percentage >= 90
                ? "text-[var(--rls-error)]"
                : "text-[var(--rls-primary-container)]")
          )}
        >
          {formatPercent(percentage)}%
        </span>
      </div>

      <div className="w-full h-2 bg-[var(--rls-surface-container-high)] rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", barColor)}
          style={{ width: `${progressWidth}%` }}
        />
      </div>

      {remainingText && (
        <span
          className={cn(
            "rls-text-label-md",
            remainingClassName ||
              (percentage >= 90
                ? "text-[var(--rls-error)]"
                : "text-[var(--rls-on-surface-variant)]")
          )}
        >
          {remainingText}
        </span>
      )}
    </div>
  )
}
