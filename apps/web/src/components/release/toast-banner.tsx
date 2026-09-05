"use client";

import { useEffect } from "react";
import { CheckCircle, XCircle, AlertCircle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastVariant = "success" | "error" | "warning" | "info";

interface ToastBannerProps {
  message: string;
  variant?: ToastVariant;
  isOpen: boolean;
  onClose?: () => void;
  duration?: number;
  className?: string;
}

const variantStyles: Record<
  ToastVariant,
  { bg: string; icon: typeof CheckCircle; iconClassName: string }
> = {
  success: {
    bg: "bg-[var(--rls-secondary-container)]/20 border-[var(--rls-secondary-container)] text-[var(--rls-on-secondary-container)]",
    icon: CheckCircle,
    iconClassName: "text-[var(--rls-secondary)]",
  },
  error: {
    bg: "bg-[var(--rls-error-container)] border-[var(--rls-error)] text-[var(--rls-on-error-container)]",
    icon: XCircle,
    iconClassName: "text-[var(--rls-error)]",
  },
  warning: {
    bg: "bg-amber-50 border-amber-200 text-amber-800",
    icon: AlertCircle,
    iconClassName: "text-amber-600",
  },
  info: {
    bg: "bg-blue-50 border-blue-200 text-blue-800",
    icon: Info,
    iconClassName: "text-blue-600",
  },
};

export function ToastBanner({
  message,
  variant = "success",
  isOpen,
  onClose,
  duration = 3000,
  className,
}: ToastBannerProps) {
  const Icon = variantStyles[variant].icon;

  useEffect(() => {
    if (isOpen && duration > 0) {
      const timer = setTimeout(() => {
        onClose?.();
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [isOpen, duration, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className={cn(
        "fixed top-[88px] left-1/2 z-[80] w-[calc(min(100%,28rem)-24px)] -translate-x-1/2",
        "flex items-center justify-center gap-3 border px-4 py-3 rounded-[var(--rls-radius-pill)] shadow-lg",
        "animate-[slide-down_200ms_ease-out]",
        variantStyles[variant].bg,
        className,
      )}
    >
      <Icon
        className={cn("w-5 h-5 shrink-0", variantStyles[variant].iconClassName)}
      />
      <span className="rls-text-body-lg">{message}</span>
      {onClose && (
        <button
          onClick={() => {
            onClose();
          }}
          className="ml-2 hover:opacity-70 transition-opacity"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
