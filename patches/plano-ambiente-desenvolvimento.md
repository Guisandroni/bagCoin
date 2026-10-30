# Plano: simplificação do ambiente de desenvolvimento

Registro das decisões combinadas para a alteração implementada após o plano da Evolution API.

1. Remover as configurações Compose antigas, a configuração de produção e o Traefik; manter uma única composição para desenvolvimento.
2. Remover os contêineres e volumes Docker pertencentes ao bagCoin, incluindo os dados antigos, preservando recursos de outros projetos.
3. Iniciar frontend, backend, PostgreSQL, Redis e Evolution API na nova composição. Manter PostgreSQL e Redis acessíveis pela rede Docker e habilitar recarga automática do frontend e do backend.
4. Remover do projeto Telegram, bridge legada de WhatsApp, Celery, Beat, Flower e Mailpit. Remover o campo de Telegram com migração Alembic, preservando as migrações históricas e a integração financeira via WhatsApp.
5. Manter confirmação de e-mail e recuperação de senha, com Resend como provedor padrão.
6. Manter a Evolution API v2.3.7 somente para desenvolvimento e experimentação, aceitando temporariamente o risco conhecido; atualizar e reavaliar antes de expor o projeto online.
7. Atualizar as instruções operacionais e verificar a configuração. A execução de testes foi inicialmente adiada por solicitação do usuário e posteriormente autorizada para a inicialização do Compose.

O plano original da integração permanece em [plano-evolution-api.md](plano-evolution-api.md).
