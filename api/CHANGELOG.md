# CHANGELOG — Invec API

## [1.3.2] — 2026-06-25

### Correções de bugs

#### `app/routers/inventario.py`

- **Bug crítico — PK_INVENTARIO_TEMP bloqueava toda bipagem**: `UPDATE` filtrava por `SESSION_ID` no `WHERE`, resultando em `rowcount=0` quando já existia linha para `(CDPRODUTO, CDDEPOSITO)` de sessão anterior ou inserida pelo Automec. O `INSERT` subsequente falhava com violação de `PRIMARY KEY`. Fix: `WHERE` usa apenas `(CDPRODUTO, CDDEPOSITO)`; `SESSION_ID`, `QTDEATUAL_SNAP` e `ORIGEM` são atualizados no `SET`.
- **Bipagem em linha do Automec acumulava em vez de substituir**: `UPDATE` fazia `QTDE + scan_qty` sobre linha de sessão anterior ou do Automec. Nova lógica em 3 passos: ① `UPDATE` com `SESSION_ID` — acumula na sessão atual; ② se `rowcount=0`: `UPDATE` sem `SESSION_ID`, `SET QTDE = scan_qty` — substitui a contagem existente; ③ se ainda `rowcount=0`: `INSERT`. Mesma lógica aplicada em `/bipagem/lote`.
- **Lote aceita delta negativo**: `net_qtde <= 0` substituído por `net_qtde == 0` — edições offline com resultado negativo não são mais descartadas.

#### `app/routers/produtos.py`

- **EAN-13 vs UPC-A — zeros iniciais**: nova função `_barcode_variants()` gera ambas as formas do código (12 dígitos UPC-A e 13 dígitos EAN-13 com zero prefixo). A query usa `IN()` para encontrar qualquer variante — resolve produto não encontrado quando scanner retorna formato diferente do ERP.

#### `instalador.py`

- **Firewall 100% automático** — 5 cenários cobertos:
  1. `MpsSvc` ausente (Windows sem Firewall) → pula, porta já acessível
  2. `MpsSvc` parado → inicia via `sc start` antes de adicionar regra
  3. Todos os perfis OFF (`netsh show allprofiles`) → pula
  4. Método primário: PowerShell `New-NetFirewallRule -ExecutionPolicy Bypass`
  5. Fallback: `netsh profile=any`
  - Desinstalação: `Remove-NetFirewallRule` + `netsh delete` como dupla garantia
  - Logs em `C:\Invec\logs\firewall.log` com seções por etapa
- **Sequência de instalação corrigida** (4 bugs):
  1. Para o serviço antes de copiar arquivos (evita `PermissionError` em updates)
  2. Verifica porta após parar o serviço (não bloqueia update onde o próprio serviço usava a porta)
  3. Exclui `InvecServidor.exe` do Windows Defender antes de copiar
  4. Dialog "Instalação concluída" só aparece após ping bem-sucedido
  5. Timeout de ping: 12 s → 20 s

#### Documentação

- **`docs/BANCO_TABELAS.md`** (novo): referência completa de todas as tabelas e colunas criadas pelo Invec no Firebird.

---

## [1.3.1] — 2026-06-24

### Correções de bugs

#### Backend — `app/routers/inventario.py`

- **Bug crítico: estoque zero ignorado em `/consolidar`** — `qtdeatual_snap = 0.0` era tratado como `None` pelo operador `or` do Python (`float(0.0) or x` avalia para `x`). Produtos com estoque zero no sistema no momento do scan usavam o estoque atual de `MOVIMENTO` como baseline, gerando `QTENTRADA`/`QTSAIDA` incorretos no `MOV_PRODUTO`. Corrigido para `float(snap) if snap is not None else float(movimento_qtde.get(...))` — afeta linhas do loop de divergências e do loop de consolidação.

#### Instalador — `instalador.py` + `instalar.bat`

- **Firewall configurado após o serviço iniciar**: o Windows cria automaticamente uma regra Domain+Private quando o executável ouve a porta pela primeira vez. A regra do instalador precisa ser aplicada depois para sobrescrever essa regra automática e garantir o perfil Public. Movida a etapa de firewall para depois do `nssm start`.
- **Caminho absoluto do `netsh.exe`**: usa `os.path.join(SystemRoot, "System32", "netsh.exe")` para evitar falhas em ambientes com PATH restrito.
- **Log de firewall**: saída do `netsh` é gravada em `C:\Invec\logs\firewall.log` para diagnóstico — inclui delete, add e show da regra.
- **`instalar.bat`**: `profile=any` → `profile=domain,private,public` (equivalente explícito, mais legível).

