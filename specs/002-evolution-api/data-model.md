# Modelo e invariantes

- **Instância**: nome configurado e estado conectado/desconectado; sessão persistida pela Evolution, não pelo backend.
- **Evento**: ID estável e origem verificável, tipo suportado, mensagem e identidade confiável. Eventos próprios/grupo são ignorados. Entradas ambíguas não podem ser atribuídas a usuário financeiro.
- **Processamento**: deduplicação deve distinguir em andamento, concluído e falha, evitar processamento concorrente e manter segurança financeira em reentregas. Falha de envio após persistência precisa ser tratada sem repetir a operação financeira. A solução deve demonstrar comportamento em falha intermediária e reinício antes de declarar equivalência.
- **Vínculo**: associação existente entre telefone normalizado e usuário; não criar associação baseada em LID sem resolução confiável.

Nenhuma migração de modelo financeiro deve ser feita sem necessidade e avaliação explícita. Armazenamento da Evolution pertence a banco isolado e sessão em volume dedicado.

## Idempotência: desenho conservador para eventos Evolution

### Limitações observadas no fluxo atual

`apps/server/app/api/routes/v1/webhook.py` marca a mensagem no Redis antes de processá-la, com expiração de 60 segundos, e prossegue sem deduplicação quando o Redis não está disponível. O orquestrador executa operações em sessões próprias: por exemplo, `apps/server/app/agents/persistence.py` confirma uma transação financeira e pode confirmar uma recorrência separadamente; `pending_actions.py` e `budget_service.py` também fazem commits próprios. Portanto, um `SET NX`, lock com prazo ou registro salvo depois de `orchestrator.invoke()` não torna os efeitos e o reconhecimento do evento atômicos. Também há funções que capturam exceções; a ausência de exceção no endpoint, por si só, não prova sucesso financeiro.

### Registro durável e estados

Criar em PostgreSQL um registro de evento de entrada com chave única `(instancia, id_mensagem)`, ambos obrigatórios e validados, mais estado, timestamps, tentativa proprietária aleatória, estado/erro sanitizado e referência ao resultado quando conhecido. A chave inclui a instância porque IDs não devem ser presumidos globais. Não usar telefone, conteúdo, timestamp ou hash heurístico como substituto do ID; sem ID confiável, rejeitar sem executar o orquestrador.

Estados: `recebido` → `em_processamento` → `concluido` ou `incerto`. `recebido` só pode ser assumido por uma tentativa via atualização condicional atômica; depois que `em_processamento` for confirmado, **nenhuma reentrega, expiração ou reinício pode iniciar automaticamente outra invocação**. Uma falha ou interrupção antes de registrar o resultado muda ou deixa o evento em estado que exige reconciliação; um processo morto ou timeout não prova ausência de efeitos, nem autoriza retomada automática. Duplicatas concorrentes devem observar o registro existente e nunca executar o orquestrador novamente. Sem banco disponível, rejeitar com erro transitório antes de efetuar qualquer ação financeira.

Registrar um evento durável e sua aceitação apenas depois de autenticar, validar instância e ID, filtrar eventos e validar identidade. A execução deve ser síncrona à requisição ou operada por processamento durável que efetivamente consuma registros `recebido`; não responder sucesso por trabalho que exista apenas em memória. Se uma invocação retorna, `concluido` requer inspeção dos erros e resultados de domínio explícitos, e a resposta gerada deve ser persistida no mesmo commit da transição para `concluido`. Se resultado financeiro for desconhecido, parcial ou não verificável, registrar `incerto`; não repetir a mensagem. Informações armazenadas devem ser mínimas, com acesso restrito e política de retenção apropriada para dados financeiros.

Esse desenho fornece **no máximo uma invocação automática por chave de evento** desde que toda entrada Evolution obrigatoriamente passe por esse gate e a chave estável seja a mesma em reentregas. Ele não garante conclusão automática, atomicidade entre várias ações dentro da invocação, nem impede duplicatas decorrentes de IDs distintos, outros canais, ação humana ou bugs internos. Um crash após um commit financeiro e antes de `concluido` deixa `incerto`: reconciliar os registros de domínio e histórico com evidências; reaplicar só mediante procedimento explícito e prova de ausência de efeitos. Um recebimento legítimo que falhe antes do commit financeiro também pode exigir intervenção; esta perda de disponibilidade é deliberada até implementar idempotência transacional no domínio.

### Entrega de resposta e janela ambígua

Armazenar os itens de saída ordenados (texto fragmentado e eventual referência segura ao PDF) e seu estado durável separado do efeito financeiro. Registrar `enviando` antes de chamar a Evolution e `enviado` após confirmação verificável. Se a chamada falhar comprovadamente antes de ser transmitida, poderá ser reenfileirada; timeout, conexão interrompida ou crash depois de iniciar o envio é `envio_incerto` e não deve ser reenviado automaticamente, pois o provedor pode já ter entregue. Se a versão selecionada oferecer chave idempotente documentada e verificável para envio, só então adotar repetição com essa chave; sem ela, a entrega exata não é garantida e o operador precisa reconciliar. Falha de envio nunca deve reinvocar a ação financeira concluída. Evitar registrar payloads completos, dados bancários, mídia ou credenciais nos logs.

### Evolução para recuperação automática

Para retomar automaticamente após qualquer crash, propagar `(instancia, id_mensagem, indice_de_acao)` até **cada** mutação de domínio e persistir o marcador único com o efeito financeiro na mesma transação de banco, ou refatorar a execução para uma unidade de trabalho comum. Os múltiplos commits e sessões atuais, incluindo recorrência e confirmação pendente, impedem declarar essa garantia hoje. Antes de habilitar retries automáticos, cobrir todas as ferramentas e efeitos, inclusive concorrência, ações parciais e tarefas recorrentes; uma tabela de entrada separada não é suficiente.

### Verificações obrigatórias

Exercitar duas entregas concorrentes com a mesma chave; repetição após mais de 60 segundos e após reinício; banco indisponível antes da recepção; crash antes da ação, durante os commits e entre commit financeiro e gravação do resultado; crash e timeout antes/depois do envio externo; múltiplas ações e recorrência parcialmente concluídas; e reconciliação de `incerto`. Em todos os casos, verificar que a mesma chave não gera uma segunda invocação automática nem duplicação financeira e que a resposta não é repetida automaticamente após envio ambíguo.
