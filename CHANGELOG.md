# CHANGELOG — Invec

## [1.5.0] — 2026-06-28

### Novas funcionalidades

#### Considerar Entrega — modo de contagem configurável

- **Diálogo ao selecionar depósito**: ao iniciar uma sessão de inventário, o app pergunta se a contagem inclui materiais separados para entrega ("Sim — contar tudo" / "Não — só disponíveis"). A escolha fica salva em `SessionManager` para toda a sessão.
- **Relatório ajustado**: quando "Sim", o campo **Sistema** já soma `MOVIMENTO.QTDEATUAL + QTDEENTREGA` e exibe `(+X.XX entrega)` ao lado do valor. Quando "Não", mostra apenas o disponível.
- **Consolidação correta**: o flag é enviado ao servidor no momento de consolidar, garantindo que a quantidade gravada no Automec reflita o modo escolhido.
- **Fonte dos itens de entrega**: tabela `SAIDAPRODUTO JOIN SAIDAESTOQUE` onde `IDENTREGA NOT IN (0, 9999)`, excluindo pedidos cancelados/entregues — mesma lógica do Delphi (`ChkCalculoEntrega`).

#### Android
- `MainActivity`: diálogo de modo de contagem após seleção do depósito
- `SessionManager`: `saveConsiderarEntrega()` / `getConsiderarEntrega()`
- `ApiService`: parâmetro `considerar_entrega` em `relatorio()`
- `RelatorioAdapter`: exibe `(+X.XX entrega)` quando aplicável
- `RelatorioActivity`: passa flag para relatório e consolidação
- `Models.kt`: `ItemRelatorio.qtde_entrega`; `ConsolidarRequest.considerarEntrega`

#### Backend
- `schemas.py`: `ItemRelatorio.qtde_entrega`; `ConsolidarRequest.considerar_entrega`
- `inventario.py`: query SAIDAPRODUTO condicional no relatório e na consolidação; diferença calculada em Python (não mais em SQL)

---

### Correções de bugs

- **Params SQL do relatório**: após remover a coluna `DIFERENCA` do SQL (agora calculada em Python), o tuple `params` ainda tinha um `cddeposito` extra do subquery removido. Corrigido de `(dep, dep, dep, session)` para `(dep, dep, session)`.

---

## [1.4.0] — 2026-06-28

### Correções de bugs

#### Android — Scanner automático congela após ~20 bipagens

- **Causa raiz**: `BarcodeScanning.getClient()` era chamado a cada frame da câmera enquanto `aguardandoScan=true` (~30 fps). Após ~20 bipagens, centenas de instâncias ML Kit acumuladas sem fechar saturavam o pipeline interno e congelavam a leitura.
- **Fix**: instância `barcodeScanner` criada uma única vez como campo da `ScannerActivity` e fechada em `onDestroy()`, conforme documentação do ML Kit ("reuse the scanner, don't create a new one for each input").

---

## [1.3.3] — 2026-06-28

### Novas funcionalidades

#### Android — Scanner

- **Botão shutter em modo unitário**: botão grande centralizado na tela do scanner para disparar leitura manualmente. Modo múltiplo exibe instrução automática no lugar do botão.
- Arquivo novo: `res/drawable/ic_scan_shutter.xml`; campo novo em `activity_scanner.xml`

#### Android — Relatório

- **Código interno visível**: campo `Cód. Int.` exibe `CDPRODUTO` ao lado do código de barras em cada item do relatório.
- **Motivo obrigatório na edição** (fix definitivo): dialog de edição de quantidade não fecha com campo de motivo vazio — `setPositiveButton` sobrescrito após `show()` para validar antes de fechar.
- **Recontagem 100% opcional**: supervisor não é mais exigido para consolidar quando não há divergências.
- **Supervisor obrigatório com divergências sem recontagem**: ao consolidar com itens em divergência sem ter feito recontagem, o app exige justificativa mínima de 10 caracteres, que é gravada na auditoria.

#### Android — Recontagem

- **1ª contagem oculta durante escaneamento**: painel lateral e lista ocultam a 1ª contagem enquanto a recontagem está em andamento; resultado final exibe apenas a 2ª contagem com ✓/✗.
- **Botão −1 por item**: permite corrigir scan duplicado sem reiniciar a recontagem do produto.

#### Android — Auditoria

- **Novo evento `CONSOLID_SEM_RECONTAGEM`**: exibido em roxo na tela de auditoria com a justificativa informada pelo supervisor.

#### Backend

- `ConsolidarRequest`: campo `justificativa_sem_recontagem`
- `inventario.py`: grava `LOG_INVENTARIO` tipo `CONSOLID_SEM_RECONTAGEM` quando supervisor autoriza consolidação sem recontagem

---

### Correções de bugs

- **Scanner — re-arm em modo múltiplo**: leitura parava após chamada de rede lenta porque `resetarEstado()` rearmava o scanner antes de `processando = false`. Corrigido: re-arm movido para após `processando = false`.
- **Compilação**: chamada `pedirSupervisor()` sem argumento em `RelatorioActivity` corrigida.

---

## [1.3.2] — 2026-06-25

### Novas funcionalidades

#### Android — Flash da câmera

- **Flash no scanner e na recontagem**: botão raio (ícone Material Design) na toolbar do `ScannerActivity` e `RecontagemActivity`. Toque alterna a lanterna da câmera traseira. Implementado via `camera.cameraControl.enableTorch(ligado)` do CameraX. Estado não persiste entre sessões.
- Arquivos novos: `res/drawable/ic_flash_on.xml`, `res/menu/menu_scanner.xml`

#### Android — Modo escuro

- **Switch na tela inicial** (`MainActivity`): usuário alterna entre tema claro e escuro sem sair do app
- Preferência salva em `SessionManager` (`dark_mode: Boolean`)
- `InvecApp.kt` aplica o modo no startup via `AppCompatDelegate.setDefaultNightMode()`
- `res/values-night/colors.xml`: variante de cores para o tema escuro (fundo de card `#1E1E1E`, texto `#E0E0E0`)
- Arquivos novos: `InvecApp.kt`, `res/values-night/colors.xml`, `res/drawable/ic_sync.xml`

