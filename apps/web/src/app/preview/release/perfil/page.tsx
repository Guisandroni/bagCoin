"use client"

import { ProfileView } from "@/components/release"
import { mockProfile } from "@/components/release/__preview__/mock-data"

export default function PerfilPreview() {
  return (
    <ProfileView
      profile={mockProfile}
      onBack={() => {}}
    />
  )
}
