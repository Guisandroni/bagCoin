"use client"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"
import {
  useConversations,
  useConversation,
  useCreateConversation,
  type Conversation,
  type Message,
} from "@/hooks/use-conversations"
import { Plus, MessageSquare, AlertCircle, ChevronLeft, User, Bot, Bell } from "lucide-react"
import Link from "next/link"
import { AssetRow } from "@/components/coinbase"

const dateFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
})

const shortDateFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
})

function MessageBubble({ message }: { message: Message }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = message.content.length > 300
  const isUser = message.role === "user"
  const isAssistant = message.role === "assistant"

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <Avatar
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm ${
          isUser
            ? "bg-primary/10 text-primary"
            : isAssistant
              ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
              : "bg-muted text-muted-foreground"
        }`}
      >
        {isUser ? (
          <User className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4" />
        )}
      </Avatar>

      <div className={`flex max-w-[80%] flex-col ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-foreground"
          }`}
        >
          {isLong && !expanded ? (
            <>
              <p className="whitespace-pre-wrap">{message.content.slice(0, 300)}...</p>
              <button
                onClick={() => setExpanded(true)}
                className="mt-1 text-xs font-medium text-brand hover:underline"
              >
                Ver mais
              </button>
            </>
          ) : (
            <p className="whitespace-pre-wrap">{message.content}</p>
          )}
          {isLong && expanded && (
            <button
              onClick={() => setExpanded(false)}
              className="mt-1 text-xs font-medium text-muted-foreground hover:underline"
            >
              Ver menos
            </button>
          )}
        </div>

        <div className="mt-1 flex items-center gap-2 px-1">
          <Badge
            variant="secondary"
            className={`text-[10px] px-1.5 py-0 ${
              isUser
                ? "bg-primary/10 text-primary"
                : isAssistant
                  ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
                  : ""
            }`}
          >
            {isUser ? "Você" : isAssistant ? "Assistente" : "Sistema"}
          </Badge>
          <span className="text-[10px] text-muted-foreground">
            {new Date(message.created_at).toLocaleTimeString("pt-BR", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
      </div>
    </div>
  )
}

function ConversationSidebar({
  conversations,
  selectedId,
  onSelect,
  isLoading,
}: {
  conversations: Conversation[]
  selectedId: string | null
  onSelect: (id: string) => void
  isLoading: boolean
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between p-4 pb-2">
        <h2 className="text-sm font-semibold">Conversas</h2>
        <span className="text-xs text-muted-foreground">{conversations.length}</span>
      </div>

      <ScrollArea className="flex-1 px-2">
        {isLoading ? (
          <div className="space-y-2 p-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 rounded-xl p-3">
                <Skeleton className="h-8 w-8 rounded-full" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="h-4 w-32 rounded" />
                  <Skeleton className="h-3 w-20 rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <MessageSquare className="text-muted-foreground mb-3 h-10 w-10" />
            <p className="text-sm font-medium text-muted-foreground">Nenhuma conversa</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Inicie uma nova conversa com o assistente.
            </p>
          </div>
        ) : (
          <div className="space-y-2 px-1 pb-2">
            {conversations.map((conv) => (
              <AssetRow
                key={conv.id}
                className={selectedId === conv.id ? "border-primary ring-1 ring-primary/30" : undefined}
                icon={<MessageSquare className="h-5 w-5 text-primary" />}
                title={conv.title || "Conversa sem título"}
                subtitle={`Atual. ${shortDateFormatter.format(new Date(conv.updated_at))}`}
                onClick={() => onSelect(conv.id)}
              />
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}

export default function ConfirmacoesPage() {
  const { data: convData, isLoading: isListLoading, error: listError } = useConversations()
  const createConversation = useCreateConversation()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  const conversations = convData?.items ?? []
  const { data: conversationDetail, isLoading: isDetailLoading } =
    useConversation(selectedId)
  const messages = conversationDetail?.messages ?? []

  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Auto-select first conversation on load
  useEffect(() => {
    if (!isListLoading && conversations.length > 0 && !selectedId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedId(conversations[0].id)
    }
  }, [isListLoading, conversations, selectedId])

  // When a new conversation is created, select it
  useEffect(() => {
    if (createConversation.data?.id) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedId(createConversation.data.id)
    }
  }, [createConversation.data])

  const handleNewConversation = async () => {
    setCreating(true)
    try {
      await createConversation.mutateAsync()
    } catch {
      // handled by hook toast
    } finally {
      setCreating(false)
    }
  }

  const selectedConversation = conversations.find((c) => c.id === selectedId)

  // Error state (full page)
  if (listError && !isListLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Card className="w-full max-w-md">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="text-destructive mb-4 h-12 w-12" />
            <p className="text-lg font-medium">Erro ao carregar conversas</p>
            <p className="text-muted-foreground mt-1 text-sm text-center">
              {(listError as Error).message || "Não foi possível carregar as conversas. Tente novamente mais tarde."}
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col lg:h-[calc(100vh-5rem)]">
      {/* Mobile header */}
      <div className="flex items-center gap-2 border-b border-border/60 p-4 lg:hidden">
        {selectedId && (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={() => setSelectedId(null)}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
        )}
        <h1 className="text-lg font-bold">Confirmações</h1>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar - hidden on mobile when a conversation is selected */}
        <aside
          className={`w-full shrink-0 border-r border-border/60 lg:w-72 lg:block ${
            selectedId ? "hidden" : "block"
          } lg:block`}
        >
          <div className="hidden items-center justify-between border-b border-border/60 p-4 lg:flex">
            <h1 className="text-lg font-bold">Confirmações</h1>
          </div>
          <div className="flex h-full flex-col">
            <div className="px-4 pb-3 pt-2">
              <Button
                className="w-full"
                size="sm"
                onClick={handleNewConversation}
                disabled={creating}
              >
                <Plus className="mr-1.5 h-4 w-4" />
                {creating ? "Criando..." : "Nova Conversa"}
              </Button>
            </div>
            <Separator />
            <div className="flex-1 overflow-hidden">
              <ConversationSidebar
                conversations={conversations}
                selectedId={selectedId}
                onSelect={setSelectedId}
                isLoading={isListLoading}
              />
            </div>
          </div>
        </aside>

        {/* Main content - messages */}
        <main
          className={`flex flex-1 flex-col overflow-hidden ${
            !selectedId ? "hidden lg:flex" : "flex"
          }`}
        >
          {!selectedId ? (
            <div className="flex flex-1 items-center justify-center">
              <div className="text-center">
                <MessageSquare className="text-muted-foreground mx-auto mb-4 h-16 w-16" />
                <h2 className="text-lg font-medium">Selecione uma conversa</h2>
                <p className="text-muted-foreground mt-1 text-sm">
                  Escolha uma conversa ao lado ou crie uma nova.
                </p>
              </div>
            </div>
          ) : isDetailLoading ? (
            <div className="flex flex-1 flex-col gap-4 p-6">
              <div className="flex items-center gap-3">
                <Skeleton className="h-8 w-8 rounded-full" />
                <div className="space-y-1">
                  <Skeleton className="h-4 w-48 rounded" />
                  <Skeleton className="h-3 w-24 rounded" />
                </div>
              </div>
              <Separator />
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className={`flex gap-3 ${i % 2 === 0 ? "" : "flex-row-reverse"}`}>
                  <Skeleton className="h-8 w-8 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-20 w-full max-w-md rounded-2xl" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <>
              {/* Conversation header */}
              <div className="flex items-center gap-2 border-b border-border/60 px-4 py-3">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-10 w-10 shrink-0 lg:hidden"
                  onClick={() => setSelectedId(null)}
                  aria-label="Voltar às conversas"
                >
                  <ChevronLeft className="h-5 w-5" />
                </Button>
                <div className="flex min-w-0 flex-1 items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10">
                    <MessageSquare className="h-5 w-5 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <h2 className="truncate text-[15px] font-semibold">
                      {selectedConversation?.title || "Conversa sem título"}
                    </h2>
                    <p className="text-[11px] text-muted-foreground">
                      {selectedConversation
                        ? dateFormatter.format(new Date(selectedConversation.created_at))
                        : ""}
                    </p>
                  </div>
                </div>
                <Link
                  href="/app/confirmacoes"
                  className="touch-target flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-muted-foreground hover:bg-muted"
                  aria-label="Centro de confirmações"
                >
                  <Bell className="h-5 w-5" />
                </Link>
              </div>

              {/* Messages area */}
              <ScrollArea className="flex-1 p-6">
                {messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <Bot className="text-muted-foreground mb-3 h-12 w-12" />
                    <p className="text-sm font-medium text-muted-foreground">
                      Nenhuma mensagem nesta conversa
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      As mensagens aparecerão aqui quando você interagir com o assistente.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-5">
                    {messages.map((msg) => (
                      <MessageBubble key={msg.id} message={msg} />
                    ))}
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </ScrollArea>
            </>
          )}
        </main>
      </div>
    </div>
  )
}