---

### Correções de bugs

#### Android — Modo offline

- **Scan offline instantâneo**: scanner registra a bipagem no Room imediatamente; a requisição ao servidor vai em background. Antes, o app aguardava a resposta do servidor, travando a tela se não houvesse rede.
- **Edição de quantidade offline** (`RelatorioActivity`): editar a quantidade de um item funciona sem conexão.
- **Crash offline corrigido**: tratamento de exceção ao tentar bipar sem conexão.
- **Scanner offline desbloqueia** sem depender da flag `completo` do catálogo: o scanner já opera se o catálogo tem produtos locais, independente de o download ter sido marcado como concluído.
- **ServerMonitor**: ping de `GET /ping` reduzido de 30 s para 8 s — reconexão detectada mais rapidamente.

#### Android — Modo escuro — textos invisíveis

- `tvProduto` em `item_relatorio.xml`, `item_auditoria.xml` e `item_recontagem.xml` usava `textColor=#212121` fixo. Em fundos escuros (`#1E1E1E`) o texto ficava invisível. Corrigido para `@color/colorPrimaryText` que tem variante night `#E0E0E0`.

#### Backend — `app/routers/inventario.py`

- **Bug crítico — PK_INVENTARIO_TEMP bloqueava toda bipagem**: o `UPDATE` filtrava por `SESSION_ID` no `WHERE`, resultando em `rowcount=0` quando já existia linha para `(CDPRODUTO, CDDEPOSITO)` de sessão anterior ou inserida pelo Automec. O `INSERT` subsequente falhava com violação de `PRIMARY KEY`. Fix: `WHERE` usa apenas `(CDPRODUTO, CDDEPOSITO)`; `SESSION_ID`, `QTDEATUAL_SNAP` e `ORIGEM` são atualizados no `SET`.
- **Bipagem em linha do Automec acumulava em vez de substituir**: quando `INVENTARIO_TEMP` já tinha linha do Automec (ou de sessão anterior), o `UPDATE` fazia `QTDE + scan_qty`, somando sobre a contagem antiga. Nova lógica em 3 passos: ① `UPDATE` filtrando `SESSION_ID` — acumula na linha da sessão atual; ② se `rowcount=0`: `UPDATE` sem filtro de sessão, `SET QTDE = scan_qty` — assume a linha existente e **substitui** a quantidade; ③ se ainda `rowcount=0`: `INSERT`.
- **Lote aceita delta negativo**: `net_qtde <= 0` substituído por `net_qtde == 0` para não descartar edições offline com resultado negativo.

#### Backend — `app/routers/produtos.py`

- **EAN-13 vs UPC-A — zeros iniciais**: o scanner pode retornar 12 dígitos (UPC-A) enquanto o ERP gravou 13 (EAN-13) com zero à esquerda, ou vice-versa. A nova função `_barcode_variants()` gera ambas as formas e a query usa `IN()` para encontrar qualquer uma — resolve produto não encontrado na busca por código de barras.

#### Instalador — `instalador.py`

- **Firewall 100% automático** — 5 cenários tratados:
  1. `MpsSvc` ausente (Windows Firewall desativado) → pula, porta já acessível
  2. `MpsSvc` parado → inicia via `sc start` antes de adicionar regra
  3. Todos os perfis OFF (`netsh show allprofiles`) → pula
  4. Método primário: PowerShell `New-NetFirewallRule -ExecutionPolicy Bypass`
  5. Fallback: `netsh profile=any` se PowerShell falhar
  - Desinstalação: `Remove-NetFirewallRule` (PS) + `netsh delete` como dupla garantia
  - Logs unificados em `C:\Invec\logs\firewall.log` com seções por etapa
- **Sequência de instalação corrigida** (4 bugs):
  1. Para o serviço **antes** de copiar arquivos — evita `PermissionError` em atualizações
  2. Verifica porta **após** parar o serviço — não bloqueia atualização quando o próprio serviço estava usando a porta
  3. Adiciona exclusão no Windows Defender antes de copiar `InvecServidor.exe` — evita detecção como ameaça durante a cópia
  4. Dialog "Instalação concluída" só aparece quando o servidor respondeu com sucesso
  5. Timeout do ping aumentado de 12 s para 20 s — suporta máquinas lentas e migrations grandes

#### Documentação

- **`docs/BANCO_TABELAS.md`** (novo): lista completa de todas as tabelas e colunas criadas pelo Invec no banco Firebird do Automec, com tipo de dado, propósito e observações de cada campo.

---

### Arquivos criados / modificados

**Android:**
- `InvecApp.kt` — Application class; aplica modo escuro no startup
- `res/drawable/ic_flash_on.xml` — ícone de flash (raio)
- `res/drawable/ic_sync.xml` — ícone de sincronização
- `res/menu/menu_scanner.xml` — menu toolbar do scanner (flash)
- `res/values-night/colors.xml` — paleta de cores do modo escuro
- `res/layout/item_relatorio.xml` — textColor corrigido
- `res/layout/item_auditoria.xml` — textColor corrigido
- `res/layout/item_recontagem.xml` — textColor corrigido
- `res/layout/activity_recontagem.xml` — botão flash adicionado
- `res/layout/activity_main.xml` — switch modo escuro
- `ui/scanner/ScannerActivity.kt` — flash, offline instantâneo, modo câmera
- `ui/relatorio/RelatorioActivity.kt` — edição offline, ic_sync
- `ui/recontagem/RecontagemActivity.kt` — flash, crash offline
- `util/SessionManager.kt` — `dark_mode` preference
- `util/ServerMonitor.kt` — ping 30 s → 8 s
- `AndroidManifest.xml` — `android:name=".InvecApp"`

