"use client"

import { useEffect } from "react"
import { Button } from "@/components/ui/button"

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error("Global error:", error)
  }, [error])

  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body className="min-h-screen flex items-center justify-center bg-background font-sans">
        <div className="text-center space-y-4 p-8">
          <h1 className="text-4xl font-bold text-foreground">Erro inesperado</h1>
          <p className="text-muted-foreground max-w-md">
            Algo deu errado. Tente recarregar a página ou contate o suporte se o problema persistir.
          </p>
          {error.digest && (
            <p className="text-xs text-muted-foreground/60">
              Digest: {error.digest}
            </p>
          )}
          <Button onClick={reset} variant="default">
            Tentar novamente
          </Button>
        </div>
      </body>
    </html>
  )
}
