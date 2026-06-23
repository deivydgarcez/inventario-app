# Guia de Instalação — Invec Servidor

Este guia explica como instalar o servidor Invec em um computador Windows que já possui o Automec com Firebird 5.

---

## Pré-requisitos

- Windows 10 ou 11 (64-bit)
- Automec instalado e funcionando com Firebird 5
- Acesso de **Administrador** no computador servidor
- Arquivo `Instalar-Invec.exe` fornecido pela Pontual Tecnologia
- Chave de licença (`LICENSE_KEY`) fornecida pela Pontual Tecnologia

---

## Passo 1 — Executar o instalador

1. Clique com o botão direito em `Instalar-Invec.exe`
2. Selecione **"Executar como administrador"**
3. Se aparecer o aviso do Windows (UAC), clique em **Sim**

---

## Passo 2 — Preencher as configurações

O instalador abrirá uma janela com os campos abaixo:

| Campo | O que preencher | Exemplo |
|---|---|---|
| **Banco de dados Firebird** | Caminho completo do arquivo `.FDB` do Automec | `C:\Automec\dados\empresa.FDB` |
| **Host Firebird** | Deixar `localhost` se o banco está na mesma máquina | `localhost` |
| **Usuário Firebird** | Normalmente `SYSDBA` | `SYSDBA` |
| **Senha Firebird** | Senha do Firebird (padrão: `masterkey`) | `masterkey` |
| **Porta da API** | Porta TCP que o app vai usar para conectar | `8000` |
| **JWT Secret** | Qualquer texto longo e aleatório (mínimo 32 caracteres) | `minha-chave-secreta-123456` |
| **License Key** | Chave de licença fornecida pela Pontual Tecnologia | `eyJhbGciOiJSUzI1NiJ9...` |

> **Dica:** O caminho do banco pode ser encontrado nas configurações do Automec, em Arquivo > Configurações > Banco de dados.

---

## Passo 3 — Clicar em "Instalar / Atualizar"

O instalador irá automaticamente:

1. Criar a pasta `C:\Invec\`
2. Copiar o servidor para `C:\Invec\InvecServidor.exe`
3. Gravar o arquivo `C:\Invec\.env` com as configurações
4. Registrar o serviço Windows **InvecAPI** (inicia automaticamente com o Windows)
5. Abrir a porta configurada no Firewall do Windows
6. Iniciar o servidor

Ao final, aparecerá a mensagem **"Instalação concluída com sucesso"**.

---

## Passo 4 — Verificar se o servidor subiu

Abra o navegador no servidor e acesse:

```
http://localhost:8000/
```

Deve aparecer:
```json
{"status": "ok", "versao": "1.0.0"}
```

---

## Passo 5 — Descobrir o IP da rede local

Para que os celulares consigam conectar, você precisa saber o IP do servidor na rede local.

Abra o **Prompt de Comando** e digite:
```
ipconfig
```

Procure por **"Endereço IPv4"** na adaptador de rede da empresa. Exemplo: `192.168.1.31`

O endereço que você vai digitar no app será:
```
http://192.168.1.31:8000/
```

---

## Atualizar o servidor (nova versão)

Quando receber um novo `Instalar-Invec.exe` da Pontual Tecnologia:

1. Execute novamente como Administrador
2. Preencha os mesmos campos (ou os campos já virão preenchidos com os valores atuais)
3. Clique em **"Instalar / Atualizar"**

O serviço será parado automaticamente, atualizado e reiniciado.

---

## Verificar logs do servidor

Se algo não funcionar, os logs ficam em:

```
C:\Invec\logs\servico.log   ← saída normal do servidor
C:\Invec\logs\erro.log      ← erros
```

Para visualizar em tempo real, abra PowerShell como Administrador e rode:
```powershell
Get-Content C:\Invec\logs\servico.log -Wait -Tail 50
```

---

## Gerenciar o serviço manualmente

Abra **Prompt de Comando como Administrador**:

```cmd
# Parar o servidor
net stop InvecAPI

# Iniciar o servidor
net start InvecAPI

# Ver status
sc query InvecAPI
```

---

## Estrutura de arquivos após a instalação

```
C:\Invec\
├── InvecServidor.exe     ← servidor da API
├── nssm.exe              ← gerenciador de serviço Windows
├── .env                  ← configurações (não compartilhar)
├── relatorios\           ← relatórios de consolidação gerados automaticamente
└── logs\
    ├── servico.log       ← log do servidor (rotação automática a cada 10 MB)
    └── erro.log          ← erros do servidor
```

---

## Solução de problemas

| Problema | Causa provável | Solução |
|---|---|---|
| Servidor não sobe | Licença inválida ou expirada | Verificar `servico.log` e contatar Pontual Tecnologia |
| Servidor não sobe | Caminho do banco errado | Verificar `C:\Invec\.env` e reinstalar |
| App não conecta | IP errado ou firewall | Verificar IP com `ipconfig` e testar `http://IP:8000/` no navegador |
| App não conecta | Porta bloqueada | Executar o instalador novamente (reabre a regra de firewall) |
| Login recusado | Usuário sem senha mobile | Cadastrar senha mobile na tela de Usuários do app |
| Erro 500 ao consolidar | Banco Firebird fora do ar | Verificar se o Automec está funcionando normalmente |
