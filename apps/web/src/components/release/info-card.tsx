"use client"

import { cn } from "@/lib/utils"
import type { ReactNode } from "react"

interface InfoCardProps {
  title?: string
  value: string
  subtitle?: string
  caption?: string
  icon?: ReactNode
  variant?: "default" | "primary" | "success" | "danger"
  className?: string
  children?: ReactNode
}

export function InfoCard({
  title,
  value,
  subtitle,
  caption,
  icon,
  variant = "default",
  className,
  children,
}: InfoCardProps) {
  const bgMap = {
    default: "bg-[var(--rls-surface-container-lowest)] shadow-sm",
    primary:
      "bg-[var(--rls-primary-container)] text-[var(--rls-on-primary)] relative overflow-hidden",
    success:
      "bg-[var(--rls-secondary-container)] text-[var(--rls-on-secondary-container)]",
    danger: "bg-[var(--rls-error-container)] text-[var(--rls-on-error-container)]",
  }

  const valueColorMap = {
    default: "text-[var(--rls-on-surface)]",
    primary: "text-[var(--rls-on-primary)]",
    success: "text-[var(--rls-on-secondary-container)]",
    danger: "text-[var(--rls-on-error-container)]",
  }

  return (
    <div
      className={cn(
        "rounded-[var(--rls-radius-lg)] p-[var(--rls-inline-padding-md)] flex flex-col gap-2",
        bgMap[variant],
        className
      )}
    >
      {variant === "primary" && (
        <div className="absolute -right-4 -top-4 w-24 h-24 bg-white/10 rounded-full blur-xl pointer-events-none" />
      )}

      {icon && (
        <div className="flex items-center gap-2">
          <div
            className={cn(
              "w-8 h-8 rounded-full flex items-center justify-center",
              variant === "primary" ? "bg-white/20" : "bg-[var(--rls-surface-container)]"
            )}
          >
            {icon}
          </div>
          {title && (
            <span className="rls-text-label-lg">{title}</span>
          )}
        </div>
      )}

      {title && !icon && (
        <span
          className={cn(
            "rls-text-body-md",
            variant === "default"
              ? "text-[var(--rls-on-surface-variant)]"
              : ""
          )}
        >
          {title}
        </span>
      )}

      <span
        className={cn(
          "text-[22px] font-semibold leading-7 tabular-nums",
          valueColorMap[variant]
        )}
      >
        {value}
      </span>

      {subtitle && (
        <span
          className={cn(
            "rls-text-body-md",
            variant === "default"
              ? "text-[var(--rls-on-surface-variant)]"
              : ""
          )}
        >
          {subtitle}
        </span>
      )}

      {caption && (
        <span className="rls-text-label-lg opacity-80">{caption}</span>
      )}

      {children}
    </div>
  )
}
