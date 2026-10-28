import { create } from "zustand"
import type { Transaction, ModalType, FilterState } from "@/types"

interface AppStore {
  transactions: Transaction[]
  activeModal: ModalType
  selectedTransaction: Transaction | null
  sidebarCollapsed: boolean
  filter: FilterState
  drawerOpen: boolean

  setFilter: (filter: Partial<FilterState>) => void
  resetFilter: () => void
  openModal: (modal: ModalType, transaction?: Transaction) => void
  closeModal: () => void
  setTransactions: (transactions: Transaction[]) => void
  openDrawer: () => void
  closeDrawer: () => void
  toggleDrawer: () => void
  toggleSidebar: () => void
}

const defaultFilter: FilterState = {
  type: "all",
  categories: [
    "Alimentação",
    "Transporte",
    "Moradia",
    "Saúde",
    "Lazer",
    "Educação",
    "Compras",
    "Salário",
  ],
  searchQuery: "",
}

export const useAppStore = create<AppStore>((set) => ({
  transactions: [],
  activeModal: null,
  selectedTransaction: null,
  sidebarCollapsed: false,
  filter: { ...defaultFilter },
  drawerOpen: false,

  setFilter: (partial) =>
    set((state) => ({
      filter: { ...state.filter, ...partial },
    })),

  resetFilter: () => set({ filter: { ...defaultFilter } }),

  openModal: (modal, transaction) =>
    set({
      activeModal: modal,
      selectedTransaction: transaction ?? null,
    }),

  closeModal: () =>
    set({
      activeModal: null,
      selectedTransaction: null,
    }),

  setTransactions: (transactions) => set({ transactions }),

  openDrawer: () => set({ drawerOpen: true }),
  closeDrawer: () => set({ drawerOpen: false }),
  toggleDrawer: () => set((state) => ({ drawerOpen: !state.drawerOpen })),
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
}))
