# Guia de Instalação — Invec Servidor

Instala o servidor Invec em um computador Windows com Automec + Firebird 5.

---

## Pré-requisitos

- Windows 10 ou 11 (64-bit)
- Automec instalado e funcionando com Firebird 5
- Acesso de **Administrador** no computador servidor
- Arquivo `Instalar-Invec.exe` fornecido pela Pontual Tecnologia
- Chave de **licença** (`LICENSE_KEY`) fornecida pela Pontual Tecnologia
- Rede Wi-Fi interna para os celulares acessarem o servidor

---

## Passo 1 — Executar o instalador

Clique com o botão direito em `Instalar-Invec.exe` → **Executar como administrador**.  
Se aparecer o aviso do Windows (UAC), clique em **Sim**.

---

## Passo 2 — Preencher os campos

| Campo | O que preencher | Exemplo |
|---|---|---|
| Banco de dados Firebird | Caminho completo do `.FDB` do Automec. Use o botão `...` para navegar. | `C:\Automec\Dados\empresa.FDB` |
| Host Firebird | `localhost` se o banco está na mesma máquina | `localhost` |
| Usuário Firebird | Normalmente `SYSDBA` | `SYSDBA` |
| Senha Firebird | Senha do Firebird (padrão de instalação: `masterkey`) | `masterkey` |
| Porta da API | Porta TCP que o app usará. Padrão `8000`. | `8000` |
| Chave de Licença | String JWT fornecida pela Pontual Tecnologia. **Obrigatória.** | `eyJhbGciOiJSUzI1NiJ9...` |

> O caminho do banco pode ser encontrado no Automec em **Arquivo → Configurações → Banco de dados**.

---

## Passo 3 — Instalar / Atualizar

Clique em **Instalar / Atualizar**. O instalador irá:

1. Criar `C:\Invec\` com subpastas `logs\` e `relatorios\`
2. Copiar o servidor para `C:\Invec\InvecServidor.exe`
3. Salvar todas as configurações (incluindo a licença) em `C:\Invec\.env`
4. Registrar o serviço Windows **InvecAPI** (inicia automaticamente com o Windows)
5. Liberar a porta no Firewall do Windows
6. Iniciar o serviço

Ao concluir aparece: **"Serviço instalado e iniciado com sucesso!"**

---

## Passo 4 — Verificar se o servidor subiu

Abra o navegador **no próprio computador servidor** e acesse:

```
http://localhost:8000/
```

Deve aparecer: `{"status": "ok", "versao": "1.0.0"}`

Se aparecer erro, consulte `C:\Invec\logs\servico.log`.

---

## Passo 5 — Descobrir o IP para os celulares

Abra o Prompt de Comando (Win+R → `cmd`) e execute:

```
ipconfig
```

Procure **Endereço IPv4** na placa de rede da empresa (ex: `192.168.1.31`).  
O endereço que você configura nos celulares será:

```
http://192.168.1.31:8000/
```

> Recomendável configurar IP fixo no roteador para este computador.

---

## Licença — o que fazer quando expira ou está inválida

O servidor valida a licença **toda vez que é iniciado**. Sem licença válida, não sobe.

| Mensagem no log | Causa | Solução |
|---|---|---|
| `Licenca nao encontrada` | Campo LICENSE_KEY vazio ou ausente no `.env` | Abrir o instalador, colar a chave e clicar em Reiniciar Serviço |
| `Licenca invalida ou corrompida` | Chave adulterada ou errada | Contatar a Pontual Tecnologia para nova chave |
| `Licenca expirada em YYYY-MM-DD` | Licença com prazo vencido | Contatar a Pontual Tecnologia para renovar |

> Log de licença: `C:\Invec\logs\servico.log` — procure por linhas com `[LICENCA]`.

---

## Instalar o app nos celulares

1. Transfira `invec-app.apk` para o celular (USB, WhatsApp ou e-mail)
2. Abra o arquivo no celular e instale. Se pedir permissão de "fonte desconhecida", aceite.
3. Abra o app Invec
4. No campo **URL do servidor**, informe o endereço (ex: `http://192.168.1.31:8000/`)
5. Toque em **Salvar servidor**
6. Faça login com seu usuário e senha mobile

> A URL só precisa ser configurada uma vez por celular. Se o IP mudar, atualize antes de logar.

---

## Atualizar o servidor

Recebeu um novo `Instalar-Invec.exe`? Execute como Administrador e clique em **Instalar / Atualizar**.  
O serviço é parado, atualizado e reiniciado automaticamente. A licença e os dados são preservados.

---

## Gerenciar o serviço manualmente

Abra o Prompt de Comando como Administrador:

```
net stop InvecAPI     # para o servidor
net start InvecAPI    # inicia o servidor
sc query InvecAPI     # mostra o status
```

---

## Solução de problemas

| Problema | Causa provável | Solução |
|---|---|---|
| Servidor não sobe | Licença ausente ou inválida | Ver `servico.log` e contatar Pontual Tecnologia |
| Servidor não sobe | Caminho do banco `.FDB` errado | Corrigir no instalador e reinstalar |
| Servidor não sobe | Firebird não está rodando | Verificar se o Automec está acessível |
| App não conecta | IP errado no campo URL | Verificar com `ipconfig` e testar no navegador do celular |
| App não conecta | Porta bloqueada no firewall | Executar o instalador novamente |
| Sessão encerrada automaticamente | 15 min sem usar o app | Normal — faça login novamente |
| Login recusado no app | Usuário sem senha mobile | Admin mobile deve cadastrar senha na tela Usuários |
| Erro ao consolidar | Banco Firebird indisponível | Verificar Automec e reiniciar o serviço |
