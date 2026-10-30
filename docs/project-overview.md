# BagCoin — visão geral

O BagCoin é um assistente financeiro acessível pela aplicação web e pelo WhatsApp. O backend FastAPI usa LangGraph para processar mensagens e SQLAlchemy com PostgreSQL para persistir dados financeiros. O frontend usa Next.js.

A Evolution API integra o WhatsApp ao backend. Eventos chegam pelo webhook da API, são registrados para evitar processamento duplicado e encaminhados ao agente. O backend envia as respostas pela Evolution. Redis também atende recursos do backend e da Evolution.

O Compose de desenvolvimento contém frontend, backend, PostgreSQL, Redis, Evolution e um serviço de inicialização do banco da Evolution. Consulte o [README](../README.md) para configuração, portas e inicialização, e [CONTEXT.md](../CONTEXT.md) para o domínio.

O backend aplica as migrações Alembic ao iniciar. As configurações de envio de e-mail usam Resend como padrão. O ambiente descrito é local e não constitui uma configuração de produção.
