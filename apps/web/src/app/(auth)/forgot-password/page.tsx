"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Mail } from "lucide-react"
import { AuthCard, AuthFooter, AuthHeader } from "@/components/release/auth-card"
import { PillInput } from "@/components/release/pill-input"
import { ToastBanner } from "@/components/release/toast-banner"
import { useAuthStore } from "@/lib/auth-store"
import { PASSWORD_RESET_SENT_MESSAGE, safePasswordResetRequestMessage } from "@/lib/toast-messages"

export default function ForgotPasswordPage() {
  const router = useRouter()
  const forgotPassword = useAuthStore((state) => state.forgotPassword)
  const isLoading = useAuthStore((state) => state.isLoading)
  const [email, setEmail] = useState("")
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  return (
    <div className="rls flex min-h-dvh flex-col items-center justify-center bg-[var(--rls-background)] p-[var(--rls-container-margin)]">
      <ToastBanner
        isOpen={!!(message || error)}
        message={message || error || ""}
        variant={error ? "error" : "success"}
        onClose={() => {
          setMessage(null)
          setError(null)
        }}
      />
      <AuthCard>
        <AuthHeader title="Redefinir senha" subtitle="Informe seu email para receber o link de redefinição." />
        <form
          className="flex w-full flex-col gap-[var(--rls-stack-gap-md)]"
          onSubmit={async (event) => {
            event.preventDefault()
            setError(null)
            setMessage(null)
            if (!email.trim()) {
              setError("Digite seu email.")
              return
            }
            try {
              await forgotPassword(email)
              setMessage(PASSWORD_RESET_SENT_MESSAGE)
            } catch (err) {
              setError(safePasswordResetRequestMessage(err))
            }
          }}
        >
          <PillInput
            label="Email"
            icon={<Mail className="h-5 w-5" />}
            placeholder="seu@email.com"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <button
            type="submit"
            disabled={isLoading}
            className="h-14 rounded-[var(--rls-radius-pill)] bg-[var(--rls-primary-container)] text-white rls-text-title-lg disabled:opacity-50"
          >
            {isLoading ? "Enviando..." : "Enviar link"}
          </button>
        </form>
        <AuthFooter text="Lembrou a senha?" linkText="Entrar" onLinkClick={() => router.push("/login")} />
      </AuthCard>
    </div>
  )
}
