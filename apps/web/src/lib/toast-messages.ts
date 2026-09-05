import type { ApiClientError } from "@/lib/api-client"

export const PASSWORD_RESET_SENT_MESSAGE =
  "Se o email informado estiver cadastrado, o link de redefinição foi enviado. Confira sua caixa de entrada."

export const PASSWORD_RESET_COOLDOWN_MESSAGE = "Aguarde 3 minutos antes de solicitar outro link."

export const PASSWORD_RESET_REQUEST_ERROR_MESSAGE =
  "Não foi possível processar a solicitação agora. Tente novamente em alguns minutos."

export const PASSWORD_RESET_INVALID_MESSAGE =
  "Não foi possível alterar a senha. Solicite um novo link e tente novamente."

export const PASSWORD_RESET_SUCCESS_MESSAGE = "Senha alterada com sucesso. Faça login para continuar."

export function safePasswordResetRequestMessage(error: unknown): string {
  const apiError = error as ApiClientError
  if (apiError?.code === "PASSWORD_RESET_COOLDOWN" || apiError?.code === "PASSWORD_RESET_RATE_LIMITED") {
    return PASSWORD_RESET_COOLDOWN_MESSAGE
  }
  return PASSWORD_RESET_REQUEST_ERROR_MESSAGE
}

export function safeToastErrorMessage(fallback: string): string {
  return fallback
}
