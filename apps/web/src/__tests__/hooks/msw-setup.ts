/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-require-imports */
import { vi, beforeAll, afterEach, afterAll } from "vitest"
import { server } from "./setup"

// Mock api-client so axios uses http adapter (MSW compatible)
// Vitest hoists vi.mock to the top, so this affects all test files that import this module
vi.mock("@/lib/api-client", () => {
  // Use a dynamic import approach that works with vitest hoisting
  const axios = require("axios").default
  const http = axios.create({
    baseURL: "http://localhost:8000/api/v1",
    headers: { "Content-Type": "application/json" },
    withCredentials: true,
    adapter: "http",
  })
  return {
    default: http,
    api: {
      get: (url: string) => http.get(url).then((r: any) => r.data),
      post: (url: string, body?: unknown) => http.post(url, body).then((r: any) => r.data),
      patch: (url: string, body?: unknown) => http.patch(url, body).then((r: any) => r.data),
      delete: (url: string) => http.delete(url).then(() => {}),
    },
    getTokenStore: () => ({ getAccessToken: () => null, setTokens: () => {}, clearTokens: () => {} }),
    setAuthCookies: () => {},
    clearAuthCookies: () => {},
  }
})

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
