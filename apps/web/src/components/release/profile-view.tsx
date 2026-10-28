"use client";

import { useState } from "react";
import Image from "next/image";
import { Badge, Eye, EyeOff, LogOut, Mail, Phone } from "lucide-react";
import { AppBar } from "./app-bar";
import { PillInput } from "./pill-input";
import type { ReleaseProfile } from "./types";

interface ProfileViewProps {
  profile: ReleaseProfile & { phone?: string; tier?: string };
  onBack?: () => void;
  onOpenDrawer?: () => void;
  onLogout?: () => void;
}

export function ProfileView({
  profile,
  onBack,
  onOpenDrawer,
  onLogout,
}: ProfileViewProps) {
  const [showPhone, setShowPhone] = useState(false);
  const phoneValue = profile.phone || "";
  const maskedPhone = maskPhone(phoneValue);

  return (
    <div className="rls mx-auto min-h-dvh w-full max-w-md bg-[var(--rls-background)] shadow-[0_0_48px_rgba(22,82,240,0.08)]">
      <AppBar
        title="Perfil"
        onBack={onBack}
        onOpenDrawer={onOpenDrawer}
        titleClassName="text-[var(--rls-primary-container)] rls-text-headline-sm"
      />

      <main className="px-[var(--rls-container-margin)] flex flex-col gap-[var(--rls-stack-gap-lg)] pt-[var(--rls-stack-gap-md)] pb-24">
        <div className="bg-[var(--rls-surface-container-lowest)] border border-[var(--rls-outline-variant)] rounded-[var(--rls-radius-lg)] p-[var(--rls-inline-padding-md)] flex flex-col gap-6">
          <div className="flex justify-center">
            <div className="relative w-24 h-24 rounded-full overflow-hidden bg-[var(--rls-surface-variant)] flex items-center justify-center">
              {profile.avatarUrl ? (
                <Image
                  src={profile.avatarUrl}
                  alt={profile.name}
                  fill
                  sizes="96px"
                  unoptimized
                  className="object-cover"
                />
              ) : (
                <span className="text-[var(--rls-on-surface-variant)] text-3xl">
                  {profile.name.charAt(0)}
                </span>
              )}
            </div>
          </div>

          <div className="text-center">
            <h2 className="rls-text-title-lg text-[var(--rls-on-surface)]">
              {profile.name}
            </h2>
          </div>

          <div className="flex items-center gap-2 border-b border-[var(--rls-outline-variant)] pb-2">
            <Badge className="w-5 h-5 text-[var(--rls-primary)]" />
            <h3 className="rls-text-body-lg text-[var(--rls-on-surface)] font-semibold">
              Informações Pessoais
            </h3>
          </div>

          {/* Form Fields */}
          <div className="flex flex-col gap-[var(--rls-stack-gap-md)]">
            <PillInput
              icon={<Badge className="w-5 h-5" />}
              label="Nome Completo"
              value={profile.name}
              readOnly
              tabIndex={-1}
            />
            <PillInput
              icon={<Mail className="w-5 h-5" />}
              label="E-mail"
              value={profile.email}
              readOnly
              tabIndex={-1}
            />
            {profile.phone && (
              <div className="flex flex-col gap-1">
                <label className="rls-text-label-lg text-[var(--rls-on-background)] ml-4">
                  Telefone
                </label>
                <div className="relative flex h-14 items-center rounded-[var(--rls-radius-pill)] bg-[var(--rls-surface-container)]">
                  <Phone className="absolute left-4 h-5 w-5 text-[var(--rls-outline)]" />
                  <input
                    value={showPhone ? phoneValue : maskedPhone}
                    readOnly
                    tabIndex={-1}
                    aria-label="Telefone"
                    className="h-full w-full bg-transparent pl-12 pr-12 rls-text-body-lg text-[var(--rls-on-surface)] outline-none"
                  />
                  <button
                    type="button"
                    aria-label={
                      showPhone ? "Esconder telefone" : "Mostrar telefone"
                    }
                    aria-pressed={!showPhone}
                    onClick={() => setShowPhone((value) => !value)}
                    className="absolute right-4 text-[var(--rls-outline)] transition-colors hover:text-[var(--rls-on-surface)]"
                  >
                    {showPhone ? (
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={onLogout}
          className="flex h-14 w-full items-center justify-center gap-2 rounded-[var(--rls-radius)] bg-[var(--rls-error-container)] text-[var(--rls-on-error-container)] rls-text-body-lg font-semibold transition-opacity hover:opacity-90 active:scale-[0.98]"
        >
          <LogOut className="h-5 w-5" />
          Sair da Conta
        </button>
      </main>
    </div>
  );
}

function maskPhone(value: string): string {
  let seenDigits = 0;
  const totalDigits = value.replace(/\D/g, "").length;

  return value.replace(/\d/g, (digit) => {
    seenDigits += 1;
    return seenDigits <= Math.max(0, totalDigits - 4) ? "•" : digit;
  });
}
