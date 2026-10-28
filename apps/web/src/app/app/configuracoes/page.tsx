"use client"

import { Bell, Globe, Monitor, Moon, Send, Shield, Sun } from "lucide-react"
import { useTheme } from "next-themes"
import { AppBar } from "@/components/release/app-bar"
import { ListItem } from "@/components/release/list-item"
import { useAppStore } from "@/lib/store"
import { cn } from "@/lib/utils"

const appearanceOptions = [
  { value: "light", label: "Claro", icon: Sun },
  { value: "dark", label: "Escuro", icon: Moon },
  { value: "system", label: "Sistema", icon: Monitor },
] as const

export default function ConfiguracoesPage() {
  const { theme, setTheme } = useTheme()
  const toggleDrawer = useAppStore((state) => state.toggleDrawer)

  return (
    <div className="rls mx-auto min-h-dvh w-full max-w-md bg-[var(--rls-background)] pb-8 shadow-[0_0_48px_rgba(22,82,240,0.08)]">
      <AppBar title="Configurações" onOpenDrawer={toggleDrawer} />

      <main className="px-[var(--rls-container-margin)] flex flex-col gap-[var(--rls-stack-gap-lg)] pt-[var(--rls-stack-gap-md)]">
        <section className="rounded-[var(--rls-radius-lg)] bg-[var(--rls-surface-container-lowest)] p-[var(--rls-inline-padding-md)] shadow-sm">
          <p className="rls-text-label-lg mb-3 text-[var(--rls-on-surface-variant)]">
            Aparência
          </p>
          <div className="grid grid-cols-3 gap-2">
            {appearanceOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setTheme(option.value)}
                className={cn(
                  "flex h-14 items-center justify-center gap-2 rounded-[var(--rls-radius-pill)] text-sm font-semibold transition-colors",
                  theme === option.value
                    ? "test-bg-primary bg-[var(--rls-primary-container)] text-white"
                    : "test-bg-secondary bg-[var(--rls-surface-container)] text-[var(--rls-on-surface-variant)]"
                )}
              >
                <option.icon className="h-4 w-4" />
                {option.label}
              </button>
            ))}
          </div>
        </section>

        <section className="flex flex-col gap-2">
          <p className="rls-text-label-lg px-1 text-[var(--rls-on-surface-variant)]">
            Preferências
          </p>
          <ListItem
            icon={<Globe className="h-5 w-5 text-[var(--rls-primary-container)]" />}
            iconBg="bg-[var(--rls-primary-container)]/10"
            title="Idioma"
            description="Português (Brasil)"
          />
          <ListItem
            icon={<Bell className="h-5 w-5 text-[var(--rls-secondary)]" />}
            iconBg="bg-[var(--rls-secondary-container)]/20"
            title="Notificações"
            description="Alertas de transações e metas"
          />
          <ListItem
            icon={<Shield className="h-5 w-5 text-[var(--rls-error)]" />}
            iconBg="bg-[var(--rls-error-container)]"
            title="Privacidade"
            description="Dados e permissões"
          />
        </section>

        <section className="flex flex-col gap-2">
          <p className="rls-text-label-lg px-1 text-[var(--rls-on-surface-variant)]">
            WhatsApp
          </p>
          <ListItem
            icon={<Send className="h-5 w-5 text-[var(--rls-primary-container)]" />}
            iconBg="bg-[var(--rls-primary-container)]/10"
            title="Conexão ativa"
            description="Todos os lançamentos são detectados automaticamente"
          />
        </section>
      </main>
    </div>
  )
}
