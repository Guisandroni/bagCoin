"use client"

import dynamic from "next/dynamic"

const RegisterPreviewClient = dynamic(() => import("./register-preview-client"), {
  ssr: false,
})

export default function RegisterPreview() {
  return <RegisterPreviewClient />
}
