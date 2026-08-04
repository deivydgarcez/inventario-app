# Sistema de Licença Invec

## Visão geral

O Invec usa criptografia assimétrica **RSA 2048-bit / JWT RS256** para controlar o acesso por cliente.

- A **chave privada** (`licenca_privada.pem`) fica exclusivamente com a Pontual Tecnologia e é usada para assinar licenças.
- A **chave pública** está embutida no código do servidor e verifica a assinatura no startup.
- O servidor **não sobe** sem uma licença válida — qualquer falha de validação encerra o processo imediatamente.

---

## Para a Pontual — gerar uma licença

### Pré-requisito

O arquivo `licenca_privada.pem` deve estar dentro da pasta `api/` do repositório (nunca sobe para o git — fica apenas na máquina da Pontual).

### Passo a passo

```powershell
cd C:\Administracao\inventario-app\api
python gerar_licenca.py
```

O script vai pedir quatro informações:

| Campo | O que digitar | Exemplo |
|-------|--------------|---------|
| Nome do cliente | Razão social completa | `Comércio Silva Ltda` |
| CNPJ | Com ou sem formatação | `12.345.678/0001-90` |
| Validade (meses) | Número de meses, ou **Enter** para permanente | `12` ou *(Enter)* |
| ID da máquina | UUID do BIOS do servidor do cliente, ou **Enter** sem vínculo | *(ver seção abaixo)* |

Ao final, o script exibe:

```
=======================================================
  Cliente    : Comércio Silva Ltda
  CNPJ       : 12.345.678/0001-90
  Emitida    : 2026-08-04
  Expira     : 2027-08-04
  Maquina    : Sem vinculo (reutilizavel)
=======================================================

Adicione a linha abaixo no arquivo .env do cliente:

LICENSE_KEY=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

Copie a linha `LICENSE_KEY=...` completa — ela é a licença do cliente.

---

## Validade

| Situação | O que digitar | Comportamento |
|----------|--------------|---------------|
| Licença permanente | *(Enter em branco)* | Nunca expira |
| 6 meses | `6` | Expira em 6 meses a partir de hoje |
| 12 meses | `12` | Expira em 12 meses a partir de hoje |
| 24 meses | `24` | Expira em 24 meses a partir de hoje |

Quando a licença expira, o servidor não sobe e o log registra:

```
[Invec] ERRO DE LICENCA

  Licenca expirada em YYYY-MM-DD.
  Renove sua licenca com a Pontual Tecnologia.
```

Para renovar: gere uma nova licença com nova validade e atualize o `.env` no cliente — não é necessário reinstalar.

---

## Vinculação por máquina (opcional)

Vinculando a licença ao UUID do BIOS do servidor do cliente, ela só funciona naquele computador. Recomendado para maior controle de distribuição.

### Como obter o ID da máquina do cliente

**Opção 1 — pelo instalador (mais fácil):**
A tela do `Instalar-Invec.exe` exibe o ID da máquina automaticamente com um botão "Copiar".

**Opção 2 — pelo PowerShell (se o cliente já tem o servidor):**
```powershell
(Get-CimInstance -ClassName Win32_ComputerSystemProduct).UUID
```

### Sem vinculação

Se deixar o campo de ID da máquina em branco ao gerar, a licença funciona em qualquer computador. Use para clientes em avaliação ou quando não há risco de redistribuição.

---

## Para o cliente — instalar a licença

### Via instalador (recomendado — primeira instalação)

1. Execute `Instalar-Invec.exe` como Administrador.
2. No campo **License Key**, cole o valor `eyJhbGciOiJSUzI1NiJ9...` fornecido pela Pontual.
3. Clique em **Instalar** — a chave é gravada automaticamente em `C:\Administracao\Invec\.env`.

### Manualmente (renovação ou reinstalação)

1. Abra `C:\Administracao\Invec\.env` com o Bloco de Notas.
2. Localize a linha `LICENSE_KEY=` e substitua pelo novo valor:
   ```
   LICENSE_KEY=eyJhbGciOiJSUzI1NiJ9...
   ```
3. Salve o arquivo.
4. Reinicie o serviço como Administrador:
   ```powershell
   C:\Administracao\Invec\nssm.exe stop  InvecAPI
   C:\Administracao\Invec\nssm.exe start InvecAPI
   ```

---

## O que aparece no log quando a licença é válida

Ao subir com licença correta, o log exibe:

```
[Invec] Licenca valida
[Invec] Cliente  : Comércio Silva Ltda
[Invec] CNPJ     : 12.345.678/0001-90
[Invec] Expira em: 2027-08-04
```

Para licença permanente, o campo `Expira em` exibe `Permanente`.

O log fica em `C:\Administracao\Invec\logs\servico.log`.

---

## Erros de licença

| Mensagem no log | Causa | Solução |
|-----------------|-------|---------|
| `Licenca nao encontrada` | `LICENSE_KEY` ausente ou vazio no `.env` | Colar a chave no `.env` |
| `Licenca invalida ou corrompida` | Chave adulterada, truncada ou incorreta | Solicitar nova licença à Pontual |
| `Licenca expirada em YYYY-MM-DD` | Prazo vencido | Pontual gera nova licença com validade renovada |
| `Esta licenca pertence a outro equipamento` | Servidor rodando em PC diferente do cadastrado | Pontual gera licença com o UUID correto |
| `Nao foi possivel verificar o identificador desta maquina` | Licença vinculada mas UUID do BIOS inacessível | Pontual gera licença sem vínculo de máquina |

Todos os erros de licença encerram o serviço. O log completo fica em:
- `C:\Administracao\Invec\logs\servico.log` — saída padrão do servidor
- `C:\Administracao\Invec\logs\erro.log` — erros de processo

---

## Payload da licença (referência técnica)

A licença é um JWT assinado com RS256. O payload contém:

```json
{
  "produto":    "Invec",
  "cliente":    "Comércio Silva Ltda",
  "cnpj":       "12.345.678/0001-90",
  "emitida_em": "2026-08-04",
  "expira_em":  "2027-08-04",
  "machine_id": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
}
```

> `expira_em` vazio (`""`) = licença permanente.  
> `machine_id` ausente = licença sem vínculo de máquina.

---

## Licença de desenvolvimento (Pontual interna)

Para uso nos ambientes de desenvolvimento e teste da Pontual:

| Campo | Valor |
|-------|-------|
| Cliente | Pontual Tecnologia - Desenvolvimento |
| CNPJ | 00.000.000/0000-00 |
| Expira em | 2036-06-16 |
| Vinculada | Não |

Gerada sem `machine_id` — funciona em qualquer máquina da Pontual.
