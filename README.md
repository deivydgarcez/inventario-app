# Invec — Inventário de Estoque Mobile

**Invec** é um sistema de contagem de estoque para lojas e distribuidoras que usam o ERP Automec. Com ele, a equipe realiza o inventário direto pelo celular — bipando os produtos com a câmera ou um leitor Bluetooth — e o sistema atualiza o Automec automaticamente ao final.

Desenvolvido pela **Pontual Tecnologia**.

---

## O que o Invec faz

### Contagem pelo celular
O operador abre o app, seleciona o depósito e começa a bipar os produtos. Cada leitura soma a quantidade no sistema. Se o mesmo produto for bipado várias vezes, o sistema acumula corretamente. Não precisa de papel, planilha nem digitação posterior.

### Comparação em tempo real com o estoque
Enquanto a contagem acontece, o app mostra para cada produto:
- Quanto tem no sistema (Automec)
- Quanto foi contado
- A diferença

Se a quantidade bipada parecer muito acima do esperado, o app avisa o operador na hora.

### Recontagem antes de fechar
Quando há diferenças significativas, o app sugere uma segunda contagem para confirmar os valores. O operador bipa novamente os produtos divergentes e o sistema compara as duas contagens. Se mais de 30% dos itens divergirem, a recontagem é obrigatória.

### Consolidação com autorização
Ao consolidar, os dados são gravados no Automec e o estoque é atualizado automaticamente. Quando há divergências, um **supervisor** (gerente ou administrador) precisa autorizar com login e senha — evitando que inventários com erros sejam fechados sem revisão.

### Auditoria completa
Toda operação fica registrada: quem fez, quando, com qual dispositivo e o motivo de cada edição ou exclusão. Gerentes e administradores podem consultar o histórico completo de qualquer depósito.

### Funciona em rede local
O servidor roda no próprio computador da loja, sem dependência de internet. Vários celulares podem trabalhar em paralelo no mesmo inventário.

---

## Telas do app

| Tela | Função |
|---|---|
| Login | Autenticação com usuário do Automec |
| Início | Seleção de depósito e operador |
| Scanner | Bipagem com câmera ou leitor Bluetooth |
| Relatório | Visualização e edição dos itens contados |
| Recontagem | Segunda contagem dos itens com divergência |
| Histórico | Inventários anteriores consolidados |
| Auditoria | Log completo de operações (gerentes/admins) |
| Operadores | Cadastro de operadores de coleta |
| Usuários | Gerenciamento de acesso mobile |

---

## Para quem é

- Lojas e distribuidoras que usam o **Automec** como ERP
- Equipes que fazem inventário periódico (mensal, trimestral ou anual)
- Operações com **um ou mais depósitos**
- Times com **múltiplos operadores** trabalhando em paralelo

---

## Documentação

- [Manual de Instalação e Uso](docs/Invec_Manual.pdf) — como instalar o servidor e usar o app
- [Documentação Técnica](docs/Invec_Tecnico.pdf) — arquitetura, endpoints e programação

---

## Estrutura do repositório

```
inventario-app/
├── api/    ← Backend FastAPI (Python) — compila para InvecServidor.exe
├── app/    ← App Android (Kotlin)
└── docs/   ← Documentação PDF
```
