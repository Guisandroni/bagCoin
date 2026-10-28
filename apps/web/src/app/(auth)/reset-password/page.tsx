"use client"

import { useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Lock } from "lucide-react"
import { AuthCard, AuthFooter, AuthHeader } from "@/components/release/auth-card"
import { PillInput } from "@/components/release/pill-input"
import { ToastBanner } from "@/components/release/toast-banner"
import { useAuthStore } from "@/lib/auth-store"
import { PASSWORD_RESET_INVALID_MESSAGE, PASSWORD_RESET_SUCCESS_MESSAGE } from "@/lib/toast-messages"
import { changePasswordSchema } from "@/lib/validations"

export default function ResetPasswordPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const resetPassword = useAuthStore((state) => state.resetPassword)
  const isLoading = useAuthStore((state) => state.isLoading)
  const token = searchParams.get("token") || ""
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null)

  return (
    <div className="rls flex min-h-dvh flex-col items-center justify-center bg-[var(--rls-background)] p-[var(--rls-container-margin)]">
      <ToastBanner
        isOpen={!!toast}
        message={toast?.message ?? ""}
        variant={toast?.variant ?? "success"}
        onClose={() => setToast(null)}
      />
      <AuthCard>
        <AuthHeader title="Criar nova senha" subtitle="Digite e confirme sua nova senha. O link expira em 5 minutos." />
        <form
          className="flex w-full flex-col gap-[var(--rls-stack-gap-md)]"
          onSubmit={async (event) => {
            event.preventDefault()
            const parsed = changePasswordSchema.safeParse({
              currentPassword: "Password1",
              newPassword: password,
              confirmPassword,
            })
            if (!token) {
              setToast({ message: PASSWORD_RESET_INVALID_MESSAGE, variant: "error" })
              return
            }
            if (!parsed.success) {
              setToast({ message: parsed.error.issues[0]?.message || "Revise a senha.", variant: "error" })
              return
            }
            try {
              await resetPassword(token, password)
              setToast({ message: PASSWORD_RESET_SUCCESS_MESSAGE, variant: "success" })
              setTimeout(() => router.push("/login"), 800)
            } catch (err) {
              void err
              setToast({
                message: PASSWORD_RESET_INVALID_MESSAGE,
                variant: "error",
              })
            }
          }}
        >
          <PillInput
            label="Nova senha"
            icon={<Lock className="h-5 w-5" />}
            placeholder="Digite a nova senha"
            type="password"
            showPasswordToggle
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <PillInput
            label="Confirmar senha"
            icon={<Lock className="h-5 w-5" />}
            placeholder="Repita a nova senha"
            type="password"
            showPasswordToggle
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
          />
          <button
            type="submit"
            disabled={isLoading}
            className="h-14 rounded-[var(--rls-radius-pill)] bg-[var(--rls-primary-container)] text-white rls-text-title-lg disabled:opacity-50"
          >
            {isLoading ? "Salvando..." : "Salvar nova senha"}
          </button>
        </form>
        <AuthFooter text="Já alterou sua senha?" linkText="Entrar" onLinkClick={() => router.push("/login")} />
      </AuthCard>
    </div>
  )
}
