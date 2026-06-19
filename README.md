# Invec — App Android de Inventário

Aplicativo Android para contagem de estoque integrado ao sistema Automec (Firebird). Desenvolvido pela **Pontual Tecnologia**.

---

## Stack

| Componente | Tecnologia |
|---|---|
| Linguagem | Kotlin |
| Min SDK | Android 8.0 (API 26) |
| Target SDK | Android 14 (API 34) |
| UI | ViewBinding + Material Design 3 |
| Leitura de câmera | CameraX + ML Kit Barcode Scanning |
| HTTP | Retrofit2 + OkHttp3 |
| Serialização | Gson |
| Coroutines | kotlinx.coroutines |

---

## Funcionalidades

- Login com autenticação JWT (sessão de 8h)
- Timeout de inatividade de 15 minutos (logout automático)
- Leitura de código de barras por câmera ou leitor Bluetooth
- Registro de bipagem com atualização atômica no servidor
- Alerta de quantidade suspeita (mais de 2× o estoque do sistema)
- Relatório da sessão com diferença sistema/contado em tempo real
- Edição e exclusão de bipagem com auditoria obrigatória (motivo)
- Recontagem (2ª contagem) com comparação das duas contagens
- Consolidação com aprovação de supervisor quando há divergências
- Histórico de consolidações por depósito
- Log de auditoria (visível para gerentes/admins)
- Gestão de operadores de coleta (gerentes/admins)
- Gestão de usuários mobile com senha separada (admin mobile)

---

## Estrutura do projeto

```
app/src/main/java/br/com/inventario/
├── data/
│   ├── api/
│   │   ├── ApiService.kt          # Endpoints Retrofit
│   │   └── RetrofitClient.kt      # OkHttp + interceptor 401
│   └── model/
│       └── Models.kt              # Data classes (request/response)
├── ui/
│   ├── base/
│   │   └── TimeoutActivity.kt     # Base com timeout de inatividade 15min
│   ├── login/
│   │   └── LoginActivity.kt
│   ├── main/
│   │   └── MainActivity.kt        # Seleção de depósito e operador
│   ├── scanner/
│   │   ├── ScannerActivity.kt     # Bipagem (câmera + Bluetooth)
│   │   └── ScannedItemsAdapter.kt
│   ├── relatorio/
│   │   ├── RelatorioActivity.kt   # Relatório, edição, consolidação
│   │   └── RelatorioAdapter.kt
│   ├── recontagem/
│   │   └── RecontagemActivity.kt  # Segunda contagem com câmera/BT
│   ├── historico/
│   │   └── HistoricoActivity.kt
│   ├── auditoria/
│   │   └── AuditoriaActivity.kt
│   ├── operadores/
│   │   └── OperadoresActivity.kt
│   └── usuarios/
│       └── UsuariosActivity.kt
└── util/
    └── SessionManager.kt          # SharedPreferences — token, depósito, etc.
```

---

## Fluxo de uso

```
Login → Selecionar Depósito → Selecionar Operador
    ↓
Scanner (bipa produtos)
    ↓
Relatório (revisa contagens)
    ↓
Recontagem (opcional — se há divergências)
    ↓
Consolidação (grava no Automec)
```

---

## Segurança

- Token JWT armazenado em `SharedPreferences` (não exportável)
- Interceptor OkHttp detecta 401 e redireciona para login automaticamente
- Timeout de 15 minutos de inatividade em todas as telas pós-login
- `device_id` único por instalação gravado em todos os eventos de auditoria
- Senha do supervisor digitada no momento da consolidação (nunca armazenada)

---

## Build

```bash
# Debug
./gradlew assembleDebug

# Release
./gradlew assembleRelease
# APK em: app/build/outputs/apk/release/app-release.apk
```

---

## Configuração do servidor no app

Na tela de login, campo **"URL do servidor"**:
```
http://192.168.1.31:8000/
```

O IP deve ser o IP local do computador onde o `InvecServidor.exe` está instalado.

Veja [docs/MANUAL_USO.md](docs/MANUAL_USO.md) para o guia de uso completo.
