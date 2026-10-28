import { describe, expect, it } from "vitest"
import {
  PASSWORD_RESET_COOLDOWN_MESSAGE,
  PASSWORD_RESET_REQUEST_ERROR_MESSAGE,
  safePasswordResetRequestMessage,
  safeToastErrorMessage,
} from "@/lib/toast-messages"

describe("toast-messages", () => {
  it("usa mensagem fixa para cooldown de redefinição de senha", () => {
    expect(safePasswordResetRequestMessage({ code: "PASSWORD_RESET_COOLDOWN", message: "raw" })).toBe(
      PASSWORD_RESET_COOLDOWN_MESSAGE
    )
    expect(safePasswordResetRequestMessage({ code: "PASSWORD_RESET_RATE_LIMITED", message: "raw" })).toBe(
      PASSWORD_RESET_COOLDOWN_MESSAGE
    )
  })

  it("não expõe mensagem técnica no reset de senha", () => {
    expect(safePasswordResetRequestMessage(new Error("Internal Server Error"))).toBe(
      PASSWORD_RESET_REQUEST_ERROR_MESSAGE
    )
  })

  it("retorna somente fallback seguro para toasts genéricos", () => {
    expect(safeToastErrorMessage("Não foi possível salvar. Tente novamente.")).toBe(
      "Não foi possível salvar. Tente novamente."
    )
  })
})
