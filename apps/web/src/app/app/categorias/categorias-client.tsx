"use client"

import { useState } from "react"
import { CategoriesView } from "@/components/release/categories-view"
import {
  ReleaseCreateActionModal,
  type ReleaseCreateActionPayload,
} from "@/components/release/create-action-modal"
import { ReleaseCategoryDetailModal } from "@/components/release/entity-detail-modals"
import { useCreateCategory, useDeleteCategory, useUpdateCategory } from "@/hooks/use-categories"
import { usePathname, useRouter } from "next/navigation"
import { getReleaseNavItems } from "@/lib/adapters"
import type { ReleaseCategory } from "@/components/release/types"

interface Props {
  categories: ReleaseCategory[]
  totalAllocated: number
}

export function CategoriasClient({ categories, totalAllocated }: Props) {
  const pathname = usePathname()
  const router = useRouter()
  const createCategory = useCreateCategory()
  const updateCategory = useUpdateCategory()
  const deleteCategory = useDeleteCategory()
  const [createOpen, setCreateOpen] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<ReleaseCategory | null>(null)
  const navItems = getReleaseNavItems(pathname)

  return (
    <>
      <CategoriesView
        categories={categories}
        totalAllocated={totalAllocated}
        navItems={navItems}
        onAddCategory={() => setCreateOpen(true)}
        onSelectCategory={setSelectedCategory}
        onNavigate={(href) => {
          if (href === "#settings") return
          router.push(href)
        }}
      />
      <ReleaseCategoryDetailModal
        open={!!selectedCategory}
        category={selectedCategory}
        isSaving={updateCategory.isPending}
        isDeleting={deleteCategory.isPending}
        onOpenChange={(open) => {
          if (!open) setSelectedCategory(null)
        }}
        onSave={async (data) => {
          await updateCategory.mutateAsync({
            id: data.id,
            data: {
              name: data.name,
              type: data.type,
              color: data.color,
            },
          })
          setSelectedCategory(null)
          router.refresh()
        }}
        onDelete={async (category) => {
          if (!category.id) return
          await deleteCategory.mutateAsync(category.id)
          setSelectedCategory(null)
          router.refresh()
        }}
      />
      <ReleaseCreateActionModal
        open={createOpen}
        kind="category"
        categories={categories}
        isSaving={createCategory.isPending}
        onOpenChange={setCreateOpen}
        onSubmit={async (payload: ReleaseCreateActionPayload) => {
          if (payload.kind !== "category") return
          await createCategory.mutateAsync({
            name: payload.name,
            type: payload.type,
            color: payload.color,
          })
          setCreateOpen(false)
          router.refresh()
        }}
      />
    </>
  )
}
