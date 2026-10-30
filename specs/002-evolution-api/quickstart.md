# Verificação local

1. O usuário aceitou v2.3.7 vulnerável somente para teste local; confirmar versão corrigida antes de produção. A execução dos testes está suspensa por enquanto. Ver [research.md](research.md) e [contratos](contracts/whatsapp.md).
2. Preparar Docker com banco, Redis e volumes isolados e credenciais locais; evitar colisões de portas/nomes e preservar dados existentes. O entrypoint atual executa migrações. Iniciar a aplicação e a Evolution sem deploy.
3. Executar testes automatizados do novo webhook/cliente: autenticação, instância, filtro, tamanho de mídia, telefone/LID, deduplicação concorrente, falhas antes/depois da persistência, texto e PDF. Confirmar que Telegram não regrediu.
4. Configurar webhook autenticado e instância no painel; com internet, conectar número de teste por QR. Enviar texto, áudio, imagem e documento e solicitar PDF; verificar vínculo, resposta e ausência de duplicação. Reiniciar serviços e validar sessão.
5. Encerrar somente os recursos descartáveis criados para o teste. Registrar limitações, status e evidência sem expor conteúdo financeiro ou credenciais.