**Backend:**
- `app/routers/inventario.py` — fix PK_INVENTARIO_TEMP, lógica 3 passos de bipagem, lote delta negativo
- `app/routers/produtos.py` — EAN-13/UPC-A variants

**Instalador:**
- `instalador.py` — firewall automático completo, sequência de instalação corrigida

**Documentação:**
- `docs/BANCO_TABELAS.md` — novo documento de referência do banco

---

## [1.3.1] — 2026-06-24

### Correções de bugs

#### Backend — `api/app/routers/inventario.py`

- **Bug crítico: estoque zero ignorado em `/consolidar`** — `qtdeatual_snap = 0.0` era tratado como `None` pelo operador `or` do Python. Produtos com estoque zero no sistema no momento do scan usavam o estoque atual como baseline, gerando movimentações incorretas no `MOV_PRODUTO`. Corrigido com `float(snap) if snap is not None else float(movimento_qtde.get(...))`.
- **Sincronizado com `inventario-api` v1.3.1**: inclui correções de segurança de MI bypass em `_verificar_acesso_deposito`, auto-criação de sessão em `/bipagem`, e rate limiting em supervisor.

#### Android — `ScannerActivity.kt`

- **Contador consistente**: label do contador mudou de `"X bipagens"` para `"X un. contadas"` — o valor representa total de unidades na sessão, não eventos de scan; agora consistente entre scan e retorno de outra tela.
- **Erro 404 na edição com sync pendente**: quando a edição falha com 404 e há itens ainda não sincronizados no Room, exibe `"Itens pendentes de sync. Aguarde e tente novamente."` em vez do genérico `"Item não encontrado na contagem"`.

#### Android — `RelatorioActivity.kt`

- **Erro HTTP com detalhe real**: ao falhar carregamento ou remoção de item, o erro exibido agora inclui o `detail` da resposta JSON do servidor em vez de mensagem genérica.

#### Android — `SyncManager.kt`

- **409 encerra acumulação de lixo**: lote rejeitado com 409 (sessão já consolidada) agora marca todos os itens da sessão como sincronizados no Room, evitando tentativas infinitas de re-envio.

#### Outros

- **`.gitignore`**: `*.hprof` adicionado (exclui heap dumps do Java/Android)
- **APK renomeado**: `invec-app.apk` → `app-release.apk` (nome padrão do Gradle)

---

## [1.3.0] — 2026-06-23

### Segurança, integridade offline e correções do instalador

---

#### Segurança — Backend

**`app/routers/inventario.py`**
- **CRÍTICO — fail-open corrigido em `_verificar_acesso_deposito`**: qualquer exceção de banco abria acesso ao depósito; agora só ignora erros de tabela inexistente (migration pendente), demais erros negam acesso
- **CRÍTICO — rate limiting em `POST /supervisor/pre-auth`**: endpoint de pré-autenticação do supervisor não tinha proteção contra brute force; adicionado mesmo esquema do login (5 tentativas/60s, bloqueio 5 min) via `_sup_tentativas/_sup_bloqueados`

**`app/routers/auth.py`**
- **`DELETE LOGIN_FALHOU` preserva histórico de ataques**: ao logar com sucesso, apagava TODOS os registros de falha do usuário; agora apaga apenas os da janela de bloqueio (`_DB_JANELA_MINUTOS`), mantendo evidências de ataques anteriores

**`app/database.py`**
- **Aviso de senha padrão no startup**: se `FB_PASSWORD` não estiver configurado no `.env`, exibe aviso visível no log em vez de falhar silenciosamente com `masterkey`

---

#### Integridade Offline — Backend

**`app/migrations.py`**
- **Nova tabela `SCANS_PROCESSADOS`**: deduplicação de scans individuais por `scan_id` (UUID) — evita duplicata quando scan online sofre timeout de rede e é reenviado
- **Nova tabela `LOTES_SYNC_PROCESSADOS`**: deduplicação de lotes de sync offline por `lote_id`
- **`_reset_sessoes_consolidando()`**: reseta sessões com `STATUS='CONSOLIDANDO'` para `'ABERTA'` no startup — evita travamento permanente após restart do servidor durante consolidação
- **`_limpar_idempotencia_antiga()`**: remove registros de `SCANS_PROCESSADOS` e `LOTES_SYNC_PROCESSADOS` com mais de 90 dias — evita crescimento indefinido das tabelas
- **Ordenação corrigida em `run_migrations()`**: `_migrar_lotes_processados` e `_migrar_usuario_deposito` chamados antes de `_migrar_indices_log` — corrige falha em instalação nova onde índices eram criados antes das tabelas existirem

**`app/routers/inventario.py`**
- **`POST /bipagem/lote` rejeita sessões encerradas**: verifica `STATUS` da sessão antes de processar — retorna 409 se `ENCERRADA` ou `CONSOLIDADA`; previne inserção de dados em `INVENTARIO_TEMP` que nunca seriam consolidados
- **`registrar_bipagem`: idempotente por `scan_id`**: retorna quantidade atual sem inserir se `scan_id` já foi processado
- **`sincronizar_lote`: desconta `scan_ids` já processados** antes de somar `QTDE` — evita duplicação em sincronização offline

**`app/models/schemas.py`**
- `BipagemRequest`: campo `scan_id: Optional[str]` adicionado
- `BipagemLoteItem`: campo `scan_ids: Optional[List[str]]` adicionado

---

#### Integridade Offline — Android

**`data/db/InvecDatabase.kt`** — versão 3
- Coluna `scan_id TEXT NOT NULL DEFAULT ''` adicionada em `bipagens_pendentes`
- `onUpgrade`: `ALTER TABLE bipagens_pendentes ADD COLUMN scan_id`
- `BipagPendente.scanId: String = ""` — UUID gerado em `ScannerActivity` antes do insert
- `atualizarQtdeProduto`: **DELETE substitui UPDATE** — fix de bug onde scans antigos ficavam marcados como sincronizados sem ser deletados, fazendo `getRelatorioOffline` somar valores duplicados (BUG-5)

