# Invec — Sistema de Inventário

Sistema de contagem de estoque integrado ao Automec (Firebird). Desenvolvido pela **Pontual Tecnologia**.

---

## Estrutura do repositório

```
inventario-app/
├── api/              ← Backend FastAPI (Python) — InvecServidor.exe
├── app/              ← App Android (Kotlin)
└── docs/
    ├── INSTALACAO.md ← Guia de instalação do servidor Windows
    └── MANUAL_USO.md ← Manual de uso do app para o usuário final
```

---

## Documentação

- [Guia de Instalação do Servidor](docs/INSTALACAO.md)
- [Manual de Uso do App](docs/MANUAL_USO.md)
- [Documentação Técnica do Backend](api/README.md)

---

## Stack

| Componente | Tecnologia |
|---|---|
| Backend | Python 3.13 + FastAPI + Uvicorn |
| Banco de dados | Firebird 5 (Automec) via `firebird-driver` |
| App mobile | Android (Kotlin) + Retrofit2 + CameraX + ML Kit |
| Autenticação | JWT HS256 (sessão 8h) + rate limiting |
| Licença | RSA 2048-bit (JWT RS256) |
| Distribuição servidor | PyInstaller → `InvecServidor.exe` + NSSM |

---

## Fluxo de uso

```
Login → Selecionar Depósito → Selecionar Operador
    ↓
Scanner (câmera ou Bluetooth — bipa produtos)
    ↓
Relatório (revisa: sistema vs contado vs diferença)
    ↓
Recontagem (opcional — recomendado quando há divergências)
    ↓
Consolidação (grava no Automec — autorização de supervisor se houver divergências)
```

---

## Build

### Servidor

```powershell
cd api
pyinstaller servidor.spec --clean --noconfirm
# Gera: api/dist/InvecServidor.exe

pyinstaller instalador.spec --clean --noconfirm
# Gera: api/dist/Instalar-Invec.exe  ← este é o arquivo que vai para o cliente
```

### App Android

```powershell
.\gradlew assembleRelease
# Gera: app/build/outputs/apk/release/app-release.apk
```

---

## Arquivos que NUNCA devem ir para o Git

- `api/licenca_privada.pem` — chave privada RSA (uso exclusivo Pontual Tecnologia)
- `api/gerar_licenca.py` — gerador de licenças
- `api/.env` / `C:\Invec\.env` — contém `JWT_SECRET` e `LICENSE_KEY` de produção
