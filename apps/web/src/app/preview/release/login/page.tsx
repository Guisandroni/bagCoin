"use client"

import dynamic from "next/dynamic"

const LoginPreviewClient = dynamic(() => import("./login-preview-client"), {
  ssr: false,
})

export default function LoginPreview() {
  return <LoginPreviewClient />
}