**`util/SyncManager.kt`**
- Coleta `scan_ids` por produto ao montar lote para envio

**`ui/scanner/ScannerActivity.kt`**
- `registrarBipagem`: try-catch com `resetarEstado()` no catch — scanner não trava mais se Room falhar durante insert
- UUID de `scan_id` gerado antes do insert em Room

**`ui/MainActivity.kt`** + **`ui/TimeoutActivity.kt`**
- `deleteAllDaSessao(sessionId)` chamado antes de `session.logout()` em todos os paths (online, offline e timeout) — elimina dados fantasmas no sync pós-logout

**`ui/recontagem/RecontagemActivity.kt`**
- `carregarItens()`: variável `erroHttp` — erros 4xx/5xx do servidor não causam mais fallback silencioso para cache local; exibe toast de erro

---

#### Instalador — `instalador.py` + `instalador.spec`

- **Firewall `profile=any`**: regra criada para todos os perfis de rede (Privado, Domínio e Público) — corrige falha de conectividade em máquinas com rede classificada como Pública pelo Windows
- **`_test_firebird` corrigido**: usava `firebirdsql` (driver errado) causando `ImportError` silencioso e pulando validação em 100% das instalações; corrigido para `firebird.driver`
- **`_test_porta`**: verifica se a porta já está em uso antes de registrar o serviço; exibe erro claro em vez de instalar e falhar silenciosamente
- **`instalador.spec`**: `hiddenimports` para `firebird.driver` e `firebird.driver.core`

---

#### Arquivos criados / modificados

**Backend:**
- `app/migrations.py` — tabelas `SCANS_PROCESSADOS`, `LOTES_SYNC_PROCESSADOS`; `_reset_sessoes_consolidando`; `_limpar_idempotencia_antiga`; ordenação de migrations corrigida
- `app/routers/inventario.py` — idempotência scan_id/lote_id; rejeição de sessões encerradas; rate limit supervisor; fail-open corrigido
- `app/routers/auth.py` — DELETE LOGIN_FALHOU preserva histórico
- `app/database.py` — aviso FB_PASSWORD padrão
- `app/models/schemas.py` — campos scan_id e scan_ids

**Android:**
- `data/db/InvecDatabase.kt` — v3 com scan_id; fix BUG-5 DELETE→UPDATE
- `util/SyncManager.kt` — coleta scan_ids por produto
- `ui/scanner/ScannerActivity.kt` — try-catch Room + geração de scan_id
- `ui/MainActivity.kt` — deleteAllDaSessao no logout
- `ui/TimeoutActivity.kt` — deleteAllDaSessao no timeout
- `ui/recontagem/RecontagemActivity.kt` — erroHttp fallback

**Instalador:**
- `instalador.py` — profile=any; _test_firebird; _test_porta
- `instalador.spec` — hiddenimports firebird.driver

---

## [1.2.0] — 2026-06-22

### Modo offline-first + correções de bugs

---

#### Arquitetura — Modo Offline-First

O app agora funciona sem conexão contínua com o servidor.

**Backend — `app/migrations.py`**
- Nova tabela `INVENTARIO_SESSAO`: registra cada sessão de coleta por dispositivo (`SESSION_ID UUID`, `CDDEPOSITO`, `OPERADOR`, `USUARIO`, `STATUS`, `INICIO`, `FIM`)
- Nova tabela `LOTES_PROCESSADOS`: garante idempotência — lote de bipagens já processado não duplica dados mesmo se sincronizado duas vezes

**Backend — `app/routers/inventario.py`**
- `POST /inventario/bipagem/lote`: recebe um lote de bipagens acumuladas offline por SESSION_ID; atômico, idempotente via LOTES_PROCESSADOS; detecta alertas de quantidade; registra LOG_INVENTARIO
- `POST /sessao/iniciar`: cria ou retorna sessão existente em INVENTARIO_SESSAO (idempotente)
- `GET /ping`: endpoint sem autenticação; retorna `{"status":"ok"}` — usado pelo ServerMonitor Android

**Android — `util/ServerMonitor.kt`** (novo singleton)
- Pinga `/ping` a cada 30 segundos em coroutine
- Expõe `StateFlow<Boolean> isOnline` — observado por todas as Activities
- `startOrKeep()` garante apenas um loop de ping ativo

**Android — `util/SyncManager.kt`** (novo object singleton)
- Observa `ServerMonitor.isOnline` e dispara sincronização na transição offline→online
- Retry automático a cada 60 segundos enquanto online
- Mutex (`withLock`) garante apenas uma sincronização por vez e serializa com carregamento do relatório
- Agrupa bipagens por SESSION_ID e cdproduto antes de enviar (reduz requisições)

**Android — `data/db/InvecDatabase.kt`** + DAOs (Room)
- `bipagens_pendentes`: armazena cada scan antes de confirmar com o servidor
- `produtos_cache`: cache local do catálogo de produtos para busca offline
- `BipagPendenteDao`: `getNaoSincronizados`, `marcarSincronizados`, `getQtdeSistema`, `deleteAllDaSessao`
- `ProdutoCacheDao`: `upsert`, `getByBarcode`, `buscarPorNome`

**Android — `util/SessionManager.kt`** — campos adicionados
- `session_id`: UUID gerado ao entrar no depósito, identifica a sessão no servidor
- `consolidar_bloqueado_{dep}`: flag persistida quando há divergências pendentes
- `getSessionId()`, `encerrarSession()`, `isConsolidarBloqueado()`, `setConsolidarBloqueado()`

**Android — `ui/relatorio/RelatorioActivity.kt`**
- Offline: constrói relatório a partir do Room (bipagens pendentes) sem chamar o servidor
- Online: sincroniza pendentes via `SyncManager.sincronizarPendentes()` antes de carregar relatório
- Chip Online/Offline muda dinamicamente via `ServerMonitor.isOnline.collect`
- `btnSincronizar` visível quando há pendentes não sincronizados offline
- Consolidar desabilitado quando offline

