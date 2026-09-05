"use client"

import { RegisterCard } from "@/components/release"
import { GoogleProvider } from "@/components/auth/google-provider"

export default function RegisterPreviewClient() {
  return (
    <GoogleProvider>
      <RegisterCard
        onRegister={() => {}}
        onGoogleRegister={() => {}}
        onLoginClick={() => {}}
      />
    </GoogleProvider>
  )
}
