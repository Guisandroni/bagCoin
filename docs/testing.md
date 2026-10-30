# Testes

Os testes existentes do backend ficam em `apps/server/tests/`. A cobertura atual é limitada; não presuma que todos os fluxos de API, frontend ou WhatsApp estejam cobertos.

Quando for apropriado executar os testes disponíveis:

```sh
cd apps/server
uv run pytest tests/
```

A inicialização local dos serviços está descrita no [README](../README.md). Testar a integração real do WhatsApp exige uma instância Baileys conectada e um número de teste; verificações da API isoladamente não confirmam a entrega de mensagens.
