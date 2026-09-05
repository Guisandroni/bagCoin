import type { Metadata } from "next"
import { ThemeProvider } from "next-themes"
import { TooltipProvider } from "@/components/ui/tooltip"
import { QueryProvider } from "@/lib/query-client"
import { Toaster } from "sonner"
import "./globals.css"
import "@/components/release/release.css"

export const metadata: Metadata = {
  title: "Bagcoin — Assistente Financeiro Pessoal",
  description: "Controle suas finanças de forma inteligente e simples",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body className="min-h-full font-sans antialiased">
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <QueryProvider>
            <TooltipProvider>
              {children}
            </TooltipProvider>
          </QueryProvider>
          <Toaster richColors position="top-right" />
        </ThemeProvider>
      </body>
    </html>
  )
}
