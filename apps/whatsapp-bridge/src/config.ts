// ──────────────────────────────────────────
// Configuração via environment variables
// ──────────────────────────────────────────

import dotenv from 'dotenv';
import type { Config } from './types';

dotenv.config();

export const config: Config = {
  fastApiUrl: process.env.FASTAPI_URL || 'http://localhost:8000',
  apiKey: process.env.WHATSAPP_API_KEY || 'bagcoin_webhook_secret_123',
  port: parseInt(process.env.PORT || '3001', 10),
  dedupTtlMs: 30 * 1000,          // 30s
  maxReplyLength: 4000,            // caracteres por chunk
  webhookTimeout: 120_000,         // 2min
  sendSeen: false,                 // não marca como lido (sem ✓✓ azul)
  showTyping: true,                // mostra "digitando..." durante processamento
};
