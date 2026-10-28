"use client"

import { useState, type FormEvent } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useAuthStore } from "@/lib/auth-store"
import { GoogleButton } from "./google-button"

export function LoginForm({ compact = false }: { compact?: boolean }) {
  const router = useRouter()
  const { login, loginWithGoogle, isLoading, error, clearError } = useAuthStore()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    try {
      await login(email, password)
      router.push("/app")
    } catch (error) {
      const authError = error as Error & { code?: string; details?: { email?: string } }
      if (authError.code === "EMAIL_NOT_VERIFIED") {
        const pendingEmail = authError.details?.email || email
        router.push(`/verify-email?email=${encodeURIComponent(pendingEmail)}&source=login`)
        return
      }
      // error is set in the store
    }
  }

  async function handleGoogleSuccess(idToken: string) {
    try {
      const result = await loginWithGoogle(idToken)
      if (result.status === "pending") {
        router.push(`/verify-email?email=${encodeURIComponent(result.pending.email)}&source=google`)
        return
      }
      router.push("/app")
    } catch {
      // error is set in the store
    }
  }

  return (
    <div className="mx-auto w-full max-w-sm space-y-6">
      {!compact && (
        <div className="space-y-2 text-center">
          <h1 className="font-heading text-3xl font-bold">Entrar no BagCoin</h1>
          <p className="text-muted-foreground">Gerencie suas finanças com inteligência</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            placeholder="seu@email.com"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value)
              clearError()
            }}
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="password">Senha</Label>
          <Input
            id="password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value)
              clearError()
            }}
            required
          />
        </div>

        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}

        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? "Entrando..." : "Entrar"}
        </Button>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-background px-2 text-muted-foreground">
              ou
            </span>
          </div>
        </div>

        <GoogleButton onSuccess={handleGoogleSuccess} isLoading={isLoading} />
      </form>

      <p className="text-center text-sm text-muted-foreground">
        Não tem conta?{" "}
        <Link href="/register" className="font-medium text-primary hover:underline">
          Cadastre-se
        </Link>
      </p>
    </div>
  )
}
