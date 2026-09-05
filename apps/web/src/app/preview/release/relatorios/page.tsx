"use client"

import { ReportsView } from "@/components/release"
import { mockReportAnalytics } from "@/components/release/__preview__/mock-data"

export default function RelatoriosPreview() {
  return (
    <ReportsView
      analytics={mockReportAnalytics}
      onOpenDrawer={() => {}}
    />
  )
}
