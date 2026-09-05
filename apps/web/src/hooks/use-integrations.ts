"use client"

import { useCallback, useRef, useState } from "react"
import axios from "axios"
import { useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query"
import apiClient from "@/lib/api-client"

export type IntegrationChannel = "whatsapp" | "telegram"

export interface LinkTokenResponse {
  token: string
  expires_at: string
  deeplink_whatsapp: string | null
  deeplink_telegram: string | null
  manual_command_whatsapp: string
  manual_command_telegram: string
}

export interface IntegrationStatus {
  whatsapp_linked: boolean
  telegram_linked: boolean
  phone_number: string | null
}

const PAIRING_POLL_TICKS = 30
const PAIRING_POLL_MS = 3000

let pairingPollCleanup: (() => void) | null = null

/** Invalidate integration status periodically so the UI picks up linking without the pairing modal. */
export function startIntegrationPairingPoll(queryClient: QueryClient) {
  pairingPollCleanup?.()
  let ticks = 0
  const id = setInterval(() => {
    ticks += 1
    void queryClient.invalidateQueries({ queryKey: ["integrations", "status"] })
    if (ticks >= PAIRING_POLL_TICKS) {
      clearInterval(id)
      pairingPollCleanup = null
    }
  }, PAIRING_POLL_MS)
  pairingPollCleanup = () => {
    clearInterval(id)
    pairingPollCleanup = null
  }
}

/** Normalize API payloads that may use camelCase or snake_case field names. */
export function normalizeLinkTokenPayload(data: LinkTokenResponse & Record<string, unknown>): LinkTokenResponse {
  const d = data as Record<string, unknown>
  return {
    token: String(d.token ?? ""),
    expires_at: String(d.expires_at ?? ""),
    deeplink_whatsapp: (d.deeplink_whatsapp ?? d.deeplinkWhatsapp ?? null) as string | null,
    deeplink_telegram: (d.deeplink_telegram ?? d.deeplinkTelegram ?? null) as string | null,
    manual_command_whatsapp: String(d.manual_command_whatsapp ?? d.manualCommandWhatsapp ?? ""),
    manual_command_telegram: String(d.manual_command_telegram ?? d.manualCommandTelegram ?? ""),
  }
}

export async function fetchIntegrationLinkToken(channel: IntegrationChannel): Promise<LinkTokenResponse> {
  const { data } = await apiClient.post<LinkTokenResponse & Record<string, unknown>>(
    "/integrations/link-token",
    { channel }
  )
  return normalizeLinkTokenPayload(data as LinkTokenResponse & Record<string, unknown>)
}

type ApiErrorPayload = { error?: { code?: string; message?: string } }

/** True when API refused pairing because BOT_WHATSAPP_NUMBER / BOT_TELEGRAM_USERNAME is missing. */
export function isIntegrationBotNotConfigured(err: unknown): boolean {
  if (!axios.isAxiosError(err)) return false
  const payload = err.response?.data as ApiErrorPayload | undefined
  return payload?.error?.code === "INTEGRATION_BOT_NOT_CONFIGURED"
}

/** Message for logs / admin tooling when link-token fails. */
export function getIntegrationLinkErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const payload = err.response?.data as ApiErrorPayload | undefined
    const msg = payload?.error?.message
    const code = payload?.error?.code
    if (code === "INTEGRATION_BOT_NOT_CONFIGURED" && msg) return msg
  }
  return "Não foi possível gerar o código. Tente de novo."
}

/**
 * POST link-token, open WhatsApp/Telegram with prefilled message (deeplink).
 * Starts a short background poll on integration status.
 * No user-visible toasts (silent failure paths).
 */
export async function openIntegrationChat(
  channel: IntegrationChannel,
  queryClient: QueryClient
): Promise<void> {
  const data = await fetchIntegrationLinkToken(channel)
  const deeplink = channel === "whatsapp" ? data.deeplink_whatsapp : data.deeplink_telegram

  void queryClient.invalidateQueries({ queryKey: ["integrations", "status"] })
  startIntegrationPairingPoll(queryClient)

  if (!deeplink) {
    throw new Error("Deeplink não disponível. Verifique se o bot está configurado no servidor.")
  }

  const w = window.open(deeplink, "_blank", "noopener,noreferrer")
  if (!w || w.closed) {
    console.warn("[integrations] browser blocked chatbot tab")
  }
}

export function useIntegrationStatus(pollWhileOpen: boolean) {
  return useQuery<IntegrationStatus>({
    queryKey: ["integrations", "status"],
    queryFn: async () => {
      const { data } = await apiClient.get<IntegrationStatus>("/integrations/status")
      return data
    },
    refetchInterval: pollWhileOpen ? 3000 : false,
  })
}

/** Wrapper with loading state for buttons (sidebar, dashboard). */
export function useOpenIntegrationChat() {
  const queryClient = useQueryClient()
  const [openingChannel, setOpeningChannel] = useState<IntegrationChannel | null>(null)
  const openingRef = useRef<IntegrationChannel | null>(null)

  const run = useCallback(
    async (channel: IntegrationChannel) => {
      if (openingRef.current) return
      openingRef.current = channel
      setOpeningChannel(channel)
      try {
        await openIntegrationChat(channel, queryClient)
      } catch (e) {
        console.error("[integrations] open chat failed", e)
      } finally {
        openingRef.current = null
        setOpeningChannel(null)
      }
    },
    [queryClient]
  )

  return { openIntegrationChat: run, openingChannel }
}