#### Documentação

- **`README.md`**: corrigido nome da tabela `LOTES_PROCESSADOS` → `LOTES_SYNC_PROCESSADOS`; adicionada `SCANS_PROCESSADOS` na lista de tabelas criadas pelo Invec.
- **`.gitignore`**: `Instalar-Invec.spec` excluído (spec auto-gerado pelo `pyi-makespec`, inferior ao `instalador.spec` manual).

---

## [1.3.0] — 2026-06-23

### Segurança, integridade offline e correções do instalador

#### Segurança — Backend

- **CRÍTICO — fail-open corrigido em `_verificar_acesso_deposito`**: qualquer exceção de banco abria acesso; agora só ignora erros de tabela inexistente, demais erros negam acesso
- **CRÍTICO — rate limiting em `POST /supervisor/pre-auth`**: adicionado mesmo esquema do login (5 tentativas/60s, bloqueio 5 min)
- **`DELETE LOGIN_FALHOU` preserva histórico de ataques**: apaga apenas registros dentro da janela de bloqueio, mantendo evidências de ataques anteriores
- **Aviso de senha padrão no startup**: se `FB_PASSWORD` não estiver configurado no `.env`, exibe aviso visível

#### Integridade Offline

- **`SCANS_PROCESSADOS`**: deduplicação por `scan_id` — evita duplicata quando scan online sofre timeout e é reenviado via lote
- **`LOTES_SYNC_PROCESSADOS`**: deduplicação de lotes de sync offline por `lote_id`
- **Reseta sessões presas**: sessões com `STATUS='CONSOLIDANDO'` voltam para `'ABERTA'` no startup
- **Limpeza de idempotência**: registros com mais de 90 dias em `SCANS_PROCESSADOS` e `LOTES_SYNC_PROCESSADOS` removidos no startup
- **`/bipagem/lote` rejeita sessões encerradas**: retorna 409 se `ENCERRADA` ou `CONSOLIDADA`
- **`/bipagem` idempotente por `scan_id`**: não duplica se scan_id já processado
- **Ordenação de migrations corrigida**: índices criados depois das tabelas

#### Instalador

- **Firewall `profile=any`** para todos os perfis de rede
- **`_test_firebird` corrigido**: usava `firebirdsql` (errado); corrigido para `firebird.driver`
- **`_test_porta`**: verifica se porta já está em uso antes de registrar o serviço
- **`instalador.spec`**: `hiddenimports` para `firebird.driver` e `firebird.driver.core`

---

## [1.2.0] — 2026-06-22

### Modo offline-first

- Nova tabela `INVENTARIO_SESSAO`
- Nova tabela `LOTES_PROCESSADOS` (renomeada para `LOTES_SYNC_PROCESSADOS` em v1.3.0)
- `POST /inventario/bipagem/lote`: sync de bipagens offline
- `POST /sessao/iniciar`: cria/retorna sessão (idempotente)
- `GET /ping`: health check sem autenticação

---

## [1.1.0] — 2026-06-19

### Segurança, performance e licença RSA

- Rate limiting no login (5 falhas/60s → bloqueio 300s)
- Race condition no scan corrigida (UPDATE atômico RETURNING)
- Lock de consolidação (`threading.Lock`)
- Limiar de recontagem (30% divergência + mínimo 5 itens)
- Relatório de consolidação em arquivo `.txt`
- Sistema de licença RSA 2048-bit (`licenca.py` + `gerar_licenca.py`)
- Histórico migrado para `MOV_PRODUTO WHERE SIST_ALT='INV_APP'`
- Estoque corrigido: migrado de `MOV_INVENTARIO` para `MOVIMENTO`

---

## [1.0.1] — 2026-06-18

### Correções de segurança e log

- `_registrar_log` usa conexão separada — falha no log não cancela operação principal
- Logs gravados após commit
- BIPAGEM removida do log automático (volume inviável em lojas grandes)
- Limpeza automática: BIPAGEM com mais de 90 dias apagada no startup

---

## [1.0.0] — 2026-06-18

Release inicial com nome definitivo **Invec**.
