"use client"

import { SettingsView } from "@/components/release"
import { mockProfile } from "@/components/release/__preview__/mock-data"

export default function ConfiguracoesPreview() {
  return (
    <SettingsView
      profile={mockProfile}
      onNavigate={() => {}}
    />
  )
}