**Android — `ui/scanner/ScannerActivity.kt`**
- Scan offline: registra em Room imediatamente; POST ao servidor em background se online
- Snapshot `QTDEATUAL_SNAP` gravado no 1º scan de cada produto → relatório e consolidação usam o valor do momento do scan, não o estoque atual (correto para lojas em movimento)

---

#### Layout — Relatório Redesenhado

**Android — `res/layout/activity_relatorio.xml`** (reescrita)
- **Barra de resumo** no topo: pill Online/Offline + contador de itens + ProgressBar
- **Dica de swipe** visível apenas quando há itens
- **RecyclerView** ocupa todo o espaço disponível
- **Card de ações** na base com elevação: Histórico|Auditoria → btnSincronizar → Recontagem → aviso acima do Consolidar → Consolidar
- Avisos organizados por contexto: "sem conexão" em cinza, "bloqueado" em laranja, "pendentes" em vermelho

**Android — `res/drawable/bg_pill.xml`** (novo)
- Fundo arredondado do chip Online/Offline; cor alterada dinamicamente em código

---

#### Correções de Bugs

**Bug: Produtos sumiam ao voltar online**
- Causa: `SyncManager.sincronizarPendentes()` usava `tryLock()` — quando `observarESync` já tinha o mutex, o carregamento do relatório pulava a sincronização e mostrava lista vazia
- Fix: substituído por `mutex.withLock {}` — carregamento aguarda a sincronização terminar em vez de pular

**Bug: Histórico sem horário**
- Causa: `DTMOVIMENTO` em `MOV_PRODUTO` é tipo `DATE` (sem hora)
- Fix: subquery correlacionada em `LOG_INVENTARIO` com `MOTIVO CONTAINING 'inv#{idinventario}'` recupera o TIMESTAMP exato da consolidação; fallback para `CAST(DTMOVIMENTO AS TIMESTAMP)` se não encontrar

**Bug: Consolidar travado em sessões antigas (BANCO-1)**
- Causa: sessões criadas antes de `STATUS` existir têm `STATUS IS NULL` — a query de lock exigia `STATUS = 'ABERTA'`
- Fix: condição ampliada para `STATUS = 'ABERTA' OR STATUS IS NULL`

**Bug: Falso bloqueio de login após reinicialização**
- Causa: registros `LOGIN_FALHOU` em `LOG_INVENTARIO` acumulavam de sessões anteriores
- Fix: ao fazer login com sucesso, deleta todos os `LOGIN_FALHOU` do usuário no banco

**Bug: Horário não aparecia no log de auditoria**
- Causa: em servidores com `LOG_INVENTARIO` criado por versão anterior, coluna `DATA_HORA` era `DATE` em vez de `TIMESTAMP`
- Fix: migration automática detecta tipo `DATE` (field_type=12 no Firebird) e executa `ALTER TABLE LOG_INVENTARIO ALTER DATA_HORA TYPE TIMESTAMP`

**Bug: Auditoria retornava 403 para gerentes com token antigo**
- Causa: JWTs emitidos antes de `idgrupo` ser incluído no payload resultavam em `idgrupo=None → 3 (operador)`
- Fix: fallback deriva `idgrupo` do campo `role` para tokens sem `idgrupo`

**Bug: Cores de tipo misturavam entre linhas na Auditoria**
- Causa: `tvTipo.background.setTint(cor)` modificava drawable compartilhado entre todos os ViewHolders
- Fix: `tvTipo.background.mutate().setTint(cor)` — instância independente por view

**Bug: Consolidar falhava silenciosamente quando havia edições sem divergências**
- Causa: servidor exige supervisor quando `teve_edicoes=True` mesmo sem divergências, mas o client não detectava isso e chamava `consolidar(null, null)`
- Fix: quando servidor retorna 403 com "Supervisor" na mensagem, o dialog de supervisor abre automaticamente

**Bug: RecontagemActivity não compilava**
- Causa: `withContext` e `Dispatchers` usados sem import
- Fix: adicionados `import kotlinx.coroutines.Dispatchers` e `import kotlinx.coroutines.withContext`

#### Outros
- Gradle: `9.5.0` → `9.5.1` (aviso de versão desatualizada eliminado)

---

#### Arquivos criados / modificados

**Backend:**
- `app/migrations.py` — tabelas `INVENTARIO_SESSAO`, `LOTES_PROCESSADOS`; migration `DATA_HORA TIMESTAMP`
- `app/routers/inventario.py` — `/ping`, `/sessao/iniciar`, `/bipagem/lote`, fix histórico, fix consolidar lock, fix auditoria idgrupo

**Android:**
- `util/ServerMonitor.kt` — novo singleton de conectividade
- `util/SyncManager.kt` — novo object de sincronização offline→online (com `withLock`)
- `data/db/InvecDatabase.kt` — Room database com bipagens_pendentes e produtos_cache
- `res/layout/activity_relatorio.xml` — redesenho completo
- `res/drawable/bg_pill.xml` — drawable do chip Online/Offline
- `ui/relatorio/RelatorioActivity.kt` — modo offline, pill, retry supervisor
- `ui/recontagem/RecontagemActivity.kt` — imports corrigidos
- `ui/auditoria/AuditoriaActivity.kt` — drawable mutate fix
- `gradle/wrapper/gradle-wrapper.properties` — Gradle 9.5.1

---

## [1.1.0] — 2026-06-19

### Segurança, performance e sistema de licença

#### Backend — `app/routers/auth.py`
- **Rate limiting no login**: máximo 5 tentativas por IP em 60 segundos → bloqueio de 5 minutos
- Constantes configuráveis: `MAX_TENTATIVAS=5`, `JANELA_SEGUNDOS=60`, `BLOQUEIO_SEGUNDOS=300`

