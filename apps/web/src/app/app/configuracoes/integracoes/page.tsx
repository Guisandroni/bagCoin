"use client"

import { useState } from "react"
import Link from "next/link"
import { MessageSquare, Loader2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button, buttonVariants } from "@/components/ui/button"
import { ConnectIntegrationModal } from "@/components/integrations/connect-modal"
import { useIntegrationStatus, useOpenIntegrationChat } from "@/hooks/use-integrations"
import { cn } from "@/lib/utils"

export default function IntegracoesPage() {
  const [modal, setModal] = useState<{
    open: boolean
    channel: "whatsapp"
    nonce: number
  }>({
    open: false,
    channel: "whatsapp",
    nonce: 0,
  })
  const { data: status, isLoading } = useIntegrationStatus(false)
  const { openIntegrationChat, openingChannel } = useOpenIntegrationChat()

  return (
    <div className="page-in space-y-6 pb-28 lg:pb-10">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="section-title">Integrações</h1>
          <p className="mt-1 text-[14px] text-muted-foreground">
            Conecte WhatsApp para lançar pelo chat.
          </p>
        </div>
        <Link
          href="/app/configuracoes"
          className={cn(buttonVariants({ variant: "outline" }), "rounded-full")}
        >
          Voltar
        </Link>
      </div>

      <div className="rounded-2xl border border-border bg-card p-4">
        <p className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Resumo</p>
        {isLoading ? (
          <p className="mt-2 text-sm text-muted-foreground">Carregando…</p>
        ) : (
          <ul className="mt-2 space-y-1 text-[14px]">
            <li>
              WhatsApp:{" "}
              <span className="font-medium">{status?.whatsapp_linked ? "conectado" : "não conectado"}</span>
            </li>
            {status?.phone_number ? (
              <li className="text-muted-foreground">
                ID: <code className="rounded bg-muted px-1 text-foreground">{status.phone_number}</code>
              </li>
            ) : null}
          </ul>
        )}
      </div>

      <div className="space-y-3">
        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-muted">
                <MessageSquare className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="font-semibold">WhatsApp</p>
                <p className="text-[13px] text-muted-foreground">Lançamentos pelo app de mensagens</p>
              </div>
            </div>
            <Badge
              className={
                status?.whatsapp_linked
                  ? "border-0 bg-success/15 text-success hover:bg-success/20"
                  : "bg-muted"
              }
            >
              {status?.whatsapp_linked ? "Conectado" : "Não conectado"}
            </Badge>
          </div>
          <Button
            className="mt-4 w-full rounded-full font-semibold"
            disabled={openingChannel !== null}
            onClick={() => {
              if (status?.whatsapp_linked) {
                setModal({ open: true, channel: "whatsapp", nonce: Date.now() })
              } else {
                void openIntegrationChat("whatsapp")
              }
            }}
          >
            {openingChannel === "whatsapp" ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Abrindo…
              </>
            ) : status?.whatsapp_linked ? (
              "Gerenciar conexão"
            ) : (
              "Conectar WhatsApp"
            )}
          </Button>
        </div>

      </div>

      <ConnectIntegrationModal
        key={`${modal.channel}-${modal.nonce}`}
        open={modal.open}
        onOpenChange={(o) => setModal((m) => ({ ...m, open: o }))}
        defaultChannel={modal.channel}
        openNonce={modal.nonce}
        manageMode
      />
    </div>
  )
}
