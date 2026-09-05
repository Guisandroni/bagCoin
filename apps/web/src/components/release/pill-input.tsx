"use client"

import { useState, type InputHTMLAttributes, type ReactNode } from "react"
import { Eye, EyeOff } from "lucide-react"
import { cn } from "@/lib/utils"

interface PillInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  label?: string
  icon?: ReactNode
  showPasswordToggle?: boolean
  error?: string
}

export function PillInput({
  label,
  icon,
  showPasswordToggle = false,
  error,
  className,
  id,
  ...props
}: PillInputProps) {
  const [showPassword, setShowPassword] = useState(false)
  const inputId = id || props.placeholder?.toLowerCase().replace(/\s+/g, "-")
  const inputType = showPasswordToggle ? (showPassword ? "text" : "password") : props.type

  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label
          htmlFor={inputId}
          className="rls-text-label-lg text-[var(--rls-on-background)] ml-4"
        >
          {label}
        </label>
      )}
      <div className="relative flex items-center">
        {icon && (
          <span className="absolute left-4 text-[var(--rls-outline)] z-10">
            {icon}
          </span>
        )}
        <input
          {...props}
          id={inputId}
          className={cn(
            "w-full h-14 bg-[var(--rls-surface-container)] border-none rounded-[var(--rls-radius-pill)]",
            "rls-text-body-lg text-[var(--rls-on-surface)]",
            "placeholder:text-[var(--rls-on-surface-variant)]/50",
            "focus:ring-2 focus:ring-[var(--rls-primary)] focus:bg-[var(--rls-surface-container-lowest)]",
            "transition-all outline-none",
            icon ? "pl-12" : "pl-4",
            showPasswordToggle ? "pr-12" : "pr-4",
            error && "ring-2 ring-[var(--rls-error)]",
            className
          )}
          type={inputType}
        />
        {showPasswordToggle && (
          <button
            type="button"
            aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
            aria-pressed={showPassword}
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-4 text-[var(--rls-outline)] hover:text-[var(--rls-on-surface)] transition-colors"
          >
            {showPassword ? (
              <EyeOff className="w-5 h-5" />
            ) : (
              <Eye className="w-5 h-5" />
            )}
          </button>
        )}
      </div>
      {error && (
        <p className="rls-text-label-md text-[var(--rls-error)] ml-4">{error}</p>
      )}
    </div>
  )
}
