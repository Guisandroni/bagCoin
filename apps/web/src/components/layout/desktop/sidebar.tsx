"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutGrid,
  List,
  BarChart3,
  Target,
  MessageSquare,
  FileText,
  Wallet,
  Settings,
  LogOut,
  Loader2,
  CreditCard,
  PanelLeft,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { BRAND, NAV_ITEMS } from "@/lib/constants"
import { useAuthStore } from "@/lib/auth-store"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
// import { useOpenIntegrationChat } from "@/hooks/use-integrations"
import { useWhatsAppConnect } from "@/hooks/use-whatsapp-connect"

import { useAppStore } from "@/lib/store"

const iconMap: Record<string, React.ElementType> = {
  LayoutGrid,
  List,
  BarChart3,
  Target,
  MessageSquare,
  FileText,
  Wallet,
  Settings,
  CreditCard,
}

export function Sidebar() {
  const pathname = usePathname()
  const { user, logout } = useAuthStore()
  const openDrawer = useAppStore((s) => s.openDrawer)
  const sidebarCollapsed = useAppStore((s) => s.sidebarCollapsed)
  const toggleSidebar = useAppStore((s) => s.toggleSidebar)
  // const { openIntegrationChat } = useOpenIntegrationChat()
  const { isLinked: whatsappLinked, isConnecting: whatsappConnecting, connect: connectWhatsApp } = useWhatsAppConnect()

  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : user?.email?.[0]?.toUpperCase() || "U"

  const isActive = (id: string) =>
    id === "dashboard" ? pathname === "/app" : pathname.startsWith(`/app/${id}`)

  const navLinkClass = (active: boolean) =>
    cn(
      "flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-[13px] font-medium transition-colors",
      active
        ? "bg-primary text-primary-foreground"
        : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground active:bg-sidebar-accent"
    )

  return (
    <aside
      className={cn(
        "relative z-20 hidden shrink-0 flex-col border-r border-sidebar-border bg-sidebar transition-all duration-200 lg:flex",
        sidebarCollapsed ? "w-[var(--sidebar-collapsed-w)]" : "w-[var(--sidebar-w)]"
      )}
    >
      <div className="flex items-center gap-2 px-3 py-5">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-xs font-bold text-primary-foreground">
          bC
        </span>
        {!sidebarCollapsed && (
          <Link href="/app" className="min-w-0 font-semibold tracking-tight">
            <span className="text-primary">{BRAND.pre}</span>
            <span className="text-sidebar-foreground">{BRAND.suf}</span>
          </Link>
        )}
        <button
          type="button"
          onClick={toggleSidebar}
          className="ml-auto rounded-md p-1 text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
          title={sidebarCollapsed ? "Expandir" : "Recolher"}
        >
          <PanelLeft className="h-4 w-4" />
        </button>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 overflow-x-hidden px-2 pt-1">
        {!sidebarCollapsed && (
          <p className="px-2 pb-1 pt-3 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/70">
            Organização
          </p>
        )}
        {NAV_ITEMS.slice(0, 2).map((item) => {
          const Icon = iconMap[item.icon]
          const href = item.id === "dashboard" ? "/app" : `/app/${item.id}`
          return (
            <Link key={item.id} href={href} title={item.label} className={navLinkClass(isActive(item.id))}>
              {Icon && <Icon className="h-[18px] w-[18px] shrink-0" />}
              {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
            </Link>
          )
        })}

        {!sidebarCollapsed && (
          <p className="px-2 pb-1 pt-3 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/70">
            Planejamento
          </p>
        )}
        {NAV_ITEMS.slice(2, 5).map((item) => {
          const Icon = iconMap[item.icon]
          return (
            <Link key={item.id} href={`/app/${item.id}`} title={item.label} className={navLinkClass(isActive(item.id))}>
              {Icon && <Icon className="h-[18px] w-[18px] shrink-0" />}
              {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
            </Link>
          )
        })}

        {!sidebarCollapsed && (
          <p className="px-2 pb-1 pt-3 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/70">Chat</p>
        )}
        {NAV_ITEMS.slice(5, 7).map((item) => {
          const Icon = iconMap[item.icon]
          return (
            <Link key={item.id} href={`/app/${item.id}`} title={item.label} className={navLinkClass(isActive(item.id))}>
              {Icon && <Icon className="h-[18px] w-[18px] shrink-0" />}
              {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
            </Link>
          )
        })}

        {!sidebarCollapsed && (
          <p className="px-2 pb-1 pt-3 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/70">Bots</p>
        )}
        <button
          type="button"
          disabled={whatsappConnecting}
          onClick={() => void connectWhatsApp()}
          title={whatsappLinked ? "WhatsApp conectado" : "Conectar WhatsApp"}
          className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-[13px] font-medium text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground disabled:opacity-60"
        >
          {whatsappConnecting ? (
            <Loader2 className="h-[18px] w-[18px] shrink-0 animate-spin" />
          ) : (
            <MessageSquare className="h-[18px] w-[18px] shrink-0" />
          )}
          {!sidebarCollapsed && <span className="truncate">WhatsApp</span>}
          {!sidebarCollapsed && (
            <span
              className={cn(
                "ml-auto h-2 w-2 rounded-full",
                whatsappLinked ? "bg-green-500" : "bg-muted-foreground/30"
              )}
              aria-label={whatsappLinked ? "Conectado" : "Desconectado"}
            />
          )}
        </button>
        {/*
        <button
          type="button"
          disabled={whatsappConnecting}
          onClick={() => void openIntegrationChat("telegram")}
          title="Telegram"
          className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-[13px] font-medium text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground disabled:opacity-60"
        >
          {whatsappConnecting ? (
            <Loader2 className="h-[18px] w-[18px] shrink-0 animate-spin" />
          ) : (
            <svg className="h-[18px] w-[18px] shrink-0" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
              <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.161c-.18 1.897-.962 6.502-1.359 8.627-.168.9-.5 1.201-.82 1.23-.697.064-1.226-.46-1.901-.903-1.056-.692-1.653-1.123-2.678-1.799-1.185-.781-.417-1.21.258-1.911.177-.184 3.247-2.977 3.307-3.23.007-.032.015-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.139-5.062 3.345-.479.329-.913.489-1.302.481-.428-.009-1.252-.242-1.865-.441-.752-.244-1.349-.374-1.297-.789.027-.216.324-.437.893-.663 3.498-1.524 5.831-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635.099-.002.321.023.465.14.121.099.154.233.17.327.016.094.036.306.02.472z" />
            </svg>
          )}
          {!sidebarCollapsed && <span className="truncate">Telegram</span>}
        </button>
        */}

        {!sidebarCollapsed && (
          <p className="px-2 pb-1 pt-3 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/70">
            Controle financeiro
          </p>
        )}
        <Link href="/app/contas" title="Contas" className={navLinkClass(pathname.startsWith("/app/contas"))}>
          <CreditCard className="h-[18px] w-[18px] shrink-0" />
          {!sidebarCollapsed && <span className="truncate">Contas</span>}
        </Link>

        {!sidebarCollapsed && (
          <p className="px-2 pb-1 pt-3 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/70">Sistema</p>
        )}
        <button
          type="button"
          onClick={() => openDrawer()}
          className={navLinkClass(pathname.startsWith("/app/configuracoes"))}
        >
          <Settings className="h-[18px] w-[18px] shrink-0" />
          {!sidebarCollapsed && <span className="truncate">Configurações</span>}
        </button>
      </nav>

      <div className="border-t border-sidebar-border p-2 px-3">
        <div className="flex items-center gap-2 rounded-lg px-2 py-2">
          <Avatar className="h-8 w-8 shrink-0">
            <AvatarFallback className="bg-sidebar-accent text-[13px] font-semibold text-sidebar-accent-foreground">
              {initials}
            </AvatarFallback>
          </Avatar>
          {!sidebarCollapsed && (
            <>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13px] font-semibold">{user?.full_name || "Usuário"}</p>
                <p className="truncate text-[11px] text-muted-foreground">{user?.email || ""}</p>
              </div>
              <Button variant="ghost" size="icon" className="h-9 w-9 shrink-0" onClick={logout} title="Sair" type="button">
                <LogOut className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>
      </div>
    </aside>
  )
}
