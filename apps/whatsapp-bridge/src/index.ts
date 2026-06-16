// ──────────────────────────────────────────
// WhatsApp Bridge — BagCoin (TypeScript)
// ──────────────────────────────────────────
//
// Bridge entre WhatsApp Web (whatsapp-web.js) e a API FastAPI do BagCoin.
// - Escuta mensagens do WhatsApp
// - Envia para a API FastAPI via webhook
// - Gerencia mídia (imagem, áudio, documento)
// - Endpoint /send para envio manual de mensagens
// - Deduplicação em memória
// - Health check
// ──────────────────────────────────────────

import { Client, LocalAuth, MessageMedia } from 'whatsapp-web.js';
import qrcode = require('qrcode-terminal');
import express from 'express';

import { config } from './config';
import { isDuplicate } from './dedup';
import { sendToFastApi, hasReply, isDocumentResponse } from './api';
import { cleanupChromiumLocks, normalizeChatId, splitMessage } from './utils';
import type { WebhookPayload, HealthStatus } from './types';

// ── Express ─────────────────────────────────

const app = express();
app.use(express.json({ limit: '50mb' }));

// ── WhatsApp Client ─────────────────────────

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: './whatsapp-session' }),
  puppeteer: {
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || '/usr/bin/chromium',
    headless: true,
    protocolTimeout: 120_000,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-features=IsolateOrigins,site-per-process',
      '--disable-gpu',
      '--disable-extensions',
      '--no-first-run',
      '--no-zygote',
      '--disable-background-networking',
      '--disable-background-timer-throttling',
      '--disable-renderer-backgrounding',
      '--disable-backgrounding-occluded-windows',
      '--disable-breakpad',
      '--disable-client-side-phishing-detection',
      '--disable-component-update',
      '--disable-default-apps',
      '--disable-hang-monitor',
      '--disable-popup-blocking',
      '--disable-prompt-on-repost',
      '--disable-sync',
      '--force-color-profile=srgb',
      '--metrics-recording-only',
      '--safebrowsing-disable-auto-update',
      '--enable-automation',
      '--password-store=basic',
      '--use-mock-keychain',
    ],
  },
});

// ── Eventos do WhatsApp ────────────────────

client.on('qr', (qr: string) => {
  console.log('\n🔄 Escaneie o QR Code abaixo para conectar:');
  console.log('RAW_QR_DATA_START');
  console.log(qr);
  console.log('RAW_QR_DATA_END');
  qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
  console.log('\n✅ WhatsApp client conectado e pronto!');
  console.log(`📱 Bridge rodando na porta ${config.port}`);
});

client.on('auth_failure', (message) => {
  console.error('❌ Falha de autenticação do WhatsApp:', message);
});

client.on('disconnected', (reason) => {
  console.error('❌ WhatsApp desconectado:', reason);
});

