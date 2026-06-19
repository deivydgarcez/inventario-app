# Invec — Inventário de Estoque Mobile

Aplicativo Android para **contagem de estoque** integrado ao ERP Automec. Substitui planilhas e papéis: o operador bipa os produtos com o celular, o sistema compara com o estoque do Automec e consolida tudo com um toque.

Desenvolvido pela **Pontual Tecnologia**.

---

## O problema que resolve

Fazer inventário no Automec tradicionalmente exige imprimir listas, anotar à mão e digitar tudo de volta no sistema — lento, sujeito a erro e sem rastreabilidade de quem fez o quê.

O Invec resolve isso colocando um leitor de código de barras no bolso do operador. Ele bipa os produtos direto no celular, vê em tempo real o que diverge do sistema e, ao final, consolida com um toque. O Automec é atualizado automaticamente, sem redigitação.

---

## Como funciona

### 1. Configuração inicial (uma vez só)
O servidor roda no computador da empresa onde o Automec está instalado. O app só precisa do IP desse computador para conectar via Wi-Fi.

### 2. Login
O usuário entra com o login e senha do Automec. O sistema suporta múltiplos usuários com níveis de acesso (operador, gerente, administrador).

### 3. Seleção de depósito e operador
Escolha qual depósito será inventariado e quem está fazendo a coleta física. Isso fica registrado em cada bipagem para fins de auditoria.

### 4. Bipagem dos produtos
Aponte a câmera do celular para o código de barras — ou use um leitor Bluetooth. O sistema soma as quantidades automaticamente se o mesmo produto for bipado mais de uma vez.

```
Bipa produto A  →  1 un
Bipa produto A  →  2 un  (soma, não duplica)
Bipa produto B  →  1 un
```

Se a quantidade parecer absurda (mais de 2× o estoque do sistema), o app avisa na hora.

### 5. Relatório em tempo real
A qualquer momento, acesse o relatório e veja:

| Produto | Sistema | Contada | Dif |
|---|---|---|---|
| Filtro de ar | 10 | 12 | **+2** |
| Correia dentada | 5 | 3 | **-2** |
| Vela de ignição | 8 | 8 | 0 |

Itens com divergência ficam marcados. É possível editar ou remover qualquer item — tudo registrado em log com motivo obrigatório.

### 6. Recontagem (quando há divergências)
Antes de consolidar, o sistema recomenda uma segunda contagem dos itens divergentes. O operador bipa novamente e o app compara as duas contagens, mostrando o que mudou.

Se mais de 30% dos itens divergirem, a recontagem é **obrigatória** antes de consolidar.

### 7. Consolidação
Confirmar a consolidação grava tudo no Automec (`MOV_PRODUTO`, tipo inventário). O estoque é atualizado automaticamente pelo próprio trigger do Automec.

Quando há divergências, é exigida a **autorização de um supervisor** (gerente ou admin) com login e senha separados — garantindo que nenhum operador consolide um inventário problemático sozinho.

---

## Segurança e rastreabilidade

Toda operação é registrada no log de auditoria:

- **Quem** fez (usuário logado)
- **Quando** (data e hora)
- **Com qual dispositivo** (ID único do celular)
- **O que foi feito** (bipagem, edição, exclusão, consolidação)
- **Motivo** (obrigatório para edições e exclusões)

O sistema detecta automaticamente padrões suspeitos, como um produto excluído e re-escaneado na mesma sessão, e registra alertas no log.

---

## Arquitetura

```
[Celular Android]  ──Wi-Fi──  [InvecServidor.exe]  ──  [Firebird / Automec]
     App Kotlin                  FastAPI + Python           banco .FDB
```

O servidor roda como serviço Windows (`InvecAPI`) no mesmo computador do Automec. Vários celulares podem trabalhar simultaneamente no mesmo depósito.

---

## Documentação

- [Guia de Instalação do Servidor](docs/INSTALACAO.md) — como instalar o `Instalar-Invec.exe` no Windows
- [Manual de Uso do App](docs/MANUAL_USO.md) — passo a passo para o usuário final
- [Documentação Técnica do Backend](api/README.md) — endpoints, banco de dados, segurança

---

## Build

### Servidor Windows

```powershell
cd api
pyinstaller servidor.spec --clean --noconfirm
# → api/dist/InvecServidor.exe

pyinstaller instalador.spec --clean --noconfirm
# → api/dist/Instalar-Invec.exe  (este vai para o cliente)
```

### App Android

```powershell
.\gradlew assembleRelease
# → app/build/outputs/apk/release/app-release.apk
```

---

## Estrutura do repositório

```
inventario-app/
├── api/              ← Backend FastAPI (Python)
├── app/              ← App Android (Kotlin)
└── docs/
    ├── INSTALACAO.md
    └── MANUAL_USO.md
```

---

> **Nota de segurança:** Os arquivos `api/licenca_privada.pem`, `api/gerar_licenca.py` e `C:\Invec\.env` nunca devem ser commitados ou distribuídos.
