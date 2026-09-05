"use client";

import { useEffect, useMemo, useState } from "react";
import { Mail, RefreshCw } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AuthCard,
  AuthFooter,
  AuthHeader,
} from "@/components/release/auth-card";
import { PillInput } from "@/components/release/pill-input";
import { ToastBanner } from "@/components/release/toast-banner";
import type { ApiClientError } from "@/lib/api-client";
import {
  clearPendingVerificationContext,
  useAuthStore,
} from "@/lib/auth-store";
import { verifyEmailSchema } from "@/lib/validations";

function buildSubtitle(source: string | null, email: string) {
  if (source === "google") {
    return `Enviamos um código para ${email} para liberar seu acesso com Google.`;
  }
  if (source === "login") {
    return `Seu email ${email} ainda não foi confirmado. Digite o código enviado para continuar.`;
  }
  return `Enviamos um código para ${email} para concluir seu cadastro.`;
}

function formatRetryTime(seconds: number) {
  if (seconds <= 0) return "alguns segundos";
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (minutes > 0 && remainingSeconds > 0) {
    return `${minutes} min ${remainingSeconds}s`;
  }
  if (minutes > 0) {
    return minutes === 1 ? "1 minuto" : `${minutes} minutos`;
  }
  return `${remainingSeconds} segundos`;
}

