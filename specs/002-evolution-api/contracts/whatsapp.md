# Contratos de integração

A API pública existente e o fluxo Telegram são preservados. O novo endpoint interno recebe somente eventos da instância autorizada com autenticação suportada pela versão escolhida; falhas de autenticação não acionam processamento. Contratos exatos dos eventos e operações de envio/mídia devem ser verificados contra fontes oficiais e testes com a versão fixada antes da implementação.

O processamento ignora mensagens próprias, grupos e tipos desconhecidos. Para eventos aceitos, resolve telefone seguro, obtém mídia limitada e encaminha conteúdo ao agente existente. Respostas de texto e relatórios PDF devem ser enviados ao mesmo destinatário de maneira ordenada.

O sucesso de recebimento e as regras de reentrega devem refletir resultados reais. A deduplicação não pode perder uma mensagem em falha nem repetir uma transação já persistida; falha entre persistência e envio deve ter tratamento e teste explícitos. Uma integração que ainda não garanta isso não satisfaz o contrato.

## Referência verificada apenas na 2.3.7 (vulnerável)

Evento `messages.upsert` inclui `data.key.id`, `fromMe`, `remoteJid` e conteúdo em `data.message`; `remoteJidAlt` só é utilizável se for um JID telefônico confiável. A API usa `apikey`; `sendText` recebe `{number,text}`, `sendMedia` recebe `{number,mediatype,mimetype,fileName,media}` e `getBase64FromMediaMessage` recebe `{message,convertToMp4:false}`. Os headers do webhook são configurados por instância; o corpo pode conter `apikey` e não deve ser registrado. Isso é evidência para pesquisa, não autorização para usar a versão vulnerável; revalidar na versão corrigida.
