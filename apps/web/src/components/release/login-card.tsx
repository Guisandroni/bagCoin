"use client";

import { useState } from "react";
// import { GoogleLogin } from "@react-oauth/google";
import { Mail, Lock, ArrowRight } from "lucide-react";
import { loginSchema } from "@/lib/validations";
import { PillInput } from "./pill-input";
import { AuthCard, AuthHeader, AuthFooter } from "./auth-card";
// import { AuthDivider } from "./auth-card";
import { ToastBanner } from "./toast-banner";

interface LoginCardProps {
  onLogin?: (email: string, password: string) => void;
  onGoogleLogin?: (idToken: string) => void;
  onRegisterClick?: () => void;
  onForgotPassword?: () => void;
  isLoading?: boolean;
  errorMessage?: string | null;
  onDismissError?: () => void;
}

export function LoginCard({
  onLogin,
  // onGoogleLogin,
  onRegisterClick,
  onForgotPassword,
  isLoading,
  errorMessage,
  onDismissError,
}: LoginCardProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  // const [googleError, setGoogleError] = useState<string | null>(null);
  // const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    const result = loginSchema.safeParse({ email, password });
    if (!result.success) {
      const fieldErrors: Record<string, string> = {};
      result.error.issues.forEach((err) => {
        const path = err.path[0] as string;
        fieldErrors[path] = err.message;
      });
      setErrors(fieldErrors);
      return;
    }
    onLogin?.(email, password);
  };

  return (
    <div className="rls min-h-dvh bg-[var(--rls-background)] flex flex-col items-center justify-center p-[var(--rls-container-margin)]">
      <ToastBanner
        isOpen={!!errorMessage}
        message={errorMessage || ""}
        variant="error"
        onClose={() => {
          // setGoogleError(null);
          onDismissError?.();
        }}
      />
      <AuthCard>
        <AuthHeader
          icon={
            <div className="w-16 h-16 rounded-full bg-[var(--rls-primary-container)] flex items-center justify-center">
              <span className="text-white text-2xl font-bold">BC</span>
            </div>
          }
          title="Bem-vindo de volta!"
        />

        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-[var(--rls-stack-gap-md)] w-full"
        >
          <PillInput
            label="Email"
            icon={<Mail className="w-5 h-5" />}
            placeholder="exemplo@email.com"
            type="email"
            value={email}
            error={errors.email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (errors.email) setErrors((prev) => ({ ...prev, email: "" }));
            }}
          />

          <PillInput
            label="Senha"
            icon={<Lock className="w-5 h-5" />}
            placeholder="••••••••"
            type="password"
            showPasswordToggle
            value={password}
            error={errors.password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (errors.password)
                setErrors((prev) => ({ ...prev, password: "" }));
            }}
          />

          <div className="flex justify-end -mt-2">
            <button
              type="button"
              onClick={onForgotPassword}
              className="rls-text-body-md text-[var(--rls-primary)] font-semibold hover:text-[var(--rls-primary-container)] transition-colors"
            >
              Esqueceu a senha?
            </button>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full h-14 bg-[var(--rls-primary-container)] text-white rls-text-title-lg rounded-[var(--rls-radius-pill)] mt-4 hover:bg-[var(--rls-primary)] transition-colors active:scale-[0.98] shadow-md shadow-[var(--rls-primary-container)]/20 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isLoading ? "Entrando..." : "Entrar"}
            {!isLoading && <ArrowRight className="w-5 h-5" />}
          </button>
        </form>

        {/*
        <AuthDivider text="ou entre com" />

        {googleClientId ? (
          <div className="flex w-full justify-center">
            <GoogleLogin
              onSuccess={(credentialResponse) => {
                if (credentialResponse.credential) {
                  onGoogleLogin?.(credentialResponse.credential);
                  return;
                }
                setGoogleError(
                  "Não foi possível receber a credencial do Google.",
                );
              }}
              onError={() => {
                setGoogleError("Erro ao entrar com Google.");
              }}
              text="continue_with"
              shape="pill"
              theme="outline"
              size="large"
            />
          </div>
        ) : (
          <button
            type="button"
            disabled
            className="w-full h-14 bg-[var(--rls-surface-container-lowest)] border border-[var(--rls-outline-variant)] text-[var(--rls-on-surface)] rls-text-title-lg rounded-[var(--rls-radius-pill)] opacity-60 flex items-center justify-center gap-3"
          >
            Google indisponível
          </button>
        )}
        */}

        <AuthFooter
          text="Não tem uma conta?"
          linkText="Cadastre-se"
          onLinkClick={onRegisterClick}
        />
      </AuthCard>
    </div>
  );
}
