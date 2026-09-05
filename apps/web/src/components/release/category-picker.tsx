"use client"

import { useState } from "react"
import { ChevronDown, Search } from "lucide-react"
import { cn } from "@/lib/utils"
import type { ReleaseCategory } from "./types"

interface ReleaseCategoryPickerProps {
  label: string
  categories: ReleaseCategory[]
  selectedCategory: ReleaseCategory | null
  onSelect: (category: ReleaseCategory) => void
  collapsible?: boolean
}

export function ReleaseCategoryPicker({
  label,
  categories,
  selectedCategory,
  onSelect,
  collapsible = false,
}: ReleaseCategoryPickerProps) {
  const [search, setSearch] = useState("")
  const [expanded, setExpanded] = useState(!collapsible)
  const availableCategories = categories.filter((category) => category.id)
  const normalizedSearch = normalizeSearch(search)
  const filteredCategories = availableCategories.filter((category) =>
    normalizeSearch(category.name).includes(normalizedSearch)
  )

  return (
    <div className="flex flex-col gap-2">
      <span className="rls-text-label-lg ml-4 text-[var(--rls-on-background)]">
        {label}
      </span>

      <div className="rounded-[var(--rls-radius)] border border-[var(--rls-outline-variant)] bg-[var(--rls-surface-container-lowest)] shadow-sm">
        {!collapsible ? (
          <button
            type="button"
            className="flex h-14 w-full items-center justify-between rounded-[var(--rls-radius)] px-4 text-left text-base text-[var(--rls-on-surface)]"
          >
            <span className={selectedCategory ? "" : "text-[var(--rls-on-surface-variant)]/60"}>
              {selectedCategory?.name ?? "Selecionar categoria..."}
            </span>
            <ChevronDown className="h-5 w-5 rotate-180 text-[var(--rls-on-surface-variant)]" />
          </button>
        ) : null}

        <div className={cn("p-3", !collapsible && "border-t border-[var(--rls-outline-variant)]")}>
          <label className="relative block">
            <span className="sr-only">Pesquisar categorias</span>
            <Search className="absolute left-1 top-1/2 h-5 w-5 -translate-y-1/2 text-[var(--rls-outline)]" />
            <input
              type="search"
              aria-label="Pesquisar categorias"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                if (collapsible) setExpanded(true)
              }}
              placeholder="Pesquisar categorias..."
              className="h-11 w-full border-0 border-b border-[var(--rls-outline-variant)] bg-transparent px-8 text-base text-[var(--rls-on-surface)] outline-none placeholder:text-[var(--rls-on-surface-variant)]/60 focus:border-[var(--rls-primary-container)]"
            />
          </label>

          {collapsible ? (
            <button
              type="button"
              onClick={() => setExpanded((value) => !value)}
              className="rls-text-label-lg mt-3 text-[var(--rls-primary)]"
            >
              {expanded ? "Ocultar categorias" : "Ver categorias"}
            </button>
          ) : null}

          {expanded ? (
          <div className="mt-3 flex max-h-44 flex-wrap gap-2 overflow-y-auto">
            {filteredCategories.length > 0 ? (
              filteredCategories.map((category) => {
                const isSelected = selectedCategory?.id === category.id
                return (
                  <button
                    key={category.id}
                    type="button"
                    onClick={() => {
                      onSelect(category)
                      setSearch(category.name)
                      if (collapsible) setExpanded(false)
                    }}
                    className={cn(
                      "flex h-9 items-center gap-1 rounded-[var(--rls-radius)] border px-3 text-sm font-semibold transition-colors",
                      isSelected
                        ? "bg-[var(--rls-primary-container)] text-white"
                        : "bg-[var(--rls-surface-container)]"
                    )}
                    style={
                      isSelected
                        ? undefined
                        : {
                            borderColor: category.color,
                            color: category.color,
                          }
                    }
                  >
                    <span aria-hidden="true">{category.icon || category.emoji || "💳"}</span>
                    {category.name}
                  </button>
                )
              })
            ) : (
              <span className="rls-text-body-md py-2 text-[var(--rls-on-surface-variant)]">
                Nenhuma categoria encontrada.
              </span>
            )}
          </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

function normalizeSearch(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
}
