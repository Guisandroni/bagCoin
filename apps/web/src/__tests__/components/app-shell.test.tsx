import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { AppShell } from "@/components/layout/app-shell"

vi.mock("@/lib/auth-store", () => ({
  useAuthStore: () => ({
    user: { id: "1", email: "ana@email.com", full_name: "Ana Silva", role: "user" },
    isAuthenticated: true,
    logout: vi.fn(),
  }),
}))

vi.mock("@/lib/store", () => ({
  useAppStore: (selector?: (state: AppStoreState) => unknown) => {
    const state: AppStoreState = {
      openModal: vi.fn(),
      closeModal: vi.fn(),
      activeModal: null,
      selectedTransaction: null,
      drawerOpen: false,
      openDrawer: vi.fn(),
      closeDrawer: vi.fn(),
    }
    return selector ? selector(state) : state
  },
}))

interface AppStoreState {
  openModal: ReturnType<typeof vi.fn>
  closeModal: ReturnType<typeof vi.fn>
  activeModal: null
  selectedTransaction: null
  drawerOpen: boolean
  openDrawer: ReturnType<typeof vi.fn>
  closeDrawer: ReturnType<typeof vi.fn>
}

const mockPathname = vi.hoisted(() => "/app")
vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
}))

vi.mock("@/components/layout/desktop/sidebar", () => ({
  Sidebar: () => <aside data-testid="sidebar">Sidebar</aside>,
}))

vi.mock("@/components/layout/tablet/sidebar", () => ({
  TabletSidebar: () => null,
}))

vi.mock("@/components/layout/desktop/top-bar", () => ({
  TopBar: () => null,
}))

vi.mock("@/components/layout/tablet/top-bar", () => ({
  TabletTopBar: () => null,
}))

vi.mock("@/components/layout/mobile/header", () => ({
  MobileHeader: ({ initials, userName }: { initials: string; userName: string }) => (
    <header data-testid="mobile-header">
      <span>{initials}</span>
      <span>{userName}</span>
    </header>
  ),
}))

vi.mock("@/components/layout/mobile/bottom-nav", () => ({
  BottomNav: () => <nav data-testid="bottom-nav">BottomNav</nav>,
}))

vi.mock("@/components/layout/shared/settings-drawer", () => ({
  SettingsDrawer: () => <div data-testid="settings-drawer">SettingsDrawer</div>,
}))

vi.mock("@/components/ui/avatar", () => ({
  Avatar: ({ children }: { children: React.ReactNode }) => <div data-testid="avatar">{children}</div>,
  AvatarFallback: ({ children }: { children: React.ReactNode }) => <span>{children}</span>,
}))

describe("AppShell", () => {
  it("renderiza children", () => {
    render(
      <AppShell>
        <p data-testid="child">Conteudo</p>
      </AppShell>
    )
    expect(screen.getByTestId("child")).toBeInTheDocument()
    expect(screen.getByText("Conteudo")).toBeInTheDocument()
  })

  it("renderiza Sidebar em desktop", () => {
    render(
      <AppShell>
        <p>child</p>
      </AppShell>
    )
    expect(screen.getByTestId("sidebar")).toBeInTheDocument()
  })

  it("renderiza BottomNav", () => {
    render(
      <AppShell>
        <p>child</p>
      </AppShell>
    )
    expect(screen.getByTestId("bottom-nav")).toBeInTheDocument()
  })

  it("renderiza SettingsDrawer", () => {
    render(
      <AppShell>
        <p>child</p>
      </AppShell>
    )
    expect(screen.getByTestId("settings-drawer")).toBeInTheDocument()
  })

  it("renderiza avatar com nome do usuario", () => {
    render(
      <AppShell>
        <p>child</p>
      </AppShell>
    )
    expect(screen.getByText("AS")).toBeInTheDocument()
  })
})
