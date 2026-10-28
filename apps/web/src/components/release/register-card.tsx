"use client";

import { useState } from "react";
// import { GoogleLogin } from "@react-oauth/google";
import { User, Mail, Lock, LockKeyhole, ArrowRight } from "lucide-react";
import { registerSchema } from "@/lib/validations";
import { PillInput } from "./pill-input";
import { AuthCard, AuthHeader, AuthFooter } from "./auth-card";
// import { AuthDivider } from "./auth-card";
import { ToastBanner } from "./toast-banner";

type PasswordChecks = {
  minLength: boolean;
  hasUppercase: boolean;
  hasLowercase: boolean;
  hasNumber: boolean;
};

function getPasswordChecks(value: string): PasswordChecks {
  let hasUppercase = false;
  let hasLowercase = false;
  let hasNumber = false;

  for (const char of value) {
    if (char >= "A" && char <= "Z") hasUppercase = true;
    if (char >= "a" && char <= "z") hasLowercase = true;
    if (char >= "0" && char <= "9") hasNumber = true;
  }

  return {
    minLength: value.length >= 6,
    hasUppercase,
    hasLowercase,
    hasNumber,
  };
}

interface RegisterCardProps {
  onRegister?: (data: {
    name: string;
    email: string;
    password: string;
  }) => void;
  onGoogleRegister?: (idToken: string) => void;
  onLoginClick?: () => void;
  isLoading?: boolean;
  errorMessage?: string | null;
  fieldErrors?: Partial<
    Record<"name" | "email" | "password" | "confirmPassword", string>
  >;
  onFieldErrorClear?: (
    field: "name" | "email" | "password" | "confirmPassword",
  ) => void;
  onDismissError?: () => void;
}

