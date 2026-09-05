"use client"

import { LoginCard } from "@/components/release"
import { GoogleProvider } from "@/components/auth/google-provider"

export default function LoginPreviewClient() {
  return (
    <GoogleProvider>
      <LoginCard
        onLogin={() => {}}
        onGoogleLogin={() => {}}
        onRegisterClick={() => {}}
        onForgotPassword={() => {}}
      />
    </GoogleProvider>
  )
}
