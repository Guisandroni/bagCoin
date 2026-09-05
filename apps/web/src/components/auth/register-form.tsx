"use client"

import { useState, type FormEvent } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useAuthStore } from "@/lib/auth-store"
import { GoogleButton } from "./google-button"

export function RegisterForm({ compact = false }: { compact?: boolean }) {
  const router = useRouter()
  const { register, loginWithGoogle, isLoading, error, clearError } = useAuthStore()
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [phone, setPhone] = useState("")
  const [password, setPassword] = useState("")

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    try {
      const pending = await register(email, password, name || undefined, phone || undefined)
      router.push(`/verify-email?email=${encodeURIComponent(pending.email)}&source=register&sent=1`)
    } catch {
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
          <h1 className="font-heading text-3xl font-bold">Criar conta</h1>
          <p className="text-muted-foreground">Comece a gerenciar suas finanças</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="name">Nome</Label>
          <Input
            id="name"
            type="text"
            placeholder="Seu nome"
            value={name}
            onChange={(e) => {
              setName(e.target.value)
              clearError()
            }}
          />
        </div>

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
          <Label htmlFor="phone">Telefone (opcional)</Label>
          <Input
            id="phone"
            type="tel"
            placeholder="(11) 99999-9999"
            value={phone}
            onChange={(e) => {
              setPhone(e.target.value)
              clearError()
            }}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="password">Senha</Label>
          <Input
            id="password"
            type="password"
            placeholder="Mínimo 6 caracteres"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value)
              clearError()
            }}
            required
            minLength={6}
          />
        </div>

        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}

        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? "Criando conta..." : "Criar conta"}
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
        Já tem conta?{" "}
        <Link href="/login" className="font-medium text-primary hover:underline">
          Entrar
        </Link>
      </p>
    </div>
  )
}
