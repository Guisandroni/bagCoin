"use client"

import { useState } from "react"
import { toast } from "sonner"
import { AppBar } from "@/components/release/app-bar"
import { PillInput } from "@/components/release/pill-input"
import { Textarea } from "@/components/ui/textarea"
import { api } from "@/lib/api-client"
import { useAppStore } from "@/lib/store"

export default function SuportePage() {
  const toggleDrawer = useAppStore((state) => state.toggleDrawer)
  const [isSendingSupport, setIsSendingSupport] = useState(false)
  const [supportSubject, setSupportSubject] = useState("")
  const [supportMessage, setSupportMessage] = useState("")

  return (
    <div className="rls mx-auto min-h-dvh w-full max-w-md bg-[var(--rls-background)] pb-8 shadow-[0_0_48px_rgba(22,82,240,0.08)]">
      <AppBar title="Suporte" onOpenDrawer={toggleDrawer} />

      <main className="px-[var(--rls-container-margin)] flex flex-col gap-[var(--rls-stack-gap-lg)] pt-[var(--rls-stack-gap-md)]">
        <section className="rounded-[var(--rls-radius-lg)] bg-[var(--rls-surface-container-lowest)] p-[var(--rls-inline-padding-md)] shadow-sm">
          <form
            className="flex flex-col gap-3"
            onSubmit={async (event) => {
              event.preventDefault()
              const subject = supportSubject.trim()
              const message = supportMessage.trim()
              if (subject.length < 3) {
                toast.error("Informe um assunto com pelo menos 3 caracteres.")
                return
              }
              if (message.length < 10) {
                toast.error("Informe uma mensagem com pelo menos 10 caracteres.")
                return
              }
              setIsSendingSupport(true)
              try {
                await api.post("/support/contact", {
                  subject,
                  message,
                })
                setSupportSubject("")
                setSupportMessage("")
                toast.success("Mensagem enviada ao suporte.")
              } catch (error) {
                void error
                toast.error("Não foi possível enviar sua mensagem. Tente novamente em instantes.")
              } finally {
                setIsSendingSupport(false)
              }
            }}
          >
            <PillInput
              label="Assunto"
              placeholder="Como podemos ajudar?"
              required
              minLength={3}
              maxLength={120}
              value={supportSubject}
              onChange={(event) => setSupportSubject(event.target.value)}
            />
            <Textarea
              aria-label="Mensagem para o suporte"
              className="min-h-32 rounded-[var(--rls-radius-lg)] border-[var(--rls-outline-variant)] bg-[var(--rls-surface-container)]"
              placeholder="Descreva o problema ou dúvida."
              required
              minLength={10}
              maxLength={4000}
              value={supportMessage}
              onChange={(event) => setSupportMessage(event.target.value)}
            />
            <button
              type="submit"
              disabled={isSendingSupport || !supportSubject.trim() || !supportMessage.trim()}
              className="h-12 rounded-[var(--rls-radius-pill)] bg-[var(--rls-primary-container)] text-white font-semibold disabled:opacity-50"
            >
              {isSendingSupport ? "Enviando..." : "Enviar mensagem"}
            </button>
          </form>
        </section>
      </main>
    </div>
  )
}
