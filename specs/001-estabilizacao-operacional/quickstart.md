# Guia de validação

Execute após implementar as alterações, a partir da raiz. Consulte [contratos operacionais](contracts/operacao.md) e [pesquisa](research.md).

## Pré-requisitos e isolamento

Docker/Compose, dependências de backend e frontend e variáveis necessárias devem estar disponíveis. Use banco e volumes descartáveis; o entrypoint executa migrações. Verifique previamente colisões de portas e nomes fixos de contêiner: `-p` não os isola. Não use volumes existentes nem `down -v` em ambiente real.

## Configuração e smoke

1. Execute `docker compose -f docker-compose.dev.yml config --quiet` e `docker compose -f docker-compose.frontend.yml config --quiet` com suas variáveis locais; ambas devem terminar sem erro.
2. Valide `docker-compose.prod.yml` com variáveis fictícias não sensíveis e `docker compose -f docker-compose.prod.yml config --quiet`; não publique a configuração expandida nem inicie produção.
3. Construa as imagens relevantes das três configurações. Em ambiente isolado, inicie os serviços essenciais locais e verifique o endpoint de saúde e as dependências. Registre comandos, resultados e eventuais bloqueios; preserve os dados existentes.

## CI

No backend, execute as verificações equivalentes aos workflows: Ruff, formatação, ty e pytest com cobertura, com PostgreSQL e Redis de teste. No frontend, execute `npm run lint`, `npm run build` e `npm run test` em `apps/web`; avalie `npm run test:e2e` separadamente com seus pré-requisitos. Não reduza o limite de cobertura para obter aprovação.

Abra um PR de teste para `develop`, confirme os nomes e resultados reais dos checks e, com permissões, confira que uma falha bloqueia a integração. Caso contrário, registre a configuração pendente. Compare a documentação com as configurações finais.
