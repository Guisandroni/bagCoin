"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import { LoginCard } from "@/components/release/login-card";
import { useAuthStore } from "@/lib/auth-store";
import { ToastBanner } from "@/components/release/toast-banner";
import type { ApiClientError } from "@/lib/api-client";

const GoogleProvider = dynamic(
  () =>
    import("@/components/auth/google-provider").then((m) => m.GoogleProvider),
  { ssr: false },
);

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, loginWithGoogle, clearError, isLoading } = useAuthStore();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showVerifiedBanner, setShowVerifiedBanner] = useState(
    searchParams.get("verified") === "true",
  );

  const handleLogin = async (email: string, password: string) => {
    setErrorMessage(null);
    try {
      await login(email, password);
      router.push("/app");
    } catch (error) {
      const authError = error as ApiClientError;
      const pendingEmail =
        typeof authError.details === "object" &&
        authError.details &&
        "email" in authError.details
          ? String((authError.details as { email?: string }).email || email)
          : email;
      if (authError.code === "EMAIL_NOT_VERIFIED") {
        router.push(
          `/verify-email?email=${encodeURIComponent(pendingEmail)}&source=login`,
        );
        return;
      }
      setErrorMessage(
        resolveAuthError(
          error,
          "Não foi possível entrar. Verifique email e senha.",
        ),
      );
    }
  };

  const handleGoogleLogin = async (idToken: string) => {
    setErrorMessage(null);
    try {
      const result = await loginWithGoogle(idToken);
      if (result.status === "pending") {
        router.push(
          `/verify-email?email=${encodeURIComponent(result.pending.email)}&source=google`,
        );
        return;
      }
      router.push("/app");
    } catch (error) {
      setErrorMessage(
        resolveAuthError(error, "Não foi possível entrar com Google."),
      );
    }
  };

  return (
    <>
      <ToastBanner
        isOpen={showVerifiedBanner}
        message="Email verificado com sucesso. Faça login para continuar."
        variant="success"
        onClose={() => {
          setShowVerifiedBanner(false);
        }}
      />
      <GoogleProvider>
        <LoginCard
          onLogin={handleLogin}
          onGoogleLogin={handleGoogleLogin}
          onRegisterClick={() => router.push("/register")}
          onForgotPassword={() => router.push("/forgot-password")}
          isLoading={isLoading}
          errorMessage={errorMessage}
          onDismissError={() => {
            setErrorMessage(null);
            clearError();
          }}
        />
      </GoogleProvider>
    </>
  );
}

function resolveAuthError(error: unknown, fallback: string): string {
  const err = error as {
    code?: string;
    response?: { data?: { error?: { message?: string }; detail?: string } };
    message?: string;
  };
  return (
    err.message ||
    err.response?.data?.error?.message ||
    err.response?.data?.detail ||
    fallback
  );
}
