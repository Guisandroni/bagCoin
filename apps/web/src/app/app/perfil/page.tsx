"use client"

import { ProfileView } from "@/components/release/profile-view"
import { getReleaseProfile } from "@/lib/adapters"
import { useAuthStore } from "@/lib/auth-store"
import { useAppStore } from "@/lib/store"

export default function PerfilPage() {
  const toggleDrawer = useAppStore((state) => state.toggleDrawer)
  const logout = useAuthStore((state) => state.logout)

  return (
    <ProfileView
      profile={getReleaseProfile()}
      onOpenDrawer={toggleDrawer}
      onLogout={logout}
    />
  )
}
