# CHANGELOG — Invec

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