#### Backend — `app/routers/inventario.py`
- **Correção de race condition no scan**: `INSERT + SELECT` substituído por `UPDATE ... RETURNING QTDE` atômico; se nenhuma linha for atualizada, faz INSERT — elimina duplicação em scans simultâneos do mesmo produto
- **Lock de consolidação**: `threading.Lock()` impede que dois usuários consolidem o mesmo depósito ao mesmo tempo
- **Correção N+1**: loop de 500+ queries na consolidação substituído por único JOIN (`INVENTARIO_TEMP + PRODUTO + MOVIMENTO`)
- **Limiar de recontagem**: divergência acima de 30% com mínimo de 5 itens impede consolidação direta — retorna HTTP 409 exigindo `recontagem_confirmada=true`; constantes `LIMIAR_RECONTAGEM=0.30` e `LIMIAR_RECONTAGEM_MINIMO=5`
- **Relatório de consolidação**: após cada consolidação bem-sucedida, grava `C:\Invec\relatorios\consolidacao_{ts}_dep{id}.txt` com lista de divergências
- **Histórico corrigido**: `GET /historico` consultava `INVENTARIO` (afetada por trigger Automec que sobrescreve `SIST_ALT` para `LOCAL` no UPDATE) — migrado para `MOV_PRODUTO WHERE SIST_ALT='INV_APP' AND TIPOMOVIMENTO=5`

#### Backend — `app/routers/produtos.py`
- **Correção crítica de estoque**: ambos os endpoints consultavam `MOV_INVENTARIO` (tabela vazia no Automec) — migrado para `MOVIMENTO` com `CAST(P.CDPRODUTO AS VARCHAR(10))` no JOIN; `QTDEATUAL` agora retorna valor correto em vez de `null`

#### Backend — `app/security.py`
- **JWT_SECRET seguro**: gera valor aleatório (`secrets.token_hex(32)`) se variável não definida ou com valor padrão — com aviso no log
- `JWT_SECRET` permanente configurado em `C:\Invec\.env`

#### Backend — `app/migrations.py`
- Índices criados automaticamente: `IDX_LOG_INV_DEPOSITO` e `IDX_LOG_INV_DATA` (DESC) na tabela `LOG_INVENTARIO`

#### Backend — Sistema de licença RSA
- **`app/licenca.py`**: módulo de validação com chave pública RSA 2048-bit embutida; verifica assinatura, produto e data de expiração; levanta `RuntimeError` com mensagem clara se inválida
- **`gerar_licenca.py`** (privado, nunca distribuído): script interativo para emitir licenças JWT assinadas com a chave privada; validade em meses ou permanente (Enter = sem data de expiração)
- **`server.py`**: valida licença na inicialização antes de subir o uvicorn; imprime cliente/CNPJ/expiração no log; encerra com `sys.exit(1)` se inválida
- **`servidor.spec`**: adicionados hiddenimports do pacote `cryptography` (necessário para RSA no jose)
- Chave privada: `licenca_privada.pem` — permanece exclusivamente com a Pontual Tecnologia
- `.gitignore`: `licenca_privada.pem` e `gerar_licenca.py` adicionados

#### `.env` (`C:\Invec\.env`)
- Adicionadas variáveis: `JWT_SECRET` e `LICENSE_KEY`

| Variável | Descrição |
|----------|-----------|
| `JWT_SECRET` | Segredo fixo para assinar tokens JWT de sessão |
| `LICENSE_KEY` | Token JWT RS256 emitido pela Pontual Tecnologia |

---

#### Android — `data/api/RetrofitClient.kt`
- **Auto-logout em 401**: interceptor OkHttp detecta resposta 401 quando o usuário está logado e a rota não é `/login` → chama `session.logout()`, reinicia o `RetrofitClient` e abre `LoginActivity` com flag `session_expired=true`
- **HttpLoggingInterceptor**: nível `BODY` apenas em debug; `NONE` em release (evita vazar dados em produção)

#### Android — `ui/login/LoginActivity.kt`
- Exibe Toast "Sessão expirada. Faça login novamente." quando aberta com `session_expired=true`

#### Android — `util/SessionManager.kt`
- `context` alterado de `private val` para `val` para que o interceptor do `RetrofitClient` possa acessar o contexto sem manter referência própria

#### Android — `data/model/Models.kt`
- `ConsolidarRequest`: adicionado campo `recontagem_confirmada: Boolean = false`

#### Android — `ui/relatorio/RelatorioActivity.kt`
- **`ActivityResultLauncher`** para `RecontagemActivity`: ao retornar da recontagem, define `recontagemConfirmada = true` e recarrega o relatório automaticamente
- `consolidar()` passa `recontagemConfirmada` ao backend e exibe mensagem de erro do body JSON em caso de falha
- `recontagemConfirmada` é resetado para `false` após consolidação bem-sucedida

#### Android — Build
- `app/build.gradle.kts`: bloco `kotlinOptions` removido (plugin não declarado neste projeto); R8/ProGuard habilitado para release
- `app/proguard-rules.pro`: regras para preservar data models, Retrofit/Gson, OkHttp, MLKit, CameraX, Coroutines, Material
- `gradle.properties`: `org.gradle.jvmargs=-Xmx4096m` (resolveu `OutOfMemoryError` durante `minifyReleaseWithR8`)

---

### Arquivos novos

**Backend:**
- `app/licenca.py`
- `gerar_licenca.py` (privado)
- `licenca_privada.pem` (privado, não versionado)

**Android:**
- `app/proguard-rules.pro`

---

## [1.0.1] — 2026-06-18

### Correções de segurança e performance no log de auditoria

#### Backend — `app/routers/inventario.py`
- **`_registrar_log` usa conexão separada + `try/except`**: falha no log nunca cancela nem reverte a operação principal
- **Logs gravados após o commit**: todos os `_registrar_log` foram movidos para fora do bloco `with get_connection()`, garantindo que só loga se a operação realmente persistiu no banco
- **BIPAGEM removida do log automático**: para lojas com 50–60 mil produtos, logar cada scan abria 1 conexão Firebird por scan — inviável. Scans suspeitos continuam sendo capturados via ALERTA
- Chip azul "BIPAGEM" removido da `AuditoriaActivity` (tipo não existe mais)

