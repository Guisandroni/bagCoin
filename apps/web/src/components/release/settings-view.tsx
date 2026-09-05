"use client"

import Image from "next/image"
import {
  FolderTree,
  Home,
  LifeBuoy,
  MessageSquare,
  // Send,
  Target,
  User,
  Wallet,
  ArrowDownUp,
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { ReleaseProfile } from "./types"

interface SettingsViewProps {
  profile: ReleaseProfile
  onNavigate?: (section: string) => void
  openingChannel?: "whatsapp" | "telegram" | null
  activeSection?: string
}

export function SettingsView({
  profile,
  onNavigate,
  openingChannel,
  activeSection,
}: SettingsViewProps) {
  const groups = [
    {
      title: "Organização",
      items: [
        { id: "inicio", label: "Início", icon: Home },
        { id: "transacoes", label: "Transações", icon: ArrowDownUp },
        { id: "categorias", label: "Categorias", icon: FolderTree },
        { id: "orcamentos", label: "Orçamentos", icon: Wallet },
        { id: "metas", label: "Metas", icon: Target },
      ],
    },
    {
      title: "Conta",
      items: [
        { id: "perfil", label: "Perfil", icon: User },
        { id: "suporte", label: "Suporte", icon: LifeBuoy },
      ],
    },
    {
      title: "Chatbot",
      items: [
        { id: "whatsapp", label: openingChannel === "whatsapp" ? "Abrindo WhatsApp..." : "WhatsApp", icon: MessageSquare },
        // { id: "telegram", label: openingChannel === "telegram" ? "Abrindo Telegram..." : "Telegram", icon: Send },
      ],
    },
  ]

  return (
    <nav className="rls flex h-full w-full flex-col bg-[var(--rls-surface-container-lowest)] text-[var(--rls-on-surface)]">
      <div className="flex-1 overflow-y-auto px-4 py-5">
        <div className="flex flex-col gap-7">
          {groups.map((group) => (
            <section key={group.title} className="flex flex-col gap-2">
              <h2 className="px-3 text-[13px] font-medium leading-5 text-[var(--rls-on-surface-variant)]">
                {group.title}
              </h2>
              <div className="flex flex-col gap-1">
                {group.items.map((item) => {
                  const Icon = item.icon
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => onNavigate?.(item.id)}
                      className={cn(
                        "flex h-11 w-full items-center gap-3 rounded-[var(--rls-radius)] px-3 text-left text-[15px] font-semibold text-[var(--rls-on-surface-variant)] transition-colors active:scale-[0.99]",
                        activeSection === item.id && "bg-[var(--rls-primary-container)]/10 text-[var(--rls-primary-container)]"
                      )}
                    >
                      <Icon className="h-5 w-5 shrink-0" />
                      <span className="min-w-0 flex-1 truncate">{item.label}</span>
                    </button>
                  )
                })}
              </div>
            </section>
          ))}
        </div>
      </div>

      <div className="border-t border-[var(--rls-outline-variant)] p-4">
        <div className="flex items-center gap-3">
          <div className="relative flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-[var(--rls-radius)] bg-[var(--rls-primary-container)]/10">
            {profile.avatarUrl ? (
              <Image
                src={profile.avatarUrl}
                alt={profile.name}
                fill
                sizes="48px"
                unoptimized
                className="object-cover"
              />
            ) : (
              <span className="text-base font-bold text-[var(--rls-primary-container)]">
                {profile.name.slice(0, 2).toUpperCase()}
              </span>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[15px] font-bold text-[var(--rls-on-surface)]">{profile.name}</p>
          </div>
        </div>
      </div>
    </nav>
  )
}
