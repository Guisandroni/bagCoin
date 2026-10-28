import { create } from "zustand"
import apiClient, {
  type ApiClientError,
  clearAuthCookies,
  getTokenStore,
  setAuthCookies,
} from "@/lib/api-client"
import {
  PASSWORD_RESET_INVALID_MESSAGE,
  PASSWORD_RESET_REQUEST_ERROR_MESSAGE,
  safePasswordResetRequestMessage,
} from "@/lib/toast-messages"

interface User {
  id: string
  email: string
  full_name: string | null
  phone_number: string | null
  is_active: boolean
  email_verified: boolean
  role: string
  avatar_url: string | null
  auth_provider: string
}

export interface PendingAuthResponse {
  email: string
  requires_email_verification: true
  auth_provider: "email" | "google"
  expires_in_seconds: number
  resend_available_in_seconds: number
}

interface VerificationSuccessResponse {
  verified: true
  message: string
  access_token?: string | null
  refresh_token?: string | null
  token_type?: string
  csrf_token?: string | null
}

interface ResendVerificationResponse {
  sent: true
  resend_available_in_seconds: number
  expires_in_seconds: number
}

type GoogleLoginResult =
  | { status: "authenticated" }
  | { status: "pending"; pending: PendingAuthResponse }

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName?: string, phoneNumber?: string) => Promise<PendingAuthResponse>
  loginWithGoogle: (idToken: string) => Promise<GoogleLoginResult>
  verifyEmail: (email: string, code: string) => Promise<VerificationSuccessResponse>
  resendVerification: (email: string) => Promise<ResendVerificationResponse>
  forgotPassword: (email: string) => Promise<void>
  resetPassword: (token: string, password: string) => Promise<void>
  logout: () => void
  fetchUser: () => Promise<void>
  clearError: () => void
}

const PENDING_VERIFY_STORAGE_KEY = "pending_email_verification"

function savePendingVerificationContext(data: PendingAuthResponse) {
  if (typeof window === "undefined") return
  window.sessionStorage.setItem(
    PENDING_VERIFY_STORAGE_KEY,
    JSON.stringify({
      email: data.email,
      source: data.auth_provider,
      resend_available_in_seconds: data.resend_available_in_seconds,
      issued_at: Date.now(),
    }),
  )
}

export function clearPendingVerificationContext() {
  if (typeof window === "undefined") return
  window.sessionStorage.removeItem(PENDING_VERIFY_STORAGE_KEY)
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null })
    try {
      const formData = new URLSearchParams()
      formData.append("username", email)
      formData.append("password", password)

      const response = await apiClient.post("/auth/login", formData, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      })

      const { access_token, refresh_token } = response.data
      setAuthCookies(access_token, refresh_token)
      getTokenStore().setTokens(access_token, refresh_token)

      await get().fetchUser()
    } catch (error: unknown) {
      const err = error as ApiClientError
      const message = err.message || "Falha ao fazer login"
      set({
        isLoading: false,
        error: message,
      })
      throw error
    }
  },

  register: async (email: string, password: string, fullName?: string, phoneNumber?: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await apiClient.post<PendingAuthResponse>("/auth/register", {
        email,
        password,
        full_name: fullName || null,
        phone_number: phoneNumber || null,
      })
      savePendingVerificationContext(response.data)
      set({ isLoading: false })
      return response.data
    } catch (error: unknown) {
      const err = error as ApiClientError
      const message = err.message || "Não foi possível criar sua conta"
      set({
        isLoading: false,
        error: message,
      })
      throw error
    }
  },

  loginWithGoogle: async (idToken: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await apiClient.post<TokenLike | PendingAuthResponse>("/auth/google", { id_token: idToken })

      if ("requires_email_verification" in response.data) {
        savePendingVerificationContext(response.data)
        set({ isLoading: false, error: null })
        return { status: "pending", pending: response.data }
      }

      const { access_token, refresh_token } = response.data
      setAuthCookies(access_token, refresh_token)
      getTokenStore().setTokens(access_token, refresh_token)
      clearPendingVerificationContext()

      await get().fetchUser()
      return { status: "authenticated" }
    } catch (error: unknown) {
      const err = error as ApiClientError
      set({
        isLoading: false,
        error: err.message || "Falha ao fazer login com Google",
      })
      throw error
    }
  },

  verifyEmail: async (email: string, code: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await apiClient.post<VerificationSuccessResponse>("/auth/verify-email", {
        email,
        code,
      })
      const { access_token, refresh_token, csrf_token } = response.data
      if (access_token && refresh_token) {
        setAuthCookies(access_token, refresh_token)
        getTokenStore().setTokens(access_token, refresh_token, csrf_token || undefined)
        await get().fetchUser()
      }
      clearPendingVerificationContext()
      set({ isLoading: false, error: null })
      return response.data
    } catch (error: unknown) {
      const err = error as ApiClientError
      set({ isLoading: false, error: err.message || "Falha ao verificar email" })
      throw error
    }
  },

  resendVerification: async (email: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await apiClient.post<ResendVerificationResponse>("/auth/resend-verification", { email })
      savePendingVerificationContext({
        email,
        auth_provider: "email",
        expires_in_seconds: response.data.expires_in_seconds,
        resend_available_in_seconds: response.data.resend_available_in_seconds,
        requires_email_verification: true,
      })
      set({ isLoading: false, error: null })
      return response.data
    } catch (error: unknown) {
      const err = error as ApiClientError
      set({ isLoading: false, error: err.message || "Não foi possível reenviar o código" })
      throw error
    }
  },

  forgotPassword: async (email: string) => {
    set({ isLoading: true, error: null })
    try {
      await apiClient.post("/auth/forgot-password", { email })
      set({ isLoading: false, error: null })
    } catch (error: unknown) {
      set({ isLoading: false, error: safePasswordResetRequestMessage(error) || PASSWORD_RESET_REQUEST_ERROR_MESSAGE })
      throw error
    }
  },

  resetPassword: async (token: string, password: string) => {
    set({ isLoading: true, error: null })
    try {
      await apiClient.post("/auth/reset-password", { token, password })
      set({ isLoading: false, error: null })
    } catch (error: unknown) {
      set({ isLoading: false, error: PASSWORD_RESET_INVALID_MESSAGE })
      throw error
    }
  },

  logout: () => {
    clearAuthCookies()
    getTokenStore().clearTokens()
    clearPendingVerificationContext()
    set({ user: null, isAuthenticated: false })
    if (typeof window !== "undefined") {
      window.location.href = "/login"
    }
  },

  fetchUser: async () => {
    try {
      const response = await apiClient.get("/auth/me")
      set({ user: response.data, isAuthenticated: true, isLoading: false, error: null })
    } catch {
      clearAuthCookies()
      getTokenStore().clearTokens()
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: "Sessão expirada",
      })
    }
  },

  clearError: () => set({ error: null }),
}))

interface TokenLike {
  access_token: string
  refresh_token: string
}
