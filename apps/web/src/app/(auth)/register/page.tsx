"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import dynamic from "next/dynamic"
import { RegisterCard } from "@/components/release/register-card"
import { useAuthStore } from "@/lib/auth-store"
import type { ApiClientError } from "@/lib/api-client"

const GoogleProvider = dynamic(
  () => import("@/components/auth/google-provider").then((m) => m.GoogleProvider),
  { ssr: false }
)

export default function RegisterPage() {
  const router = useRouter()
  const { register, loginWithGoogle, clearError, isLoading } = useAuthStore()
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<
    Partial<Record<"name" | "email" | "password" | "confirmPassword", string>>
  >({})

  const handleRegister = async (data: { name: string; email: string; password: string }) => {
    setErrorMessage(null)
    setFieldErrors({})
    try {
      const pending = await register(data.email, data.password, data.name)
      router.push(`/verify-email?email=${encodeURIComponent(pending.email)}&source=register&sent=1`)
    } catch (error) {
      const resolved = resolveRegisterError(error)
      setFieldErrors(resolved.fieldErrors)
      setErrorMessage(resolved.message)
    }
  }

  const handleGoogleRegister = async (idToken: string) => {
    setErrorMessage(null)
    try {
      const result = await loginWithGoogle(idToken)
      if (result.status === "pending") {
        router.push(`/verify-email?email=${encodeURIComponent(result.pending.email)}&source=google`)
        return
      }
      router.push("/app")
    } catch (error) {
      setErrorMessage(resolveAuthError(error, "Não foi possível entrar com Google."))
    }
  }

  return (
    <GoogleProvider>
      <RegisterCard
        onRegister={handleRegister}
        onGoogleRegister={handleGoogleRegister}
        onLoginClick={() => router.push("/login")}
        isLoading={isLoading}
        errorMessage={errorMessage}
        fieldErrors={fieldErrors}
        onFieldErrorClear={(field) => {
          setFieldErrors((current) => ({ ...current, [field]: undefined }))
        }}
        onDismissError={() => {
          setErrorMessage(null)
          setFieldErrors({})
          clearError()
        }}
      />
    </GoogleProvider>
  )
}

function resolveAuthError(error: unknown, fallback: string): string {
  const err = error as { response?: { data?: { error?: { message?: string }; detail?: string } }; message?: string }
  const detail = err.response?.data?.detail
  if (err.message) return err.message
  if (typeof detail === "string") return detail
  return err.response?.data?.error?.message || err.message || fallback
}

function resolveRegisterError(error: unknown): {
  message: string
  fieldErrors: Partial<Record<"name" | "email" | "password" | "confirmPassword", string>>
} {
  const err = error as ApiClientError
  const fieldErrors: Partial<Record<"name" | "email" | "password" | "confirmPassword", string>> = {}

  if (Array.isArray(err.details)) {
    for (const issue of err.details as Array<{ loc?: Array<string | number>; msg?: string }>) {
      const field = typeof issue.loc?.[1] === "string" ? issue.loc[1] : null
      if (field === "password" || field === "email" || field === "name" || field === "confirmPassword") {
        fieldErrors[field] = issue.msg || "Valor inválido"
      }
    }
  }

  const message = err.message || "Não foi possível criar sua conta. Tente novamente."
  const passwordMessage = fieldErrors.password
  const confirmPasswordMessage = fieldErrors.confirmPassword
  const preferredMessage =
    (confirmPasswordMessage
      ? "Senhas não coincidem. Confira os dois campos e tente novamente."
      : null) ||
    (passwordMessage
      ? "Senha incorreta. Use no mínimo 6 caracteres, com letra maiúscula, letra minúscula e número."
      : null) ||
    fieldErrors.email ||
    message
  return { message: preferredMessage, fieldErrors }
}