export default function VerifyEmailPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryEmail = searchParams.get("email") || "";
  const querySource = searchParams.get("source");
  const querySent = searchParams.get("sent");
  const { verifyEmail, resendVerification, isLoading, clearError } =
    useAuthStore();

  const [email, setEmail] = useState(queryEmail);
  const [source, setSource] = useState<string | null>(querySource);
  const [code, setCode] = useState("");
  const [codeError, setCodeError] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(0);
  const [hasManualEmailMode, setHasManualEmailMode] = useState(false);

  useEffect(() => {
    queueMicrotask(() => {
      if (queryEmail) {
        setEmail(queryEmail);
        setSource(querySource);
        if (querySource === "register" && querySent === "1") {
          setSuccessMessage(
            "Enviamos um código de verificação para o seu email.",
          );
        }
        return;
      }
      try {
        const raw = window.sessionStorage.getItem("pending_email_verification");
        if (!raw) {
          setHasManualEmailMode(true);
          setErrorMessage(
            "Não encontramos sua sessão de verificação. Digite seu email para enviar um novo código.",
          );
          return;
        }
        const parsed = JSON.parse(raw) as {
          email?: string;
          source?: string;
          resend_available_in_seconds?: number;
          issued_at?: number;
        };
        if (!parsed.email) {
          setHasManualEmailMode(true);
          setErrorMessage(
            "Não encontramos sua sessão de verificação. Digite seu email para enviar um novo código.",
          );
          return;
        }
        setEmail(parsed.email);
        setSource(parsed.source ?? null);
        const issuedAt =
          typeof parsed.issued_at === "number" ? parsed.issued_at : Date.now();
        const availableIn =
          typeof parsed.resend_available_in_seconds === "number"
            ? parsed.resend_available_in_seconds
            : 0;
        const elapsedSeconds = Math.floor((Date.now() - issuedAt) / 1000);
        setCooldown(Math.max(availableIn - elapsedSeconds, 0));
      } catch {
        setHasManualEmailMode(true);
        setErrorMessage(
          "Não encontramos sua sessão de verificação. Digite seu email para enviar um novo código.",
        );
      }
    });
  }, [queryEmail, querySource, querySent, router]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = window.setTimeout(
      () => setCooldown((current) => current - 1),
      1000,
    );
    return () => window.clearTimeout(timer);
  }, [cooldown]);

  const subtitle = useMemo(() => buildSubtitle(source, email), [email, source]);

  const handleVerify = async (event: React.FormEvent) => {
    event.preventDefault();
    setErrorMessage(null);
    setCodeError(null);
    const parsed = verifyEmailSchema.safeParse({ email, code });
    if (!parsed.success) {
      const message = parsed.error.issues[0]?.message || "Código inválido";
      setCodeError(message);
      setErrorMessage(message);
      return;
    }

    try {
      const response = await verifyEmail(email, code);
      setSuccessMessage(response.message);
      clearPendingVerificationContext();
      if (response.access_token && response.refresh_token) {
        router.push("/app");
        return;
      }
      router.push("/login?verified=true");
    } catch (error) {
      const authError = error as ApiClientError;
      const details = authError.details as
        | {
            attempts_remaining?: number;
            attempts_used?: number;
            max_attempts?: number;
            retry_after_seconds?: number;
          }
        | undefined;

      if (authError.code === "EMAIL_VERIFICATION_INVALID") {
        const attemptsRemaining = details?.attempts_remaining;
        const message =
          typeof attemptsRemaining === "number"
            ? `Código incorreto. Tentativas restantes: ${attemptsRemaining}.`
            : "Código incorreto.";
        setCodeError(message);
        setErrorMessage(message);
        return;
      }

      if (authError.code === "EMAIL_VERIFICATION_RATE_LIMITED") {
        const retryAfter =
          typeof details?.retry_after_seconds === "number"
            ? details.retry_after_seconds
            : 60;
        const message = `Você atingiu o limite de tentativas. Aguarde ${formatRetryTime(retryAfter)} antes de solicitar um novo código.`;
        setCooldown(retryAfter);
        setCodeError(message);
        setErrorMessage(message);
        return;
      }

      const fallbackMessage = authError.message || "Falha ao verificar email";
      setCodeError(fallbackMessage);
      setErrorMessage(fallbackMessage);
    }
  };

  const handleResend = async () => {
    setErrorMessage(null);
    setCodeError(null);
    setSuccessMessage(null);
    try {
      if (!email.trim()) {
        const message = "Digite seu email para enviar o código de verificação.";
        setErrorMessage(message);
        return;
      }
      const response = await resendVerification(email);
      setCooldown(response.resend_available_in_seconds);
      setHasManualEmailMode(false);
      setSuccessMessage("Enviamos um novo código para o seu email.");
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Falha ao reenviar código",
      );
    }
  };

  return (
    <div className="rls min-h-dvh bg-[var(--rls-background)] flex flex-col items-center justify-center p-[var(--rls-container-margin)]">
      <ToastBanner
        isOpen={!!errorMessage}
        message={errorMessage || ""}
        variant="error"
        onClose={() => {
          setErrorMessage(null);
          clearError();
        }}
      />
      <ToastBanner
        isOpen={!!successMessage}
        message={successMessage || ""}
        variant="success"
        onClose={() => {
          setSuccessMessage(null);
        }}
      />

      <AuthCard>
        <AuthHeader title="Confirme seu email" subtitle={subtitle} />

        <form
          onSubmit={handleVerify}
          className="flex flex-col gap-[var(--rls-stack-gap-md)] w-full"
        >
          <PillInput
            label="Email"
            icon={<Mail className="w-5 h-5" />}
            value={email}
            type="email"
            disabled={!hasManualEmailMode}
            readOnly={!hasManualEmailMode}
            onChange={(event) => setEmail(event.target.value)}
          />

          <PillInput
            label="Código de verificação"
            placeholder="000000"
            inputMode="numeric"
            pattern="\d{6}"
            maxLength={6}
            autoComplete="one-time-code"
            value={code}
            error={codeError || undefined}
            onChange={(event) => {
              const digitsOnly = event.target.value
                .replace(/\D/g, "")
                .slice(0, 6);
              setCode(digitsOnly);
              if (codeError) setCodeError(null);
            }}
          />

          <button
            type="submit"
            disabled={isLoading}
            className="w-full h-14 bg-[var(--rls-primary-container)] text-white rls-text-title-lg rounded-[var(--rls-radius-pill)] hover:bg-[var(--rls-primary)] transition-colors active:scale-[0.98] shadow-md shadow-[var(--rls-primary-container)]/20 disabled:opacity-50"
          >
            {isLoading ? "Validando..." : "Confirmar código"}
          </button>

          <button
            type="button"
            onClick={handleResend}
            disabled={isLoading || cooldown > 0 || !email.trim()}
            className="w-full h-14 bg-[var(--rls-surface-container-lowest)] border border-[var(--rls-outline-variant)] text-[var(--rls-on-surface)] rls-text-title-lg rounded-[var(--rls-radius-pill)] hover:bg-[var(--rls-surface-container)] transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <RefreshCw className="w-5 h-5" />
            {cooldown > 0
              ? `Reenviar em ${formatRetryTime(cooldown)}`
              : "Enviar código"}
          </button>
        </form>

        <AuthFooter
          text="Já verificou seu email?"
          linkText="Voltar para login"
          onLinkClick={() => router.push("/login")}
        />
      </AuthCard>
    </div>
  );
}
