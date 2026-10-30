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
} from "lucide-react"
import { cn } from "@/lib/utils"
import { BRAND, NAV_ITEMS } from "@/lib/constants"
import { useAuthStore } from "@/lib/auth-store"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
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

export function TabletSidebar() {
  const pathname = usePathname()
  const { user, logout } = useAuthStore()
  const openDrawer = useAppStore((s) => s.openDrawer)
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
        : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
    )

  return (
    <aside className="relative z-20 hidden shrink-0 w-[72px] flex-col border-r border-sidebar-border bg-sidebar transition-all duration-200 md:flex lg:hidden">
      <div className="flex items-center justify-center px-3 py-5">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-xs font-bold text-primary-foreground">
          bC
        </span>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 overflow-x-hidden px-2 pt-1">
        {NAV_ITEMS.slice(0, 2).map((item) => {
          const Icon = iconMap[item.icon]
          const href = item.id === "dashboard" ? "/app" : `/app/${item.id}`
          return (
            <Link key={item.id} href={href} title={item.label} className={navLinkClass(isActive(item.id))}>
              {Icon && <Icon className="h-[18px] w-[18px] shrink-0" />}
            </Link>
          )
        })}

        {NAV_ITEMS.slice(2, 5).map((item) => {
          const Icon = iconMap[item.icon]
          return (
            <Link key={item.id} href={`/app/${item.id}`} title={item.label} className={navLinkClass(isActive(item.id))}>
              {Icon && <Icon className="h-[18px] w-[18px] shrink-0" />}
            </Link>
          )
        })}

        {NAV_ITEMS.slice(5, 7).map((item) => {
          const Icon = iconMap[item.icon]
          return (
            <Link key={item.id} href={`/app/${item.id}`} title={item.label} className={navLinkClass(isActive(item.id))}>
              {Icon && <Icon className="h-[18px] w-[18px] shrink-0" />}
            </Link>
          )
        })}

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
        </button>

        <Link href="/app/contas" title="Contas" className={navLinkClass(pathname.startsWith("/app/contas"))}>
          <CreditCard className="h-[18px] w-[18px] shrink-0" />
        </Link>

        <button
          type="button"
          onClick={() => openDrawer()}
          className={navLinkClass(pathname.startsWith("/app/configuracoes"))}
          title="Configurações"
        >
          <Settings className="h-[18px] w-[18px] shrink-0" />
        </button>
      </nav>

      <div className="border-t border-sidebar-border p-2 px-3">
        <div className="flex items-center justify-center rounded-lg px-2 py-2">
          <Avatar className="h-8 w-8 shrink-0" title={user?.full_name || "Usuário"}>
            <AvatarFallback className="bg-sidebar-accent text-[13px] font-semibold text-sidebar-accent-foreground">
              {initials}
            </AvatarFallback>
          </Avatar>
        </div>
      </div>
    </aside>
  )
}
