# Invec — API de Inventário

Backend FastAPI para o sistema de contagem de estoque integrado ao Firebird (Automec). Desenvolvido pela **Pontual Tecnologia**.

---

## Stack

| Componente | Tecnologia |
|---|---|
| Runtime | Python 3.13 |
| Framework | FastAPI + Uvicorn |
| Banco de dados | Firebird 5 (Automec) via `firebird-driver` |
| Autenticação | JWT HS256 (8h) + Rate limiting |
| Licença | RSA 2048-bit (JWT RS256) |
| Distribuição | PyInstaller → `InvecServidor.exe` |
| Serviço Windows | NSSM |

---

## Estrutura

```
inventario-api/
├── main.py                  # Entrada FastAPI, lifespan (licença + migrations)
├── server.py                # Entrypoint Uvicorn para PyInstaller
├── servidor.spec            # Spec PyInstaller — InvecServidor.exe
├── instalador.spec          # Spec PyInstaller — Instalar-Invec.exe
├── app/
│   ├── database.py          # Conexão Firebird, context manager get_connection()
│   ├── security.py          # JWT HS256, get_current_user()
│   ├── licenca.py           # Validação RSA 2048-bit da licença
│   ├── migrations.py        # DDL automático (idempotente) na inicialização
│   ├── models/
│   │   └── schemas.py       # Pydantic models — request/response
│   └── routers/
│       ├── auth.py          # Login, rate limit, gestão de usuários mobile
│       ├── depositos.py     # Listagem de depósitos Firebird
│       ├── produtos.py      # Busca por código de barras e descrição
│       ├── inventario.py    # Bipagem, relatório, consolidação, auditoria
│       └── operadores.py    # CRUD de operadores (OPERADORES_APP)
```

---

## Endpoints principais

