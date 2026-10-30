"use client"

import { useEffect, useMemo, useReducer, useRef } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import {
  fetchIntegrationLinkToken,
  useIntegrationStatus,
  type IntegrationChannel,
} from "@/hooks/use-integrations"

interface ConnectIntegrationModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  defaultChannel?: IntegrationChannel
  /** Bump when opening the modal (e.g. `Date.now()`) so link-token fetches once per open. */
  openNonce: number
  /** When true, copy targets users who already linked and opened “Gerenciar conexão”. */
  manageMode?: boolean
}

function secondsUntil(iso: string): number {
  const t = new Date(iso).getTime() - Date.now()
  return Math.max(0, Math.floor(t / 1000))
}

export function ConnectIntegrationModal({
  open,
  onOpenChange,
  defaultChannel = "whatsapp",
  openNonce,
  manageMode = false,
}: ConnectIntegrationModalProps) {
  const [, bumpRemaining] = useReducer((n: number) => n + 1, 0)
  const queryClient = useQueryClient()
  const lastInvalidatedAt = useRef(0)

  const statusQuery = useIntegrationStatus(open)

  const tokenQuery = useQuery({
    queryKey: ["integrations", "link-token", defaultChannel, openNonce],
    queryFn: () => fetchIntegrationLinkToken(defaultChannel),
    enabled: open && openNonce > 0,
    staleTime: 0,
    gcTime: 0,
    retry: 1,
  })

  const tokenPayload = tokenQuery.data

  useEffect(() => {
    const at = tokenQuery.dataUpdatedAt
    if (!at || at === lastInvalidatedAt.current) return
    lastInvalidatedAt.current = at
    void queryClient.invalidateQueries({ queryKey: ["integrations", "status"] })
  }, [tokenQuery.dataUpdatedAt, queryClient])

  const ttlSeconds = 600
  const remaining = !tokenPayload ? ttlSeconds : secondsUntil(tokenPayload.expires_at)

  const progress = useMemo(() => {
    if (!tokenPayload) return 0
    return Math.min(100, Math.round(((ttlSeconds - remaining) / ttlSeconds) * 100))
  }, [tokenPayload, remaining, ttlSeconds])

  useEffect(() => {
    if (!open || !tokenPayload) return
    const id = setInterval(() => bumpRemaining(), 1000)
    return () => clearInterval(id)
  }, [open, tokenPayload, bumpRemaining])

  useEffect(() => {
    const s = statusQuery.data
    if (!open || !s) return
    if (s.whatsapp_linked) {
      onOpenChange(false)
    }
  }, [open, statusQuery.data, onOpenChange])

  const deeplinkWhatsApp = tokenPayload?.deeplink_whatsapp ?? null

  const busy = tokenQuery.isFetching

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md rounded-2xl">
        <DialogHeader>
          <DialogTitle>
            {manageMode ? "Gerenciar integração" : "Conectar WhatsApp"}
          </DialogTitle>
          <DialogDescription>
            {manageMode
              ? "Gere um novo código se precisar religar outro dispositivo. Abra o app pelo link ou copie o comando."
              : "Abra o app com o link ou copie o comando. O código expira em 10 minutos e só pode ser usado uma vez."}
          </DialogDescription>
        </DialogHeader>

        <ChannelPanel deeplink={deeplinkWhatsApp} label="WhatsApp" busy={busy} />

        {tokenPayload && (
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Expira em</span>
              <span>
                {Math.floor(remaining / 60)}:{String(remaining % 60).padStart(2, "0")}
              </span>
            </div>
            <Progress value={progress} className="h-1.5" />
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              disabled={busy}
              onClick={() => void tokenQuery.refetch().catch(() => undefined)}
            >
              Gerar novo código
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

function ChannelPanel({
  deeplink,
  label,
  busy,
}: {
  deeplink: string | null | undefined
  label: string
  busy: boolean
}) {
  const openApp = () => {
    if (!deeplink) return
    // Try window.open first; if blocked by popup, fall back to location.href
    const w = window.open(deeplink, "_blank", "noopener,noreferrer")
    if (!w || w.closed) window.location.href = deeplink
  }

  if (!deeplink) {
    return (
      <p className="text-sm text-muted-foreground">
        Bot não configurado no servidor. Peça ao administrador para definir <code className="rounded bg-muted px-1 py-0.5 text-xs">BOT_WHATSAPP_NUMBER</code>.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <Button className="w-full" size="lg" onClick={openApp} disabled={busy}>
        Abrir {label}
      </Button>
    </div>
  )
}
