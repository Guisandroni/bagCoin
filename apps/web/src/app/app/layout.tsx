import { Suspense } from "react"
import { AuthGuard } from "@/components/auth/auth-guard"
import { Modals } from "@/components/modals/modals"
import { PageTransition } from "@/components/layout/page-transition"
import { SettingsDrawer } from "@/components/layout/shared/settings-drawer"
import { FinancialRouteRefresher } from "./financial-route-refresher"
import Loading from "./loading"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AuthGuard>
      <Suspense fallback={<Loading />}>
        <PageTransition>{children}</PageTransition>
      </Suspense>
      <FinancialRouteRefresher />
      <Modals />
      <SettingsDrawer />
    </AuthGuard>
  )
}
