"use client"

import { type ReactNode } from "react"
import { cn } from "@/lib/utils"

interface AuthCardProps {
  children: ReactNode
  className?: string
}

export function AuthCard({ children, className }: AuthCardProps) {
  return (
    <div
      className={cn(
        "rls w-full max-w-md mx-auto flex flex-col bg-[var(--rls-surface-container-lowest)] rounded-[var(--rls-radius-lg)] shadow-sm p-6 sm:p-8",
        className
      )}
    >
      {children}
    </div>
  )
}

interface AuthHeaderProps {
  icon?: ReactNode
  title: string
  subtitle?: string
}

export function AuthHeader({ icon, title, subtitle }: AuthHeaderProps) {
  return (
    <header className="mb-8 text-center flex flex-col items-center">
      {icon && (
        <div className="w-16 h-16 bg-[var(--rls-primary-container)] rounded-full flex items-center justify-center mb-6 shadow-md shadow-[var(--rls-primary-container)]/20">
          {icon}
        </div>
      )}
      <h1 className="rls-text-display-md text-[var(--rls-on-background)] mb-2">
        {title}
      </h1>
      {subtitle && (
        <p className="rls-text-body-md text-[var(--rls-on-surface-variant)]">
          {subtitle}
        </p>
      )}
    </header>
  )
}

interface AuthDividerProps {
  text?: string
}

export function AuthDivider({ text = "ou entre com" }: AuthDividerProps) {
  return (
    <div className="flex items-center my-8 w-full gap-4">
      <div className="flex-1 h-px bg-[var(--rls-outline-variant)]/40" />
      <span className="rls-text-label-lg text-[var(--rls-on-surface-variant)] uppercase tracking-wider">
        {text}
      </span>
      <div className="flex-1 h-px bg-[var(--rls-outline-variant)]/40" />
    </div>
  )
}

interface AuthFooterProps {
  text: string
  linkText: string
  onLinkClick?: () => void
}

export function AuthFooter({ text, linkText, onLinkClick }: AuthFooterProps) {
  return (
    <div className="mt-8 text-center">
      <p className="rls-text-body-md text-[var(--rls-on-surface-variant)]">
        {text}{" "}
        <button
          onClick={onLinkClick}
          className="text-[var(--rls-primary)] font-bold hover:text-[var(--rls-primary-container)] transition-colors ml-1"
        >
          {linkText}
        </button>
      </p>
    </div>
  )
}

interface DecorativeBlobsProps {
  className?: string
}

export function DecorativeBlobs({ className }: DecorativeBlobsProps) {
  return <div className={cn("hidden", className)} aria-hidden />
}
