# Tabelas criadas pelo Invec no banco Firebird

O Invec cria suas próprias tabelas no mesmo banco Firebird do Automec (MIAUTOMEC.FDB). Todas são criadas automaticamente na primeira execução do servidor via `migrations.py` — sem necessidade de rodar scripts manuais.

---

## Tabelas novas

### `OPERADORES_APP`

Cadastro dos operadores físicos de coleta — as pessoas que pegam o coletor e fazem a contagem. Separado dos `USUARIOS` do Automec: um operador pode não ter login no sistema.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| ID | INTEGER (auto) | Chave primária |
| NOME | VARCHAR(100) | Nome do operador |
| ATIVO | SMALLINT | `1` = ativo, `0` = desativado |

---

### `INVENTARIO_SESSAO`

Controla cada sessão de contagem por celular/depósito. Permite múltiplos operadores contando ao mesmo tempo em depósitos diferentes e rastreia o estado de cada sessão.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| SESSION_ID | VARCHAR(36) | UUID gerado pelo celular — chave primária |
| CDDEPOSITO | INTEGER | Depósito sendo contado |
| OPERADOR | VARCHAR(100) | Nome do operador físico |
| USUARIO | VARCHAR(50) | Login do usuário no app |
| STATUS | VARCHAR(20) | `ABERTA`, `CONSOLIDANDO`, `CONSOLIDADA`, `ENCERRADA` |
| INICIO | TIMESTAMP | Quando a sessão foi criada |
| FIM | TIMESTAMP | Quando foi consolidada/encerrada |

---

### `LOG_INVENTARIO`

Auditoria completa de todas as operações sensíveis. Permite rastrear fraudes e contestar contagens.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| ID | INTEGER (auto) | Chave primária |
| TIPO | VARCHAR(20) | Tipo do evento (ver tabela abaixo) |
| CDDEPOSITO | INTEGER | Depósito |
| CDPRODUTO | INTEGER | Produto afetado |
| PRODUTO | VARCHAR(200) | Nome do produto no momento do evento |
| OPERADOR | VARCHAR(100) | Operador físico |
| LOGIN_USUARIO | VARCHAR(50) | Usuário logado no app |
| QTDE_ANTES | DECIMAL(15,4) | Quantidade antes da operação |
| QTDE_DEPOIS | DECIMAL(15,4) | Quantidade depois da operação |
| MOTIVO | VARCHAR(500) | Texto livre + alertas automáticos gerados pelo sistema |
| DEVICE_ID | VARCHAR(100) | ID do celular (Android ID) |
| SESSION_ID | VARCHAR(36) | Sessão em que o evento ocorreu |
| DATA_HORA | TIMESTAMP | Data e hora exatos |

**Tipos de evento:**

| Tipo | Quando é gerado |
|------|-----------------|
| `EDICAO` | Operador alterou manualmente a quantidade de um produto |
| `EDICAO_SUSPEITA` | Edição que faz a quantidade coincidir exatamente com o sistema, ou redução > 30% por operador |
| `EXCLUSAO` | Item removido da contagem (swipe no relatório) |
| `ALERTA` | Scan resultou em quantidade > 2× o estoque do sistema |
| `ALERTA_REESCAN` | Produto que havia sido excluído da sessão foi escaneado novamente |
| `CONSOLIDACAO` | Sessão consolidada — gravação em MOV_PRODUTO realizada |
| `LOGIN_FALHOU` | Tentativa de login com senha errada (controle de brute force) |

**Retenção automática** (executada no startup do servidor):

| Tipos | Retenção |
|-------|----------|
| `BIPAGEM` | 90 dias |
| `EDICAO`, `ALERTA`, `LOGIN_FALHOU` | 365 dias |
| `EDICAO_SUSPEITA`, `ALERTA_REESCAN`, `EXCLUSAO`, `CONSOLIDACAO` | **Permanente** |

---

### `LOTES_SYNC_PROCESSADOS`

Garante idempotência dos lotes offline. Se o celular perder conexão após o servidor processar mas antes de receber a resposta e reenviar o mesmo lote, o servidor identifica o `lote_id` duplicado e ignora sem contar dobrado.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| LOTE_ID | VARCHAR(36) | UUID do lote — chave primária |
| SESSION_ID | VARCHAR(36) | Sessão à qual o lote pertence |
| DATA_HORA | TIMESTAMP | Quando foi processado |

Limpeza automática após 90 dias.

---