#### Backend — `app/migrations.py`
- **Limpeza automática de BIPAGEM** no startup: registros de BIPAGEM (tipo baixo valor) com mais de 90 dias são apagados automaticamente via `DATEADD(DAY, -90, ...)` do Firebird
- Eventos críticos (EDICAO, EXCLUSAO, CONSOLIDACAO, ALERTA) são preservados para sempre
- Constante `LOG_RETENCAO_BIPAGEM_DIAS = 90` configurável

#### O que é logado na auditoria (estado final)

| Evento | Logado | Motivo |
|--------|--------|--------|
| Scan normal | Não | Volume inviável para grandes lojas |
| Quantidade suspeita (> 2× sistema) | **Sim** — ALERTA | Segurança real |
| Edição manual de quantidade | **Sim** — EDICAO | Risco de fraude |
| Exclusão de item | **Sim** — EXCLUSAO | Risco de fraude |
| Consolidação | **Sim** — CONSOLIDACAO | Evento crítico de fechamento |

---

## [1.0.0] — 2026-06-18

Release inicial do produto com nome definitivo **Invec** (Inventário + Mec, ecossistema Pontual Tecnologia).
Projeto era chamado internamente de "Contador Pontual".

---

### Renomeação

- Nome do app: `Contador Pontual` → `Invec` (`strings.xml`, `app_name`)
- Executável do servidor: `ContadorPontualServidor.exe` → `InvecServidor.exe`
- Instalador: `Instalar-Invec.exe`
- Serviço Windows: `SERVICE_NAME = "InvecAPI"`, `SERVICE_DISPLAY = "Invec - API Inventário"`
- Diretório padrão de instalação: `C:\Invec`
- Histórico no ERP: `"Inventario - Invec"`
- Todos os traços longos (—) removidos das strings da UI

---

### Instalador (`instalador.py` + `instalador.spec`)

- Bundla `nssm.exe` + `InvecServidor.exe` em um único `.exe` — sem dependências externas para o cliente
- Corrigido bug crítico: ao instalar, abria uma segunda janela do instalador
  - Causa: `_copy_server_files()` procurava pelo nome antigo do exe, caia no fallback Python, e chamava `sys.executable` (= o próprio instalador no bundle PyInstaller)
  - Solução: nome correto `InvecServidor.exe` + fallback usa `shutil.which("python")` em vez de `sys.executable`
- Exibe `messagebox` de confirmação após instalação bem-sucedida
- Adicionado botão "Fechar" na barra de botões

---

### Android — UX e Layout

#### MainActivity
- Operador exibido no header (abaixo do depósito) como texto clicável — seleção antes de entrar no scanner
- Botão "Sair da conta" redesenhado: `OutlinedButton` com ícone `ic_logout`, formato pill, centralizado com botão "Servidor"
- Removida margem fixa `56dp` de nav bar (substituída por `fitsSystemWindows`)

#### ScannerActivity + `activity_scanner.xml`
- **Seleção de operador** agora é feita na tela principal — removido auto-popup ao entrar no scanner
- **Operador travado** após o primeiro scan: toque no campo mostra aviso, sem possibilidade de troca até sair da coleta
- **Botão "Escanear"** substituiu leitura contínua: a câmera só processa frame quando o botão é pressionado (flag `aguardandoScan`)
- Timeout de 6 segundos por tentativa de scan — botão volta ao estado normal automaticamente
- **Switch "Múltiplas leituras seguidas"**: quando ligado, rearma o scan automaticamente 800 ms após cada leitura bem-sucedida
- `tvOperador` mostra operador atual com estado (livre / travado)
- Painel inferior fixo com `WindowInsets` para não sobrepor barra de navegação do sistema
- Botão "Digitar código" movido para o painel inferior (estava como ícone pequeno na toolbar)
- Ícone `ic_logout.xml` criado como vector drawable

#### RecontagemActivity + `activity_recontagem.xml`
- Layout totalmente reestruturado: câmera imediatamente abaixo da toolbar (sem "tarja" de status entre elas)
- RecyclerView com `weight=1` no meio
- Painel fixo no rodapé: status + switch + botões + Finalizar (mesma filosofia do scanner)
- **Switch "Múltiplas leituras"** no rodapé (só câmera)
- Botão "Escanear" com mesmo comportamento do scanner (flag `aguardandoScan` + timeout 6s)
- Dialog de resultado customizado (`dialog_resultado_recontagem.xml`): botões com relevo e cores semânticas
  - Aplicar 2ª contagem: verde (`#FF388E3C`)
  - Manter 1ª contagem: outlined
  - Voltar ao Relatório: laranja (`#FFCC5B2A`)
  - Continuar recontando: text button

#### RelatorioActivity + `activity_relatorio.xml`
- Dialog de consolidar customizado (`dialog_consolidar.xml`): botões com relevo e cores semânticas
  - Fazer Recontagem: verde
  - Consolidar agora / Consolidar mesmo assim: laranja
  - Cancelar: text button
- Botões "Histórico" e "Auditoria" lado a lado (antes era só Histórico, texto longo)

#### HistoricoActivity
- Corrigido: `CancellationException` capturada e relançada antes do `catch (Exception)` genérico
  - Bug: ao pressionar Voltar durante carregamento, mostrava Toast "job was cancelled"

---

### Android — Segurança

#### `TimeoutActivity` (nova base class)
- Todas as Activities principais (`Main`, `Scanner`, `Relatorio`, `Recontagem`, `Auditoria`) herdam de `TimeoutActivity` em vez de `AppCompatActivity`
- Sessão encerra automaticamente após **15 minutos de inatividade**
- Redireciona para `LoginActivity` com flag `timeout=true`, que exibe aviso "Sessão encerrada por inatividade"
- Qualquer toque do usuário (`onUserInteraction`) reinicia o contador