// Usa 'message' em vez de 'message_create' para evitar duplicatas
client.on('message', async (msg) => {
  // Ignora mensagens do próprio bot e de grupos
  if (msg.fromMe || msg.from.includes('@g.us')) return;

  // Deduplicação
  const msgId: string = msg.id?._serialized ?? String(msg.id);
  if (isDuplicate(msgId)) {
    console.log(`⏭️ Mensagem ${msgId} já processada. Ignorando.`);
    return;
  }

  console.log(`\n📩 Mensagem de ${msg.from}: ${msg.body || '(mídia)'}`);

  // ── Presença ──
  const chat = await msg.getChat();
  if (config.sendSeen) {
    await chat.sendSeen();
  }
  if (config.showTyping) {
    await chat.sendStateTyping();
  }

  // Constrói payload para a API
  const payload: WebhookPayload = {
    phone_number: msg.from.replace('@c.us', ''),
    message: msg.body || '',
    type: msg.type,
    timestamp: msg.timestamp,
    hasMedia: msg.hasMedia,
    raw_data: {
      id: msgId,
      from: msg.from,
      to: msg.to,
      deviceType: msg.deviceType,
      ack: msg.ack,
    },
  };

  // Anexa mídia se houver
  if (msg.hasMedia) {
    try {
      const media = await msg.downloadMedia();
      if (media) {
        payload.media = {
          mimetype: media.mimetype,
          data: media.data,
          filename: media.filename ?? undefined,
        };
        console.log(`📎 Mídia: ${media.mimetype}`);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        console.error('Erro ao baixar mídia:', err.message);
      }
    }
  }

  // Envia para a API FastAPI
  const data = await sendToFastApi(payload);

  // Limpa estado de digitando
  if (config.showTyping) {
    await chat.clearState();
  }

  // Resposta de texto
  if (hasReply(data)) {
    await sendReply(msg.from, data.reply);
  }

  // Resposta com documento (PDF, etc.)
  if (isDocumentResponse(data)) {
    try {
      const media = new MessageMedia(data.document.mimetype, data.document.data, data.document.filename);
      await client.sendMessage(msg.from, media, { caption: 'Seu relatório 📊' });
      console.log(`📄 Documento enviado: ${data.document.filename}`);
    } catch (err: unknown) {
      if (err instanceof Error) {
        console.error('Erro ao enviar documento:', err.message);
      }
    }
  }
});

// ── Função auxiliar para envio de reply ────

function isRetryableSendError(err: unknown): boolean {
  if (!(err instanceof Error)) return false;
  return /Runtime\.callFunctionOn timed out|protocolTimeout|Target closed|Execution context was destroyed/i.test(err.message);
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function sendReply(to: string, text: string): Promise<void> {
  try {
    const chunks = splitMessage(text);
    for (const chunk of chunks) {
      try {
        await client.sendMessage(to, chunk);
      } catch (err: unknown) {
        if (!isRetryableSendError(err)) {
          throw err;
        }
        if (err instanceof Error) {
          console.warn(`⚠️ Timeout ao enviar resposta para ${to}. Tentando novamente: ${err.message}`);
        }
        await delay(1500);
        await client.sendMessage(to, chunk);
      }
    }
    console.log(`📤 Resposta enviada para ${to}`);
  } catch (err: unknown) {
    if (err instanceof Error) {
      console.error('Erro ao enviar resposta:', err.message);
    }
  }
}

// ── Endpoint: enviar mensagem manualmente ──

app.post('/send', async (req, res) => {
  try {
    const { phone_number, message } = req.body as { phone_number?: string; message?: string };

    if (!phone_number || !message) {
      res.status(400).json({ error: 'phone_number e message são obrigatórios' });
      return;
    }

    const chatId = normalizeChatId(phone_number);
    await client.sendMessage(chatId, message);
    res.json({ success: true, message: 'Mensagem enviada' });
  } catch (err: unknown) {
    if (err instanceof Error) {
      console.error('Erro no /send:', err.message);
      res.status(500).json({ error: err.message });
    }
  }
});

// ── Health check ────────────────────────────

app.get('/health', (_req, res) => {
  const status: HealthStatus = {
    status: 'ok',
    connected: !!client.info,
    uptime: process.uptime(),
    whatsappNumber: client.info?.wid?.user
      ? `${client.info.wid.user}@c.us`
      : undefined,
  };
  res.json(status);
});

// ── Startup ─────────────────────────────────

console.log('🧹 Limpando locks do Chromium...');
cleanupChromiumLocks();

client.initialize();

app.listen(config.port, () => {
  console.log(`🚀 WhatsApp Bridge rodando em http://localhost:${config.port}`);
  console.log('Aguardando conexão com WhatsApp...');
});

// ── Graceful Shutdown ───────────────────────

process.on('SIGINT', async () => {
  console.log('\n👋 Desconectando WhatsApp...');
  try {
    await client.destroy();
  } catch {
    // ignora erro no shutdown
  }
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\n👋 SIGTERM recebido. Desconectando...');
  try {
    await client.destroy();
  } catch {
    // ignora
  }
  process.exit(0);
});
