import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios"

const API_BASE_URL = "/api/v1"

export interface ApiClientError extends Error {
  code?: string
  details?: unknown
}

function isAuthFlowRequest(url?: string) {
  return !!url && /\/auth\/(login|register|google|verify-email|resend-verification|forgot-password|reset-password|refresh)$/.test(url)
}

function translateAxiosMessage(message?: string) {
  if (!message) return null
  if (message === "Network Error") return "Erro de conexão. Tente novamente."
  if (message === "Request failed with status code 401") return "Sua sessão expirou. Faça login novamente."
  if (message === "Request failed with status code 422") return "Os dados informados são inválidos."
  return message
}

interface TokenStore {
  accessToken: string | null
  csrfToken: string | null
  setTokens: (access: string, refresh: string, csrf?: string) => void
  clearTokens: () => void
  getAccessToken: () => string | null
}

let memoryToken: string | null = null

const tokenStore: TokenStore = {
  accessToken: null,
  csrfToken: null,
  setTokens(access: string, _refresh: string, csrf?: string) {
    void _refresh
    memoryToken = access
    this.accessToken = access
    if (csrf) this.csrfToken = csrf
  },
  clearTokens() {
    memoryToken = null
    this.accessToken = null
    this.csrfToken = null
  },
  getAccessToken() {
    if (typeof window === "undefined") return null
    if (!memoryToken) {
      const match = document.cookie.match(/(?:^|; )access_token=([^;]*)/)
      if (match) memoryToken = decodeURIComponent(match[1])
    }
    return memoryToken || this.accessToken
  },
}

export function getTokenStore(): TokenStore {
  return tokenStore
}

function setAuthCookies(access_token: string, refresh_token: string) {
  const accessExpiry = 30 * 60
  const refreshExpiry = 7 * 24 * 60 * 60
  document.cookie = `access_token=${encodeURIComponent(access_token)}; path=/; max-age=${accessExpiry}; SameSite=Lax`
  document.cookie = `refresh_token=${encodeURIComponent(refresh_token)}; path=/; max-age=${refreshExpiry}; SameSite=Lax`
  memoryToken = access_token
  tokenStore.accessToken = access_token
}

function clearAuthCookies() {
  document.cookie = "access_token=; path=/; max-age=0; SameSite=Lax"
  document.cookie = "refresh_token=; path=/; max-age=0; SameSite=Lax"
  memoryToken = null
  tokenStore.accessToken = null
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
})

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStore.getAccessToken()
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (typeof window !== "undefined" && config.method !== "get") {
    // Prefer in-memory CSRF token (cross-domain safe), fallback to cookie
    const csrfToken = tokenStore.csrfToken || (() => {
      const match = document.cookie.match(/(?:^|; )csrf_token=([^;]*)/)
      return match ? decodeURIComponent(match[1]) : null
    })()
    if (csrfToken && config.headers) {
      config.headers["X-CSRF-Token"] = csrfToken
    }
  }
  return config
})

let isRefreshing = false
let failedQueue: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

function processQueue(error: unknown, token: string | null = null) {
  failedQueue.forEach((promise) => {
    if (error) {
      promise.reject(error)
    } else {
      promise.resolve(token!)
    }
  })
  failedQueue = []
}

apiClient.interceptors.response.use(
  (response) => {
    if (response.data?.access_token && response.data?.refresh_token) {
      setAuthCookies(response.data.access_token, response.data.refresh_token)
      if (response.data?.csrf_token) {
        tokenStore.csrfToken = response.data.csrf_token
      }
    }
    return response
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthFlowRequest(originalRequest.url)) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token: string) => {
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${token}`
              }
              resolve(apiClient(originalRequest))
            },
            reject,
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      const match = document.cookie.match(/(?:^|; )refresh_token=([^;]*)/)
      const refreshToken = match ? decodeURIComponent(match[1]) : null

if (!refreshToken) {
        clearAuthCookies()
        isRefreshing = false
        processQueue(new Error("Sessão expirada"))
        if (typeof window !== "undefined") {
          window.location.href = "/login"
        }
        return Promise.reject(extractErrorMessage(error))
      }

      try {
        const response = await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          { refresh_token: refreshToken },
          { headers: { "Content-Type": "application/json" }, withCredentials: true }
        )
        const { access_token, refresh_token } = response.data
        setAuthCookies(access_token, refresh_token)
        processQueue(null, access_token)
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`
        }
        return apiClient(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        clearAuthCookies()
        if (typeof window !== "undefined") {
          window.location.href = "/login"
        }
        return Promise.reject(refreshError instanceof Error ? refreshError : new Error(String(refreshError)))
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(extractErrorMessage(error))
  },
)

function extractErrorMessage(error: AxiosError): ApiClientError {
  const data = error.response?.data as {
    error?: { code?: string; message?: string; details?: unknown }
    detail?: string | Array<{ loc?: Array<string | number>; msg?: string; type?: string }>
  } | undefined
  const validationDetail = Array.isArray(data?.detail) ? data.detail[0] : null
  const message =
    data?.error?.message ||
    (typeof data?.detail === "string" ? data.detail : null) ||
    validationDetail?.msg ||
    translateAxiosMessage(error.message) ||
    "Erro desconhecido"
  const enriched = new Error(message) as ApiClientError
  enriched.code = data?.error?.code
  enriched.details = data?.error?.details ?? data?.detail
  return enriched
}

// ---- typed convenience wrapper ----

export const api = {
  get: async <T>(url: string) => {
    const { data } = await apiClient.get<T>(url)
    return data
  },
  post: async <T>(url: string, body?: unknown) => {
    const { data } = await apiClient.post<T>(url, body)
    return data
  },
  patch: async <T>(url: string, body?: unknown) => {
    const { data } = await apiClient.patch<T>(url, body)
    return data
  },
  delete: async (url: string) => {
    await apiClient.delete(url)
  },
}

export { setAuthCookies, clearAuthCookies }
export default apiClient