### Autenticação
| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth/login` | Login com rate limit (5 falhas/60s → bloqueio 300s) |
| GET | `/auth/usuarios` | Lista usuários com acesso mobile (admin mobile) |
| PUT | `/auth/usuarios/{id}/senha-mobile` | Define senha mobile do usuário |
| PUT | `/auth/usuarios/{id}/toggle-admin` | Alterna flag admin mobile (só MI) |

### Depósitos
| Método | Rota | Descrição |
|---|---|---|
| GET | `/depositos` | Lista depósitos do Firebird |

### Produtos
| Método | Rota | Descrição |
|---|---|---|
| GET | `/produtos/barcode/{codigo}` | Busca produto por código de barras |
| GET | `/produtos/busca?q=&cddeposito=` | Busca por descrição |

### Inventário
| Método | Rota | Descrição |
|---|---|---|
| GET | `/ping` | Health check sem autenticação (app detecta conectividade) |
| POST | `/sessao/iniciar` | Cria sessão de contagem (idempotente por session_id) |
| POST | `/inventario/bipagem` | Registra scan online (UPDATE atômico + INSERT) |
| POST | `/inventario/bipagem/lote` | Sincroniza lote offline (idempotente via LOTES_PROCESSADOS) |
| GET | `/inventario/relatorio/{cddeposito}` | Relatório da sessão atual |
| GET | `/inventario/resumo/{cddeposito}` | Produtos não contados |
| POST | `/inventario/consolidar` | Grava MOV_PRODUTO (TIPOMOVIMENTO=5) |
| PUT | `/inventario/bipagem/{cdproduto}` | Edita quantidade (auditado) |
| DELETE | `/inventario/bipagem/{cdproduto}` | Remove item da contagem (auditado) |
| GET | `/inventario/historico/{cddeposito}` | Histórico de consolidações com timestamp real |
| GET | `/inventario/log/{cddeposito}` | Log de auditoria (gerentes/admins) |

### Operadores
| Método | Rota | Descrição |
|---|---|---|
| GET | `/operadores` | Lista operadores da tabela OPERADORES_APP |
| POST | `/operadores` | Cria operador |
| PUT | `/operadores/{id}/toggle` | Ativa/desativa operador |

---

## Tabelas Firebird utilizadas

### Tabelas do Automec (leitura/escrita)
| Tabela | Uso |
|---|---|
| `USUARIOS` | Autenticação, colunas `SENHAMOBILE` e `MOBILE_ADMIN` adicionadas |
| `DEPOSITO` | Listagem de depósitos |
| `PRODUTO` + `PRODUTO_CODBARRA` | Busca por código de barras |
| `MOVIMENTO` | Estoque atual (`QTDEATUAL`) |
| `MOV_PRODUTO` | Consolidação grava `TIPOMOVIMENTO=5` |
| `SAIDAPRODUTO` + `SAIDAESTOQUE` | CE (Considerar Entrega) — pedidos pendentes |
| `PRODUTOPRECO` | `FATORCONV` e `VLCUSTO` para MOV_PRODUTO |

### Tabelas criadas pelo Invec
| Tabela | Uso |
|---|---|
| `INVENTARIO_TEMP` | Bipagens em andamento (por session_id + depósito) |
| `INVENTARIO_SESSAO` | Sessões de contagem por dispositivo (status, início, fim) |
| `LOTES_SYNC_PROCESSADOS` | Idempotência do sync offline — evita lotes duplicados |
| `SCANS_PROCESSADOS` | Idempotência por scan individual (UUID) — evita duplicata em retry de rede |
| `OPERADORES_APP` | Operadores de coleta físicos |
| `LOG_INVENTARIO` | Auditoria completa de todas as operações (TIMESTAMP) |
| `USUARIO_DEPOSITO` | Restrição de acesso por depósito por usuário |

---

## Segurança

- **JWT HS256** com expiração de 48h. `JWT_SECRET` no `.env`; se ausente, usa chave aleatória (aviso no console)
- **Rate limit** de login: 5 tentativas em 60s → bloqueio de 300s, por IP e por usuário; persistido em `LOG_INVENTARIO` (sobrevive a reinicializações); limpo ao fazer login com sucesso
- **Licença RSA 2048-bit**: JWT RS256, chave pública embutida em `app/licenca.py`. Servidor não sobe sem licença válida
- **Supervisor obrigatório** quando há divergências OU edições na sessão (`FRAUDE-2`); operadores precisam de gerente/admin diferente; gerentes podem autorizar a si mesmos
- **LOG_INVENTARIO** registra: `EDICAO`, `EDICAO_SUSPEITA`, `EXCLUSAO`, `ALERTA`, `ALERTA_REESCAN`, `CONSOLIDACAO`, `LOGIN_FALHOU`
- **ALERTA_REESCAN**: detecta produto excluído da contagem e re-escaneado na mesma sessão (possível fraude)
- **Sessões por dispositivo**: cada celular tem um `session_id` UUID independente — rastreabilidade completa por dispositivo no LOG e no histórico

---

## Variáveis de ambiente (`.env`)

```env
FB_DATABASE=C:\Caminho\para\banco.FDB
FB_HOST=localhost
FB_USER=SYSDBA
FB_PASSWORD=masterkey
PORT=8000
JWT_SECRET=chave-longa-e-aleatoria
LICENSE_KEY=eyJ...
```

---

## Desenvolvimento local

```bash
pip install -r requirements.txt
# Configure .env com o banco de teste
uvicorn main:app --reload --port 8000
```

Docs interativas: http://localhost:8000/docs

---

## Build e distribuição

```powershell
# 1. Compilar servidor
pyinstaller servidor.spec --clean --noconfirm
# Gera: dist\InvecServidor.exe

# 2. Compilar instalador
pyinstaller instalador.spec --clean --noconfirm
# Gera: dist\Instalar-Invec.exe
```

O cliente recebe apenas `Instalar-Invec.exe`. Veja [docs/INSTALACAO.md](docs/INSTALACAO.md) para o guia completo.

---

## Arquivos que NUNCA devem ir para o Git

- `licenca_privada.pem` — chave privada RSA (uso exclusivo Pontual Tecnologia)
- `gerar_licenca.py` — gerador de licenças
- `.env` — contém `JWT_SECRET` e `LICENSE_KEY` de produção
