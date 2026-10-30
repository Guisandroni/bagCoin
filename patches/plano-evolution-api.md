# Plano de migração do WhatsApp para Evolution API

## Objetivo e decisões

Substituir integralmente a bridge baseada em `whatsapp-web.js` por integração direta do backend com a Evolution API. O projeto ainda não está online; a mudança e os testes serão feitos no ambiente local. Não há necessidade de migração sem interrupção.

- Executar Evolution API no mesmo servidor, em contêiner Docker, com uma única instância de WhatsApp compartilhada pelos usuários.
- Usar o painel da Evolution para criar/conectar a instância por QR Code; existe um número disponível para testes reais.
- Compartilhar os serviços de PostgreSQL e Redis existentes, usando banco próprio e isolamento de cache para a Evolution. Não compartilhar tabelas nem credenciais administrativas entre aplicações.
- Fixar inicialmente `evoapicloud/evolution-api:v2.3.7`, sujeito à confirmação de disponibilidade da imagem e compatibilidade durante a implementação. A versão 2.4.0-rc2 é pré-lançamento e não será usada como padrão.
- Manter a identidade financeira e os vínculos existentes por telefone; Telegram permanece inalterado.

## Escopo funcional

Preservar o comportamento atual para mensagens individuais de texto, imagem, áudio e documentos; extração e encaminhamento de mídia ao agente; resposta textual, divisão de mensagens longas e entrega de relatórios PDF. Ignorar mensagens próprias e de grupos; manter deduplicação por identificador de mensagem e o fluxo de vinculação da conta. Avaliar e preservar, onde disponíveis, envio de visto e indicador de digitação e registrar diferenças verificadas.

A conexão por QR e o estado da instância ficam sob responsabilidade do painel Evolution. Rotas e serviços internos que hoje chamam a bridge devem ser migrados ou removidos junto com seus consumidores, sem alterar contratos públicos desnecessariamente.

## Etapas

1. **Contratos e infraestrutura**: conferir a documentação e os payloads reais da versão fixada para criação e conexão de instância, eventos de mensagem, recuperação de mídia e envio de texto/documento. Adicionar Evolution ao Compose de desenvolvimento e às configurações de produção pertinentes, com persistência própria, banco separado, prefixo de cache isolado, dependências saudáveis e credenciais via variáveis de ambiente. Preservar volumes e dados atuais; atualizar exemplos e documentação. Não usar `latest`.
2. **Recebimento**: criar endpoint autenticado no backend para eventos da Evolution. Verificar origem e instância, ignorar eventos não suportados, mensagens próprias e grupos; identificar e normalizar telefone/JID/LID com base em dados confiáveis. Não associar identificador ambíguo ao usuário errado. Converter texto e mídia para o contrato interno existente e acionar o processamento financeiro e o vínculo de identidade.
3. **Envio**: implementar cliente HTTP no backend para enviar textos e PDFs pela instância configurada; preservar ordenação e fragmentação de respostas e tratar indisponibilidade, timeouts e erros sem registrar segredos ou conteúdo sensível. Não repetir envios sem considerar o risco de duplicação.
4. **Idempotência e falhas**: usar IDs estáveis e deduplicação compartilhada para evitar processamento duplicado; definir atomicidade e tratamento de falhas e reentregas conforme o contrato confirmado da versão escolhida. Não reconhecer como concluída uma ação que falhou; garantir que reentregas não criem transações financeiras duplicadas.
5. **Remoção da bridge antiga**: após validar os fluxos equivalentes, retirar `apps/whatsapp-bridge`, referências a `whatsapp-web.js`/Chromium, serviços, variáveis e instruções obsoletas. Não excluir sessões ou volumes existentes automaticamente. Ajustar health/status e consumidores internos ao novo serviço, preservando Telegram.
6. **Operação e documentação**: documentar criação do banco, inicialização local, configuração do webhook autenticado, conexão e reconexão por QR, checagem de saúde, backup de dados da Evolution e desligamento. Não expor chave administrativa ou painel publicamente por padrão. Atualizar o grafo após alterações de código.

## Validação e critérios de aceite

- Subir o Compose em ambiente isolado com banco e volumes descartáveis; confirmar saúde da aplicação, Evolution, banco e Redis sem tocar nos dados existentes.
- Validar eventos simulados de texto, áudio, imagem e documento, incluindo mídia ausente ou inválida, identificadores LID ambíguos, mensagens próprias/de grupo, duplicatas e falha temporária da Evolution. Confirmar autenticação, limites de entrada e que falhas não persistem transações indevidas.
- Conectar o número de teste no painel e, com internet, enviar mensagens reais de texto e mídia; verificar resposta, vínculo do usuário e envio de PDF. Reiniciar serviços e confirmar persistência/reconexão da instância.
- Verificar que a integração Telegram e o acesso web não regrediram. Como as suítes anteriores foram removidas por decisão do projeto, definir verificações automatizadas mínimas para os novos fluxos e executar os smoke tests necessários sem pressupor testes antigos.
- Confirmar que não restam referências operacionais à bridge antiga e que as configurações de desenvolvimento e produção correspondem à documentação. Nenhum deploy de produção está incluído.

## Referências e pendências

- [Releases oficiais](https://github.com/evolution-foundation/evolution-api/releases)
- [Exemplo oficial de instalação Docker](https://github.com/evolution-foundation/docs-evolution/blob/main/v2/en/install/docker.mdx)
- [Eventos de webhook](https://github.com/evolution-foundation/evolution-docs/blob/main/docs/02-Configuration/Webhooks.md)
- A autenticação de webhooks, os formatos de mensagens/mídias, limites e a política segura de reentrega devem ser confirmados para a versão fixada antes de implementar. A ausência de usuários em produção não elimina a necessidade de preservar dados locais existentes.
