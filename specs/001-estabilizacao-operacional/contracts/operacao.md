# Contratos operacionais

- Os ambientes declarados devem referenciar contextos existentes, construir imagens relevantes e preservar volumes e redes existentes.
- A API deve iniciar no processo e porta definidos pela configuração; verificações de saúde devem falhar quando o endpoint responder com erro HTTP.
- Em PR para `develop`, os checks de backend e frontend selecionados devem produzir resultados e a proteção, quando configurável, deve impedir merge com falhas.
- A investigação é somente leitura: não consome filas, não altera dados nem remove serviços. Permissões insuficientes e evidências indisponíveis são registradas.
- APIs públicas e modelos de dados permanecem inalterados; seus contratos existentes continuam autoritativos.