#### Operador — controle de fraude
- Seleção de operador na `MainActivity` antes de qualquer coleta
- `selecionarOperador()` no scanner retorna imediatamente se `totalBipagens > 0`
- Texto do operador exibe estado: `"Operador: X (toque para trocar)"` ou `"[travado - saia para trocar]"`

#### Device ID
- `SessionManager.getDeviceId()`: retorna `Settings.Secure.ANDROID_ID`
- Enviado em todos os requests de bipagem, edição e exclusão
- Gravado em `LOG_INVENTARIO.DEVICE_ID`

#### Alerta de quantidade suspeita
- Quando bipagem resulta em total > 2× o estoque do sistema (e estoque > 10 un.), backend retorna `alerta` no `BipagemResponse`
- App exibe `AlertDialog` com aviso imediato após o scan

#### Exclusão com motivo obrigatório
- Dialog de remoção de item (swipe no relatório) agora exige campo de texto "Motivo da exclusão"
- Exclusão não ocorre se motivo vazio; motivo é gravado no log de auditoria

#### Aprovação de supervisor
- Consolidar com divergências exige login + senha de um segundo usuário no backend
- Backend valida contra `USUARIOS` (aceita `SENHAMOBILE` ou `SENHA`)
- Rejeita se supervisor == usuário atual
- Dialog dedicado (`pedirSupervisor()`) com campos login e senha

#### Tela de Auditoria (`AuditoriaActivity`)
- Acessível pelo botão "Auditoria" na tela de Relatório
- Lista todos os eventos do `LOG_INVENTARIO` para o depósito atual
- Tipos com cores: vermelho (EXCLUSAO), laranja (EDICAO), verde (CONSOLIDACAO), amarelo (ALERTA)
- Exibe: tipo, data/hora, produto, operador, usuário, antes/depois, motivo, device_id

---

### Backend (`inventario-api`)

#### Migration — `LOG_INVENTARIO`
- Tabela criada automaticamente na primeira execução via `migrations.py`
- Colunas: `ID`, `TIPO`, `CDDEPOSITO`, `CDPRODUTO`, `PRODUTO`, `OPERADOR`, `LOGIN_USUARIO`, `QTDE_ANTES`, `QTDE_DEPOIS`, `MOTIVO`, `DEVICE_ID`, `DATA_HORA`

#### `schemas.py` — novos campos
- `BipagemRequest`: `+device_id`
- `BipagemResponse`: `+alerta`
- `EditarBipagemRequest`: `+motivo`, `+device_id`
- `ConsolidarRequest`: `+supervisor_login`, `+supervisor_senha`
- Nova schema: `LogItem`

#### `inventario.py` — endpoints atualizados
- `POST /bipagem`: detecta quantidade suspeita (> 2× sistema), registra `LOG_INVENTARIO` tipo `ALERTA`
- `PUT /bipagem/{cdproduto}`: registra `LOG_INVENTARIO` tipo `EDICAO` com valor anterior e motivo
- `DELETE /bipagem/{cdproduto}`: aceita `motivo` e `device_id` via query params; registra `LOG_INVENTARIO` tipo `EXCLUSAO`
- `POST /consolidar`: valida supervisor quando há divergências; registra `LOG_INVENTARIO` tipo `CONSOLIDACAO`
- `GET /inventario/log/{cddeposito}`: retorna até 200 registros de auditoria ordenados por data DESC

#### `SessionManager.kt`
- `logout()` preserva `server_url` (antes apagava tudo, forçando o usuário a reconfigurar o IP)
- `getDeviceId()`: retorna `ANDROID_ID` do dispositivo

---

### Arquivos criados (novos)

**Android:**
- `ui/base/TimeoutActivity.kt`
- `ui/auditoria/AuditoriaActivity.kt`
- `res/layout/activity_auditoria.xml`
- `res/layout/item_auditoria.xml`
- `res/layout/dialog_resultado_recontagem.xml`
- `res/layout/dialog_consolidar.xml`
- `res/drawable/ic_logout.xml`
- `res/drawable/chip_background.xml`

**Backend:**
- Tabela `LOG_INVENTARIO` (via migration automática)

---

### Arquivos modificados (principais)

**Android:**
- `AndroidManifest.xml` — registro de `AuditoriaActivity`
- `data/model/Models.kt` — novos campos e `LogAuditoria`
- `data/api/ApiService.kt` — assinaturas atualizadas + `logAuditoria`
- `util/SessionManager.kt` — `getDeviceId()`, `logout()` preserva URL
- `ui/main/MainActivity.kt` — operador no header, `TimeoutActivity`
- `ui/login/LoginActivity.kt` — aviso de timeout
- `ui/scanner/ScannerActivity.kt` — `TimeoutActivity`, operador travado, device_id, alerta
- `ui/recontagem/RecontagemActivity.kt` — reescrita completa, `TimeoutActivity`
- `ui/relatorio/RelatorioActivity.kt` — `TimeoutActivity`, motivo exclusão, supervisor, auditoria
- `ui/historico/HistoricoActivity.kt` — fix `CancellationException`
- `res/layout/activity_scanner.xml` — switch múltiplas leituras, painel inferior
- `res/layout/activity_recontagem.xml` — reescrita completa
- `res/layout/activity_main.xml` — operador no header, botão sair redesenhado
- `res/layout/activity_relatorio.xml` — botão auditoria
- `res/values/strings.xml` — `app_name = "Invec"`

**Backend (`inventario-api`):**
- `app/migrations.py` — tabela `LOG_INVENTARIO`
- `app/models/schemas.py` — campos novos e `LogItem`
- `app/routers/inventario.py` — auditoria completa, alertas, supervisor
- `app/routers/auth.py` — (sem alteração nesta sessão)
- `instalador.py` — fix double-window, confirmação, botão fechar, renomeação
- `instalador.spec` / `servidor.spec` — nomes dos executáveis atualizados
