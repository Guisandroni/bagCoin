// ──────────────────────────────────────────
// Tipos e interfaces do WhatsApp Bridge
// ──────────────────────────────────────────

export interface MediaPayload {
  mimetype: string;
  data: string;
  filename?: string;
}

export interface WebhookPayload {
  phone_number: string;
  message: string;
  type?: string;
  timestamp?: number;
  hasMedia?: boolean;
  media?: MediaPayload;
  raw_data?: Record<string, unknown>;
}

export interface WebhookResponse {
  reply?: string;
  document?: {
    mimetype: string;
    data: string;
    filename: string;
  };
  actions?: string[];
}

export interface HealthStatus {
  status: 'ok' | 'error';
  connected: boolean;
  uptime: number;
  whatsappNumber?: string;
}

export interface SendRequest {
  phone_number: string;
  message: string;
}

export interface Config {
  fastApiUrl: string;
  apiKey: string;
  port: number;
  dedupTtlMs: number;
  maxReplyLength: number;
  webhookTimeout: number;
  sendSeen: boolean;
  showTyping: boolean;
}
