"use client"

import { usePathname, useRouter } from "next/navigation"
import { useAppStore } from "@/lib/store"
import { SettingsView } from "@/components/release/settings-view"
import { getReleaseProfile } from "@/lib/adapters"
import { useOpenIntegrationChat } from "@/hooks/use-integrations"

export function SettingsDrawer() {
  const { drawerOpen, closeDrawer } = useAppStore()
  const router = useRouter()
  const pathname = usePathname()
  const profile = getReleaseProfile()
  const { openIntegrationChat, openingChannel } = useOpenIntegrationChat()

  const handleNavigate = (s: string) => {
    const routes: Record<string, string> = {
      inicio: "/app",
      transacoes: "/app/transacoes",
      categorias: "/app/categorias",
      orcamentos: "/app/orcamentos",
      metas: "/app/metas",
      perfil: "/app/perfil",
      suporte: "/app/suporte",
    }

    if (s === "whatsapp" || s === "telegram") {
      closeDrawer()
      void openIntegrationChat(s)
      return
    }

    closeDrawer()
    router.push(routes[s] ?? "/app/configuracoes")
  }

  if (!drawerOpen) return null

  return (
    <>
      <button
        type="button"
        aria-label="Fechar menu"
        className="rls-drawer-backdrop"
        onClick={closeDrawer}
      />
      <aside
        aria-label="Menu"
        className="rls rls-drawer-panel"
      >
        <SettingsView
          profile={profile}
          onNavigate={handleNavigate}
          openingChannel={openingChannel}
          activeSection={getActiveSection(pathname)}
        />
      </aside>
    </>
  )
}

function getActiveSection(pathname: string): string {
  if (pathname === "/app") return "inicio"
  if (pathname.startsWith("/app/transacoes")) return "transacoes"
  if (pathname.startsWith("/app/categorias")) return "categorias"
  if (pathname.startsWith("/app/orcamentos")) return "orcamentos"
  if (pathname.startsWith("/app/metas")) return "metas"
  if (pathname.startsWith("/app/perfil")) return "perfil"
  if (pathname.startsWith("/app/suporte")) return "suporte"
  return ""
}
