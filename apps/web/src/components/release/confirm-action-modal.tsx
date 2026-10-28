"use client"

import { AlertTriangle, X } from "lucide-react"
import { cn } from "@/lib/utils"

interface ReleaseConfirmActionModalProps {
  open: boolean
  title: string
  description: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: "danger" | "primary"
  isLoading?: boolean
  onConfirm: () => Promise<void> | void
  onCancel: () => void
}

export function ReleaseConfirmActionModal({
  open,
  title,
  description,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  variant = "danger",
  isLoading = false,
  onConfirm,
  onCancel,
}: ReleaseConfirmActionModalProps) {
  if (!open) return null

  return (
    <div className="rls">
      <button
        type="button"
        aria-label="Fechar confirmação"
        className="fixed inset-0 z-[70] bg-[rgba(27,28,30,0.45)] backdrop-blur-sm"
        onClick={onCancel}
      />
      <div className="fixed bottom-0 left-1/2 z-[70] flex w-[min(100%,28rem)] -translate-x-1/2 justify-center">
        <div className="w-full max-w-sm rounded-t-[12px] bg-[var(--rls-surface-container-lowest)] shadow-sheet">
          <div className="flex justify-center pb-2 pt-3">
            <div className="h-1 w-10 rounded-full bg-[var(--rls-outline-variant)]" />
          </div>

          <div className="flex items-start justify-between gap-4 border-b border-[var(--rls-outline-variant)] px-[var(--rls-inline-padding-md)] pb-4">
            <div className="flex items-start gap-3">
              <div
                className={cn(
                  "flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--rls-radius)]",
                  variant === "danger"
                    ? "bg-[var(--rls-error-container)] text-[var(--rls-error)]"
                    : "bg-[var(--rls-primary-container)]/10 text-[var(--rls-primary-container)]"
                )}
              >
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <h2 className="rls-text-title-lg text-[var(--rls-on-surface)]">{title}</h2>
                <p className="rls-text-body-md mt-1 text-[var(--rls-on-surface-variant)]">
                  {description}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onCancel}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--rls-radius)] text-[var(--rls-on-surface-variant)] transition-colors hover:bg-[var(--rls-surface-container-high)]"
              aria-label="Fechar confirmação"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3 px-[var(--rls-inline-padding-md)] py-4">
            <button
              type="button"
              onClick={onCancel}
              disabled={isLoading}
              className="h-12 rounded-[var(--rls-radius-pill)] bg-[var(--rls-surface-container)] text-[var(--rls-on-surface)] rls-text-body-lg transition-colors disabled:opacity-50"
            >
              {cancelLabel}
            </button>
            <button
              type="button"
              onClick={onConfirm}
              disabled={isLoading}
              className={cn(
                "h-12 rounded-[var(--rls-radius-pill)] text-white rls-text-body-lg shadow-md transition-colors active:scale-[0.98] disabled:opacity-50",
                variant === "danger"
                  ? "bg-[var(--rls-error)] shadow-[var(--rls-error)]/20"
                  : "bg-[var(--rls-primary-container)] shadow-[var(--rls-primary-container)]/20"
              )}
            >
              {isLoading ? "Excluindo..." : confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