### `SCANS_PROCESSADOS`

Idempotência por scan individual. Se o celular faz um scan online, a rede cai antes de receber resposta e o SyncManager reenviar o mesmo scan via lote — o servidor detecta o `scan_id` duplicado e ignora, sem duplicar a quantidade em `INVENTARIO_TEMP`.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| SCAN_ID | VARCHAR(36) | UUID do scan — chave primária |
| SESSION_ID | VARCHAR(36) | Sessão do scan |
| CDPRODUTO | INTEGER | Produto bipado |
| DATA_HORA | TIMESTAMP | Quando foi processado |

Limpeza automática após 90 dias.

---

### `USUARIO_DEPOSITO`

Controle de acesso por depósito. Se houver registros para um usuário, ele só acessa os depósitos listados. Se não houver nenhum registro para o usuário, ele acessa todos os depósitos (compatibilidade com instalações existentes).

| Campo | Tipo | Descrição |
|-------|------|-----------|
| IDUSUARIO | INTEGER | ID do usuário (tabela `USUARIOS` do Automec) |
| CDDEPOSITO | INTEGER | Código do depósito permitido |

Chave primária composta: `(IDUSUARIO, CDDEPOSITO)`.

---

## Colunas adicionadas em tabelas existentes do Automec

O Invec nunca remove nem altera colunas existentes — apenas adiciona.

| Tabela | Coluna | Tipo | Motivo |
|--------|--------|------|--------|
| `INVENTARIO_TEMP` | `OPERADOR` | VARCHAR(100) | Identifica quem fez cada bipagem |
| `INVENTARIO_TEMP` | `QTDEATUAL_SNAP` | DECIMAL(15,4) | Estoque no momento do scan — baseline fixo para a consolidação, independente de movimentações posteriores |
| `INVENTARIO_TEMP` | `SESSION_ID` | VARCHAR(36) | Permite múltiplas sessões simultâneas no mesmo depósito sem conflito |
| `INVENTARIO_TEMP` | `ORIGEM` | VARCHAR(20) | Valor `'INVEC'` — impede que o `DELETE` do app apague linhas gravadas pelo Automec na mesma tabela |
| `INVENTARIO` | `OPERADOR` | VARCHAR(100) | Registra o operador no histórico de inventário do Automec |
| `USUARIOS` | `SENHAMOBILE` | VARCHAR(100) | Senha exclusiva para o app (a senha normal do Automec é hasheada e não funciona no app) |
| `USUARIOS` | `MOBILE_ADMIN` | SMALLINT | `1` = usuário pode gerenciar acesso de outros usuários no app |

---

## Índices criados

Todos criados automaticamente. Nenhum afeta tabelas nativas do Automec.

| Índice | Tabela | Colunas | Motivo |
|--------|--------|---------|--------|
| `IDX_LOG_INV_DEPOSITO` | `LOG_INVENTARIO` | `CDDEPOSITO` | Consulta de auditoria por depósito |
| `IDX_LOG_INV_DATA` | `LOG_INVENTARIO` | `DATA_HORA` DESC | Ordenação por data no log |
| `IDX_LOG_INV_TIPO` | `LOG_INVENTARIO` | `TIPO` | Limpeza por tipo na subida do servidor |
| `IDX_LOG_SESSION` | `LOG_INVENTARIO` | `SESSION_ID, TIPO` | Detecção de edições por sessão |
| `IDX_INVTEMP_PROD_DEP` | `INVENTARIO_TEMP` | `CDPRODUTO, CDDEPOSITO` | Busca de bipagens por produto/depósito |
| `IDX_INVTEMP_SESSION` | `INVENTARIO_TEMP` | `SESSION_ID, CDDEPOSITO` | Leitura por sessão no relatório e consolidação |
| `IDX_INVTEMP_PROD_DEP_SES` | `INVENTARIO_TEMP` | `CDPRODUTO, CDDEPOSITO, SESSION_ID` | Verifica produtos não contados (NOT EXISTS) |
| `IDX_LOTES_SESSION` | `LOTES_SYNC_PROCESSADOS` | `SESSION_ID` | Limpeza de lotes por sessão |
| `IDX_SCANS_SESSION` | `SCANS_PROCESSADOS` | `SESSION_ID` | Limpeza de scan_ids por sessão |
| `IDX_USUDEP_USUARIO` | `USUARIO_DEPOSITO` | `IDUSUARIO` | Verificação de permissão por usuário |