export function RegisterCard({
  onRegister,
  // onGoogleRegister,
  onLoginClick,
  isLoading,
  errorMessage,
  fieldErrors,
  onFieldErrorClear,
  onDismissError,
}: RegisterCardProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [validationToast, setValidationToast] = useState<string | null>(null);
  // const [googleError, setGoogleError] = useState<string | null>(null);
  // const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";
  const mergedErrors = { ...fieldErrors, ...errors };
  const passwordChecks = getPasswordChecks(password);

  const resolvePasswordToast = (message: string) => {
    if (message === "Senhas não coincidem") {
      return "Senhas não coincidem. Confira os dois campos e tente novamente.";
    }
    if (
      message === "Senha tem que ter no mínimo 6 dígitos" ||
      message === "Senha deve conter letra maiúscula, letra minúscula e número"
    ) {
      return "Senha incorreta. Use no mínimo 6 caracteres, com letra maiúscula, letra minúscula e número.";
    }
    return message;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    const result = registerSchema.safeParse({
      name,
      email,
      password,
      confirmPassword,
    });
    if (!result.success) {
      const fieldErrors: Record<string, string> = {};
      result.error.issues.forEach((err) => {
        const path = err.path[0] as string;
        fieldErrors[path] = err.message;
      });
      setErrors(fieldErrors);
      setValidationToast(
        resolvePasswordToast(
          result.error.issues[0]?.message || "Revise os campos informados.",
        ),
      );
      return;
    }
    onRegister?.({ name, email, password });
  };

  return (
    <div className="rls min-h-dvh bg-[var(--rls-background)] flex flex-col items-center justify-center p-[var(--rls-container-margin)]">
      <ToastBanner
        isOpen={!!(errorMessage || validationToast)}
        message={errorMessage || validationToast || ""}
        variant="error"
        onClose={() => {
          // setGoogleError(null);
          setValidationToast(null);
          onDismissError?.();
        }}
      />
      <AuthCard>
        <AuthHeader title="Crie sua conta" />

        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-[var(--rls-stack-gap-md)] w-full"
        >
          <PillInput
            label="Nome Completo"
            icon={<User className="w-5 h-5" />}
            placeholder="Ex: João Silva"
            value={name}
            error={mergedErrors.name}
            onChange={(e) => {
              setName(e.target.value);
              if (errors.name) setErrors((prev) => ({ ...prev, name: "" }));
              if (validationToast) setValidationToast(null);
              onFieldErrorClear?.("name");
            }}
          />

          <PillInput
            label="Email"
            icon={<Mail className="w-5 h-5" />}
            placeholder="seu@email.com"
            type="email"
            value={email}
            error={mergedErrors.email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (errors.email) setErrors((prev) => ({ ...prev, email: "" }));
              if (validationToast) setValidationToast(null);
              onFieldErrorClear?.("email");
            }}
          />

          <PillInput
            label="Senha"
            icon={<Lock className="w-5 h-5" />}
            placeholder="Mínimo 6 caracteres"
            type="password"
            showPasswordToggle
            value={password}
            error={mergedErrors.password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (errors.password)
                setErrors((prev) => ({ ...prev, password: "" }));
              if (validationToast) setValidationToast(null);
              onFieldErrorClear?.("password");
            }}
          />
          <ul
            className="ml-4 mt-1 flex flex-col gap-1"
            aria-label="Checklist de senha"
          >
            <PasswordRuleItem
              label="Mínimo de 6 caracteres"
              passed={passwordChecks.minLength}
              testId="password-check-min-length"
            />
            <PasswordRuleItem
              label="Pelo menos 1 letra maiúscula"
              passed={passwordChecks.hasUppercase}
              testId="password-check-uppercase"
            />
            <PasswordRuleItem
              label="Pelo menos 1 letra minúscula"
              passed={passwordChecks.hasLowercase}
              testId="password-check-lowercase"
            />
            <PasswordRuleItem
              label="Pelo menos 1 número"
              passed={passwordChecks.hasNumber}
              testId="password-check-number"
            />
          </ul>

          <PillInput
            label="Confirmar Senha"
            icon={<LockKeyhole className="w-5 h-5" />}
            placeholder="Repita a senha"
            type="password"
            showPasswordToggle
            value={confirmPassword}
            error={mergedErrors.confirmPassword}
            onChange={(e) => {
              setConfirmPassword(e.target.value);
              if (errors.confirmPassword)
                setErrors((prev) => ({ ...prev, confirmPassword: "" }));
              if (validationToast) setValidationToast(null);
              onFieldErrorClear?.("confirmPassword");
            }}
          />

          <button
            type="submit"
            disabled={isLoading}
            className="w-full h-14 bg-[var(--rls-primary-container)] text-white rls-text-title-lg rounded-[var(--rls-radius-pill)] hover:bg-[var(--rls-primary)] transition-colors active:scale-[0.98] shadow-md shadow-[var(--rls-primary-container)]/20 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isLoading ? "Criando conta..." : "Criar Conta"}
            {!isLoading && <ArrowRight className="w-5 h-5" />}
          </button>
        </form>

        {/*
        <AuthDivider text="ou cadastre-se com" />

        {googleClientId ? (
          <div className="flex w-full justify-center">
            <GoogleLogin
              onSuccess={(credentialResponse) => {
                if (credentialResponse.credential) {
                  onGoogleRegister?.(credentialResponse.credential);
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
          text="Já tem uma conta?"
          linkText="Entre"
          onLinkClick={onLoginClick}
        />
      </AuthCard>
    </div>
  );
}

function PasswordRuleItem({
  label,
  passed,
  testId,
}: {
  label: string;
  passed: boolean;
  testId: string;
}) {
  return (
    <li
      data-testid={testId}
      data-status={passed ? "ok" : "pending"}
      className="flex items-center gap-2 rls-text-label-md"
    >
      <span
        aria-hidden
        className={
          passed
            ? "text-[var(--rls-primary)]"
            : "text-[var(--rls-on-surface-variant)]"
        }
      >
        {passed ? "✓" : "○"}
      </span>
      <span
        className={
          passed
            ? "text-[var(--rls-on-surface)]"
            : "text-[var(--rls-on-surface-variant)]"
        }
      >
        {label}
      </span>
    </li>
  );
}
