# Manual de Uso — App Invec

Guia completo para usar o aplicativo de inventário nos celulares Android.

---

## Índice

1. [Configurar o servidor](#1-configurar-o-servidor)
2. [Fazer login](#2-fazer-login)
3. [Selecionar depósito e operador](#3-selecionar-depósito-e-operador)
4. [Bipar produtos](#4-bipar-produtos)
5. [Consultar o relatório](#5-consultar-o-relatório)
6. [Editar ou remover um item](#6-editar-ou-remover-um-item)
7. [Fazer recontagem](#7-fazer-recontagem)
8. [Consolidar o inventário](#8-consolidar-o-inventário)
9. [Consultar histórico](#9-consultar-histórico)
10. [Auditoria de operações](#10-auditoria-de-operações)
11. [Gerenciar operadores](#11-gerenciar-operadores)
12. [Gerenciar usuários mobile](#12-gerenciar-usuários-mobile)

---

## 1. Configurar o servidor

Na **primeira vez** que usar o app em um celular, você precisa informar o endereço do servidor.

1. Na tela de login, preencha o campo **"URL"** com o endereço do servidor
2. Exemplo: `http://192.168.1.31:8000/`
3. Toque em **"Salvar servidor"**

> O endereço só precisa ser configurado uma vez por celular. Se o servidor mudar de IP, atualize aqui.

---

## 2. Fazer login

1. Digite seu **login** e **senha** do Automec
   - Na primeira vez, o gerente precisa cadastrar sua senha mobile na tela de Usuários
2. Toque em **"Entrar"**

**Observações:**
- Após **15 minutos sem usar o app**, a sessão é encerrada automaticamente por segurança
- Após **5 tentativas erradas**, o login fica bloqueado por **5 minutos**
- A sessão dura **8 horas** — após isso, faça login novamente

---

## 3. Selecionar depósito e operador

Após o login, você estará na **tela principal**.

**Selecionar o depósito:**
1. Toque em **"Selecionar Depósito"**
2. Escolha o depósito na lista

**Selecionar o operador:**
- Toque no campo de operador para escolher quem está fazendo a coleta física
- O operador é quem está com o celular na mão bipando os produtos
- Pode ser diferente do usuário logado no sistema

> O operador **trava** assim que você bipa o primeiro produto. Para trocar de operador, saia e entre novamente.

---

## 4. Bipar produtos

Toque em **"Iniciar Bipagem"** para abrir o scanner.

### Modo Câmera

1. Toque em **"Escanear"**
2. Aponte a câmera para o código de barras do produto
3. O produto é registrado automaticamente

**Modo contínuo (switch "Múltiplos"):** ativa a leitura automática um após o outro sem precisar tocar em "Escanear" a cada produto.

### Modo Bluetooth

1. Toque em **"BT"** no canto superior para alternar para Bluetooth
2. Use o leitor Bluetooth normalmente — o app captura o código automaticamente

### Digitar código manualmente

Se o código de barras estiver danificado:
1. Toque em **"Digitar código"**
2. Digite o código e toque em **"Buscar"**

### Informações após cada scan

Após cada bipagem bem-sucedida, o app mostra:
- Nome do produto
- Quantidade total acumulada neste produto
- Contador de bipagens da sessão

**Alerta de quantidade suspeita:** se a quantidade contada for mais de 2× o estoque do sistema, o app exibe um aviso. Confirme se o valor está correto.

---

## 5. Consultar o relatório

Na tela principal, toque em **"Relatório"**.

O relatório mostra todos os produtos bipados com:

| Coluna | O que significa |
|---|---|
| **Sistema** | Quantidade no estoque do Automec no momento do 1º scan |
| **Contada** | Quantidade total bipada na sessão |
| **Dif** | Diferença: Contada − Sistema |

**Cores da diferença:**
- Verde: sobra de estoque (contado > sistema)
- Vermelho: falta de estoque (contado < sistema)
- Cinza: sem diferença

**Aviso de não contados:** se houver produtos com estoque positivo no Automec que não foram bipados, o app exibe um aviso no topo.

---

## 6. Editar ou remover um item

### Editar quantidade

1. No relatório, **toque no produto** que deseja editar
2. Informe a nova quantidade
3. Informe o **motivo** da alteração (obrigatório para auditoria)
4. Toque em **"Salvar"**

### Remover da contagem

1. **Deslize o item para a esquerda ou direita**
2. Informe o motivo da remoção
3. Toque em **"Remover"**

> Toda edição e remoção fica registrada no log de auditoria com seu usuário, data/hora e dispositivo.

---

## 7. Fazer recontagem

Se houver divergências, o app recomendará a recontagem (botão verde **"✓ Fazer Recontagem"**).

1. No relatório, toque em **"✓ Fazer Recontagem"**
2. Bipe os produtos novamente para a 2ª contagem
3. O app compara 1ª e 2ª contagem e mostra as diferenças

**Ao finalizar a recontagem, você terá 4 opções:**

| Opção | O que faz |
|---|---|
| **Consolidar agora** | Aplica a 2ª contagem e já consolida direto |
| **Aplicar 2ª contagem** | Atualiza os valores e volta ao relatório para revisar |
| **Manter 1ª contagem** | Descarta a 2ª contagem, volta ao relatório |
| **Continuar recontando** | Fecha o diálogo e continua bipando |

---

## 8. Consolidar o inventário

A consolidação grava os dados no Automec (tabela `MOV_PRODUTO`). Esta operação **não pode ser desfeita**.

1. No relatório, toque em **"Consolidar"**
2. Revise o resumo e confirme

### Sem divergências

Toque em **"Consolidar agora"** — não precisa de supervisor.

### Com divergências

Quando há diferenças entre contado e sistema, é obrigatória a **autorização de um supervisor**:

1. Toque em **"Consolidar mesmo assim"**
2. Informe o **login e senha mobile** de um **gerente ou administrador**
3. Toque em **"Autorizar e Consolidar"**

> **Regra:** Operadores precisam de um gerente ou admin **diferente** para autorizar. Gerentes e admins podem autorizar com as próprias credenciais.

### Quando a recontagem é obrigatória

Se **mais de 30% dos itens** (mínimo 5 itens) tiverem divergência, o app **bloqueia** a consolidação e exige recontagem antes. Faça a recontagem e volte.

---

## 9. Consultar histórico

No relatório, toque em **"Histórico"**.

Mostra todas as consolidações realizadas para o depósito selecionado, com:
- Produto
- Quantidade contada
- Quantidade do sistema
- Data

---

## 10. Auditoria de operações

Disponível apenas para **gerentes e administradores**.

No relatório, toque em **"Auditoria"**.

O log mostra todas as operações com:
- Tipo (edição, exclusão, alerta, consolidação, etc.)
- Produto e quantidades
- Usuário, operador e dispositivo
- Data e hora
- Motivo informado

**Tipos de evento:**
| Tipo | O que significa |
|---|---|
| EDICAO | Quantidade editada manualmente |
| EDICAO_SUSPEITA | Edição que fez o valor coincidir exatamente com o estoque do sistema |
| EXCLUSAO | Item removido da contagem |
| CONSOLIDACAO | Inventário consolidado |
| ALERTA | Quantidade bipada muito acima do esperado |
| ALERTA_REESCAN | Produto excluído e re-escaneado na mesma sessão |

---

## 11. Gerenciar operadores

Disponível para **gerentes e administradores**.

Na tela principal, toque em **"Operadores"**.

- Toque em **"+"** para adicionar um operador
- Toque em **"Desativar"** / **"Ativar"** para ativar ou desativar

Operadores são as pessoas que fazem a coleta física. Eles aparecem na lista de seleção antes da bipagem.

---

## 12. Gerenciar usuários mobile

Disponível apenas para **admin mobile** (geralmente o usuário MI).

Na tela principal, toque em **"Usuários"**.

### Definir senha mobile

Todo usuário que vai usar o app precisa de uma **senha mobile** (separada da senha do Automec).

1. Localize o usuário na lista
2. Toque em **"Definir senha"** ou **"Alterar senha"**
3. Digite a nova senha e confirme

### Admin mobile

O admin mobile pode delegar permissões de administração para outros usuários:
1. Localize o usuário
2. Toque em **"Dar admin mobile"** / **"Remover admin mobile"**

---

## Dicas gerais

- **Troque o modo câmera/BT** tocando no botão no canto superior direito do scanner
- **O operador trava** após o primeiro scan — escolha o operador certo antes de começar
- **Nunca feche o app no meio de uma consolidação** — aguarde a confirmação
- **Se o app travar**, o servidor mantém todos os dados. Basta abrir novamente e continuar
- **Relatórios de consolidação** são salvos automaticamente no servidor em `C:\Invec\relatorios\`
