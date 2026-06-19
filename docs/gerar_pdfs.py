"""Gera os PDFs de documentação do Invec usando ReportLab."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import ListFlowable, ListItem
import os

LARANJA = colors.HexColor("#CC5B2A")
CINZA_CLARO = colors.HexColor("#F5F5F5")
CINZA_BORDA = colors.HexColor("#DDDDDD")
PRETO = colors.HexColor("#212121")
CINZA_TEXTO = colors.HexColor("#555555")

W, H = A4
MARGEM = 2.2 * cm


def estilos():
    base = getSampleStyleSheet()
    s = {}

    s["capa_titulo"] = ParagraphStyle("capa_titulo",
        fontName="Helvetica-Bold", fontSize=28, textColor=LARANJA,
        spaceAfter=8, alignment=TA_CENTER)

    s["capa_sub"] = ParagraphStyle("capa_sub",
        fontName="Helvetica", fontSize=14, textColor=CINZA_TEXTO,
        spaceAfter=4, alignment=TA_CENTER)

    s["capa_empresa"] = ParagraphStyle("capa_empresa",
        fontName="Helvetica-Bold", fontSize=11, textColor=CINZA_TEXTO,
        spaceAfter=2, alignment=TA_CENTER)

    s["h1"] = ParagraphStyle("h1",
        fontName="Helvetica-Bold", fontSize=16, textColor=LARANJA,
        spaceBefore=18, spaceAfter=6)

    s["h2"] = ParagraphStyle("h2",
        fontName="Helvetica-Bold", fontSize=12, textColor=PRETO,
        spaceBefore=12, spaceAfter=4)

    s["h3"] = ParagraphStyle("h3",
        fontName="Helvetica-Bold", fontSize=10, textColor=CINZA_TEXTO,
        spaceBefore=8, spaceAfter=3)

    s["corpo"] = ParagraphStyle("corpo",
        fontName="Helvetica", fontSize=9.5, textColor=PRETO,
        leading=15, spaceAfter=5, alignment=TA_JUSTIFY)

    s["code"] = ParagraphStyle("code",
        fontName="Courier", fontSize=8.5, textColor=PRETO,
        leading=13, spaceAfter=4,
        backColor=CINZA_CLARO, borderPadding=(5, 8, 5, 8),
        leftIndent=8, rightIndent=8)

    s["nota"] = ParagraphStyle("nota",
        fontName="Helvetica-Oblique", fontSize=8.5, textColor=CINZA_TEXTO,
        leading=13, spaceAfter=4)

    s["aviso"] = ParagraphStyle("aviso",
        fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#B71C1C"),
        leading=13, spaceAfter=4)

    return s


def capa(story, s, titulo, subtitulo, versao="v1.0"):
    story.append(Spacer(1, 4 * cm))
    story.append(Paragraph("INVEC", s["capa_titulo"]))
    story.append(Paragraph(titulo, ParagraphStyle("t2",
        fontName="Helvetica-Bold", fontSize=18, textColor=PRETO,
        spaceAfter=6, alignment=TA_CENTER)))
    story.append(Paragraph(subtitulo, s["capa_sub"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="60%", thickness=2, color=LARANJA, hAlign="CENTER"))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("Pontual Tecnologia", s["capa_empresa"]))
    story.append(Paragraph(versao + "  ·  2026", s["nota"]))
    story.append(PageBreak())


def hr(story):
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=0.5, color=CINZA_BORDA))
    story.append(Spacer(1, 6))


def tabela(story, cabecalho, linhas, col_widths=None):
    data = [cabecalho] + linhas
    w = col_widths or ([4 * cm] + [(W - 2 * MARGEM - 4 * cm) / (len(cabecalho) - 1)] * (len(cabecalho) - 1))
    t = Table(data, colWidths=w)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LARANJA),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CINZA_CLARO]),
        ("GRID", (0, 0), (-1, -1), 0.3, CINZA_BORDA),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))


def lista(story, s, itens):
    items = [ListItem(Paragraph(i, s["corpo"]), bulletColor=LARANJA, leftIndent=16) for i in itens]
    story.append(ListFlowable(items, bulletType="bullet", start="•"))
    story.append(Spacer(1, 4))


# ─────────────────────────────────────────────
# MANUAL (INSTALAÇÃO + USO)
# ─────────────────────────────────────────────

def gerar_manual(caminho):
    doc = SimpleDocTemplate(caminho, pagesize=A4,
        leftMargin=MARGEM, rightMargin=MARGEM,
        topMargin=MARGEM, bottomMargin=MARGEM,
        title="Invec — Manual de Instalação e Uso")
    s = estilos()
    story = []

    capa(story, s, "Manual de Instalação e Uso",
         "Guia completo para instalação do servidor e uso do aplicativo")

    # ── PARTE 1: INSTALAÇÃO ──────────────────
    story.append(Paragraph("PARTE 1 — INSTALAÇÃO DO SERVIDOR", s["h1"]))
    hr(story)

    story.append(Paragraph("O que é o servidor Invec", s["h2"]))
    story.append(Paragraph(
        "O Invec funciona em dois componentes: o <b>servidor</b> (instalado no computador da loja) "
        "e o <b>aplicativo</b> (instalado nos celulares Android). O servidor é quem se conecta ao "
        "banco de dados do Automec e processa todas as operações. Os celulares se comunicam com o "
        "servidor pelo Wi-Fi da empresa.", s["corpo"]))

    story.append(Paragraph("Pré-requisitos", s["h2"]))
    lista(story, s, [
        "Windows 10 ou 11 (64-bit)",
        "Automec instalado e funcionando com Firebird 5",
        "Acesso de <b>Administrador</b> no computador servidor",
        "Arquivo <b>Instalar-Invec.exe</b> fornecido pela Pontual Tecnologia",
        "Chave de <b>licença</b> fornecida pela Pontual Tecnologia",
        "Rede Wi-Fi que conecte o servidor aos celulares",
    ])

    story.append(Paragraph("Passo 1 — Executar o instalador", s["h2"]))
    story.append(Paragraph(
        "Clique com o botão direito no arquivo <b>Instalar-Invec.exe</b> e selecione "
        "<b>\"Executar como administrador\"</b>. Se aparecer o aviso do Windows (UAC), clique em Sim.",
        s["corpo"]))

    story.append(Paragraph("Passo 2 — Preencher as configurações", s["h2"]))
    story.append(Paragraph(
        "O instalador abrirá uma janela com os campos de configuração:", s["corpo"]))
    tabela(story,
        ["Campo", "O que preencher", "Exemplo"],
        [
            ["Banco de dados Firebird", "Caminho completo do arquivo .FDB do Automec", "C:\\Automec\\dados\\empresa.FDB"],
            ["Host Firebird", "Deixar localhost se o banco está na mesma máquina", "localhost"],
            ["Usuário Firebird", "Normalmente SYSDBA", "SYSDBA"],
            ["Senha Firebird", "Senha do Firebird (padrão: masterkey)", "masterkey"],
            ["Porta da API", "Porta TCP que o app usará para conectar", "8000"],
            ["JWT Secret", "Qualquer texto longo e aleatório (mínimo 32 caracteres)", "minha-chave-secreta-2026"],
            ["License Key", "Chave de licença fornecida pela Pontual Tecnologia", "eyJhbGciOiJSUzI1NiJ9..."],
        ],
        [4.5*cm, 6*cm, 5*cm],
    )
    story.append(Paragraph(
        "O caminho do banco pode ser encontrado nas configurações do Automec em "
        "Arquivo → Configurações → Banco de dados.", s["nota"]))

    story.append(Paragraph("Passo 3 — Clicar em \"Instalar / Atualizar\"", s["h2"]))
    story.append(Paragraph("O instalador irá automaticamente:", s["corpo"]))
    lista(story, s, [
        "Criar a pasta <b>C:\\Invec\\</b>",
        "Copiar o servidor para <b>C:\\Invec\\InvecServidor.exe</b>",
        "Gravar as configurações em <b>C:\\Invec\\.env</b>",
        "Registrar o serviço Windows <b>InvecAPI</b> (inicia com o Windows automaticamente)",
        "Abrir a porta configurada no Firewall do Windows",
        "Iniciar o servidor",
    ])
    story.append(Paragraph(
        "Ao final aparecerá a mensagem <b>\"Instalação concluída com sucesso\"</b>.",
        s["corpo"]))

    story.append(Paragraph("Passo 4 — Verificar se o servidor subiu", s["h2"]))
    story.append(Paragraph(
        "Abra o navegador no computador servidor e acesse:", s["corpo"]))
    story.append(Paragraph("http://localhost:8000/", s["code"]))
    story.append(Paragraph(
        "Deve aparecer: <font face=\"Courier\">{\"status\": \"ok\", \"versao\": \"1.0.0\"}</font>. "
        "Se aparecer erro, consulte o log em <b>C:\\Invec\\logs\\servico.log</b>.", s["corpo"]))

    story.append(Paragraph("Passo 5 — Descobrir o IP para os celulares", s["h2"]))
    story.append(Paragraph(
        "Abra o Prompt de Comando e digite <font face=\"Courier\">ipconfig</font>. "
        "Procure por <b>Endereço IPv4</b> na placa de rede da empresa. Exemplo: 192.168.1.31. "
        "O endereço que você vai configurar nos celulares será:", s["corpo"]))
    story.append(Paragraph("http://192.168.1.31:8000/", s["code"]))

    story.append(Paragraph("Quando é pedida a licença?", s["h2"]))
    story.append(Paragraph(
        "O servidor valida a licença toda vez que é iniciado. Se a licença estiver ausente, "
        "inválida ou expirada, o servidor <b>não sobe</b> e registra o erro no log. "
        "Nesse caso, entre em contato com a Pontual Tecnologia para obter ou renovar a chave de licença. "
        "A chave (<b>License Key</b>) precisa ser inserida no campo correspondente do instalador e "
        "o servidor reiniciado.", s["corpo"]))
    story.append(Paragraph(
        "Para verificar o erro de licença: abra C:\\Invec\\logs\\servico.log e procure por "
        "linhas com [LICENÇA].", s["nota"]))

    story.append(Paragraph("Instalar o app nos celulares", s["h2"]))
    story.append(Paragraph(
        "Copie o arquivo <b>app-release.apk</b> para o celular (via cabo USB, WhatsApp ou e-mail) "
        "e abra o arquivo no celular para instalar. Se o Android pedir permissão para instalar de "
        "fontes desconhecidas, aceite.", s["corpo"]))
    lista(story, s, [
        "No celular, abra o app Invec",
        "Na tela de login, preencha o campo <b>URL</b> com o endereço do servidor (ex: http://192.168.1.31:8000/)",
        "Toque em <b>Salvar servidor</b>",
        "Faça login com seu usuário do Automec",
    ])

    story.append(Paragraph("Atualizar o servidor (nova versão)", s["h2"]))
    story.append(Paragraph(
        "Quando receber um novo <b>Instalar-Invec.exe</b> da Pontual Tecnologia, execute-o novamente "
        "como Administrador e clique em <b>Instalar / Atualizar</b>. O serviço será parado, "
        "atualizado e reiniciado automaticamente, sem perda de dados.", s["corpo"]))

    story.append(Paragraph("Gerenciar o serviço manualmente", s["h2"]))
    story.append(Paragraph("Abra o Prompt de Comando como Administrador:", s["corpo"]))
    story.append(Paragraph(
        "net stop InvecAPI    ← para o servidor\n"
        "net start InvecAPI   ← inicia o servidor\n"
        "sc query InvecAPI    ← verifica o status", s["code"]))

    story.append(Paragraph("Solução de problemas comuns", s["h2"]))
    tabela(story,
        ["Problema", "Causa provável", "Solução"],
        [
            ["Servidor não sobe", "Licença inválida ou expirada", "Ver servico.log e contatar Pontual Tecnologia"],
            ["Servidor não sobe", "Caminho do banco errado", "Verificar C:\\Invec\\.env e reinstalar"],
            ["App não conecta", "IP errado no app", "Verificar IP com ipconfig e testar no navegador"],
            ["App não conecta", "Porta bloqueada no firewall", "Executar o instalador novamente"],
            ["Login recusado no app", "Usuário sem senha mobile", "Cadastrar senha mobile na tela Usuários"],
            ["Erro ao consolidar", "Banco Firebird fora do ar", "Verificar se o Automec está funcionando"],
        ],
        [4.5*cm, 4.5*cm, 6.5*cm],
    )

    story.append(PageBreak())

    # ── PARTE 2: USO DO APP ──────────────────
    story.append(Paragraph("PARTE 2 — USO DO APLICATIVO", s["h1"]))
    hr(story)

    story.append(Paragraph("Tela de Login", s["h2"]))
    story.append(Paragraph(
        "Na primeira utilização em um celular novo, preencha o campo <b>URL</b> com o endereço do "
        "servidor (ex: http://192.168.1.31:8000/) e toque em <b>Salvar servidor</b>. "
        "Em seguida, informe o <b>login</b> e a <b>senha mobile</b> cadastrados pelo administrador. "
        "A senha mobile é separada da senha do Automec e é configurada na tela de Usuários do app.",
        s["corpo"]))
    lista(story, s, [
        "Após <b>5 tentativas erradas</b>, o login fica bloqueado por <b>5 minutos</b>",
        "A sessão dura <b>8 horas</b> — após isso, é necessário fazer login novamente",
        "O app encerra a sessão automaticamente após <b>15 minutos sem uso</b>",
    ])

    story.append(Paragraph("Tela Inicial", s["h2"]))
    story.append(Paragraph(
        "Após o login, a tela inicial mostra o nome do usuário logado e permite:", s["corpo"]))
    lista(story, s, [
        "<b>Selecionar Depósito</b> — escolhe qual depósito será inventariado",
        "<b>Selecionar Operador</b> — define quem está fazendo a coleta física (pode ser diferente do usuário logado)",
        "<b>Iniciar Bipagem</b> — abre o scanner (só disponível após selecionar um depósito)",
        "<b>Relatório</b> — abre o relatório da sessão atual",
        "<b>Operadores</b> — gerenciar operadores de coleta (gerentes/admins)",
        "<b>Usuários</b> — gerenciar acesso mobile (apenas admin mobile)",
        "<b>Sair</b> — encerra a sessão",
    ])

    story.append(Paragraph("Tela de Scanner (Bipagem)", s["h2"]))
    story.append(Paragraph(
        "É a tela principal de coleta. Suporta dois modos de leitura:", s["corpo"]))
    tabela(story,
        ["Modo", "Como usar"],
        [
            ["Câmera", "Toque em Escanear e aponte a câmera para o código de barras. "
                       "Ative o switch Múltiplos para ler produtos em sequência sem tocar em Escanear a cada vez."],
            ["Bluetooth", "Conecte o leitor BT ao celular. O app captura o código automaticamente quando o leitor faz a leitura."],
            ["Manual", "Toque em Digitar código e informe o código de barras pelo teclado. Útil para códigos danificados."],
        ],
        [3.5*cm, 12*cm],
    )
    story.append(Paragraph(
        "Cada leitura soma 1 unidade ao produto. Se o mesmo código for bipado novamente, a quantidade "
        "acumula. Após cada scan, o painel inferior mostra o nome do produto e o total acumulado. "
        "O campo <b>Operador</b> trava após a primeira bipagem — escolha o operador correto antes de começar.",
        s["corpo"]))
    story.append(Paragraph(
        "Se a quantidade contada for mais de 2× o estoque do sistema, o app exibe um alerta pedindo confirmação.",
        s["nota"]))

    story.append(Paragraph("Tela de Relatório", s["h2"]))
    story.append(Paragraph(
        "Exibe todos os produtos bipados na sessão com três colunas:", s["corpo"]))
    tabela(story,
        ["Coluna", "O que significa"],
        [
            ["Sistema", "Quantidade registrada no Automec no momento do primeiro scan do produto"],
            ["Contada", "Total de unidades bipadas na sessão"],
            ["Dif", "Diferença entre Contada e Sistema. Verde = sobra, Vermelho = falta, Cinza = sem diferença"],
        ],
        [3.5*cm, 12*cm],
    )
    lista(story, s, [
        "<b>Toque em um produto</b> para editar a quantidade. Informe o motivo (obrigatório para auditoria)",
        "<b>Deslize um produto para a esquerda ou direita</b> para remover da contagem. Informe o motivo",
        "O aviso no topo informa quantos produtos com estoque positivo ainda não foram bipados",
        "O botão <b>Recontagem</b> fica verde quando há divergências, indicando que é recomendada",
        "O botão <b>Consolidar</b> fecha o inventário e atualiza o Automec",
    ])

    story.append(Paragraph("Tela de Recontagem", s["h2"]))
    story.append(Paragraph(
        "Permite fazer uma segunda contagem dos produtos para confirmar os valores antes de consolidar. "
        "O app mostra lado a lado a 1ª e a 2ª contagem de cada produto e destaca as diferenças.", s["corpo"]))
    story.append(Paragraph(
        "Ao finalizar, o app apresenta 4 opções:", s["corpo"]))
    tabela(story,
        ["Opção", "O que faz"],
        [
            ["Consolidar agora", "Aplica a 2ª contagem e consolida diretamente no Automec"],
            ["Aplicar 2ª contagem", "Atualiza os valores e volta ao relatório para revisão final"],
            ["Manter 1ª contagem", "Descarta a 2ª contagem e volta ao relatório com os valores originais"],
            ["Continuar recontando", "Fecha o diálogo e permite bipar mais produtos"],
        ],
        [4*cm, 11.5*cm],
    )

    story.append(Paragraph("Consolidação", s["h2"]))
    story.append(Paragraph(
        "A consolidação é a operação que grava os dados no Automec. <b>Não pode ser desfeita.</b>",
        s["aviso"]))
    story.append(Paragraph(
        "Ao tocar em <b>Consolidar</b>, o app exibe um resumo com o total de itens e a quantidade de "
        "divergências encontradas:", s["corpo"]))
    lista(story, s, [
        "<b>Sem divergências:</b> toque em Consolidar agora. Nenhum supervisor necessário.",
        "<b>Com divergências:</b> informe o <b>login e senha mobile de um gerente ou administrador</b> para autorizar.",
        "<b>Se mais de 30% dos itens divergirem:</b> o app bloqueia a consolidação e exige recontagem antes.",
    ])
    story.append(Paragraph(
        "Operadores precisam de um gerente ou admin diferente para autorizar. "
        "Gerentes e admins podem autorizar com as próprias credenciais.", s["nota"]))

    story.append(Paragraph("Tela de Histórico", s["h2"]))
    story.append(Paragraph(
        "Mostra todas as consolidações realizadas para o depósito selecionado, com produto, "
        "quantidade contada, quantidade do sistema e data.", s["corpo"]))

    story.append(Paragraph("Tela de Auditoria", s["h2"]))
    story.append(Paragraph(
        "Disponível apenas para gerentes e administradores. Exibe o log completo de operações:", s["corpo"]))
    tabela(story,
        ["Tipo de evento", "O que significa"],
        [
            ["EDICAO", "Quantidade de um produto foi editada manualmente"],
            ["EDICAO_SUSPEITA", "Edição fez o valor coincidir exatamente com o estoque do sistema"],
            ["EXCLUSAO", "Item removido da contagem"],
            ["CONSOLIDACAO", "Inventário consolidado no Automec"],
            ["ALERTA", "Quantidade bipada muito acima do estoque esperado"],
            ["ALERTA_REESCAN", "Produto excluído e re-escaneado na mesma sessão (possível fraude)"],
        ],
        [4.5*cm, 11*cm],
    )

    story.append(Paragraph("Tela de Operadores", s["h2"]))
    story.append(Paragraph(
        "Gerentes e administradores podem cadastrar e ativar/desativar os operadores de coleta. "
        "Operadores são as pessoas que fazem a bipagem física — aparecem na lista de seleção "
        "antes do início da contagem.", s["corpo"]))

    story.append(Paragraph("Tela de Usuários", s["h2"]))
    story.append(Paragraph(
        "Disponível apenas para o <b>admin mobile</b> (usuário MI e delegados). Permite:", s["corpo"]))
    lista(story, s, [
        "<b>Definir senha mobile</b> — cada usuário precisa de uma senha mobile separada para acessar o app",
        "<b>Dar/remover admin mobile</b> — delega a outro usuário a capacidade de gerenciar senhas e acessos",
    ])

    doc.build(story)
    print(f"Manual gerado: {caminho}")


# ─────────────────────────────────────────────
# DOCUMENTAÇÃO TÉCNICA
# ─────────────────────────────────────────────

def gerar_tecnico(caminho):
    doc = SimpleDocTemplate(caminho, pagesize=A4,
        leftMargin=MARGEM, rightMargin=MARGEM,
        topMargin=MARGEM, bottomMargin=MARGEM,
        title="Invec — Documentação Técnica")
    s = estilos()
    story = []

    capa(story, s, "Documentação Técnica",
         "Arquitetura, endpoints, banco de dados e segurança")

    story.append(Paragraph("Visão Geral", s["h1"]))
    hr(story)
    story.append(Paragraph(
        "O Invec é composto por dois componentes: um <b>backend FastAPI</b> (Python) que se conecta "
        "ao banco Firebird do Automec, e um <b>app Android</b> (Kotlin) que se comunica com o backend "
        "via HTTP/JSON pelo Wi-Fi da empresa.", s["corpo"]))
    story.append(Paragraph(
        "[Celular Android]  ──Wi-Fi──  [InvecServidor.exe]  ──  [Firebird / Automec]", s["code"]))
    story.append(Paragraph(
        "O servidor roda como serviço Windows (InvecAPI via NSSM). Vários celulares podem operar "
        "simultaneamente no mesmo depósito — as escritas no banco são atômicas para evitar condições de corrida.",
        s["corpo"]))

    story.append(Paragraph("Stack Tecnológica", s["h1"]))
    hr(story)
    tabela(story,
        ["Componente", "Tecnologia", "Versão"],
        [
            ["Backend", "Python + FastAPI + Uvicorn", "Python 3.13, FastAPI 0.115+"],
            ["Banco de dados", "Firebird 5 via firebird-driver", "Firebird 5.0"],
            ["App mobile", "Android Kotlin", "Min SDK 26 (Android 8.0)"],
            ["HTTP client (app)", "Retrofit2 + OkHttp3", "Retrofit 2.11+"],
            ["Câmera", "CameraX + ML Kit Barcode", "CameraX 1.3+"],
            ["UI", "Material Design 3 + ViewBinding", "Material 1.12+"],
            ["Autenticação", "JWT HS256", "python-jose 3.3+"],
            ["Licença", "JWT RS256 (RSA 2048-bit)", "cryptography 41+"],
            ["Distribuição servidor", "PyInstaller + NSSM", "PyInstaller 6+"],
        ],
        [4*cm, 6*cm, 5.5*cm],
    )

    story.append(Paragraph("Estrutura do Projeto", s["h1"]))
    hr(story)
    story.append(Paragraph("Backend (api/)", s["h2"]))
    story.append(Paragraph(
        "api/main.py          ← FastAPI app, lifespan (licença + migrations)\n"
        "api/server.py        ← entrypoint Uvicorn para PyInstaller\n"
        "api/app/database.py  ← get_connection() context manager\n"
        "api/app/security.py  ← JWT HS256, get_current_user()\n"
        "api/app/licenca.py   ← validação RSA 2048-bit\n"
        "api/app/migrations.py← DDL idempotente na inicialização\n"
        "api/app/models/schemas.py  ← modelos Pydantic\n"
        "api/app/routers/\n"
        "  auth.py            ← login, rate limit, usuários mobile\n"
        "  depositos.py       ← listagem de depósitos\n"
        "  produtos.py        ← busca por código de barras\n"
        "  inventario.py      ← bipagem, relatório, consolidação, auditoria\n"
        "  operadores.py      ← CRUD de operadores físicos", s["code"]))

    story.append(Paragraph("App Android (app/)", s["h2"]))
    story.append(Paragraph(
        "ui/base/TimeoutActivity.kt  ← base com timeout de inatividade 15min\n"
        "ui/login/LoginActivity.kt   ← autenticação\n"
        "ui/main/MainActivity.kt     ← seleção de depósito e operador\n"
        "ui/scanner/ScannerActivity.kt ← bipagem câmera + Bluetooth\n"
        "ui/relatorio/RelatorioActivity.kt ← relatório, edição, consolidação\n"
        "ui/recontagem/RecontagemActivity.kt ← segunda contagem\n"
        "ui/historico/HistoricoActivity.kt ← histórico de consolidações\n"
        "ui/auditoria/AuditoriaActivity.kt ← log de auditoria\n"
        "ui/operadores/OperadoresActivity.kt ← gestão de operadores\n"
        "ui/usuarios/UsuariosActivity.kt ← gestão de acesso mobile\n"
        "data/api/ApiService.kt      ← endpoints Retrofit\n"
        "data/api/RetrofitClient.kt  ← OkHttp + interceptor 401\n"
        "data/model/Models.kt        ← data classes request/response\n"
        "util/SessionManager.kt      ← SharedPreferences (token, depósito, etc.)", s["code"]))

    story.append(Paragraph("Autenticação e Sessão", s["h1"]))
    hr(story)
    story.append(Paragraph(
        "O login é feito via POST /auth/login com login e senha. O backend verifica em USUARIOS "
        "comparando com SENHAMOBILE (coluna adicionada pelo Invec) ou SENHA (senha original do Automec). "
        "Em caso de sucesso, retorna um JWT HS256 assinado com JWT_SECRET.", s["corpo"]))
    story.append(Paragraph(
        "O token contém: sub (IDUSUARIO), login, role (operador/gerente/admin), "
        "idgrupo (1=admin, 2=gerente, 3=operador) e mobile_admin.", s["code"]))
    lista(story, s, [
        "<b>Expiração:</b> 8 horas — configurável em security.py",
        "<b>Inatividade:</b> 15 minutos — implementado em TimeoutActivity via Handler/Runnable",
        "<b>Rate limit:</b> 5 tentativas em 60 segundos → bloqueio de 300 segundos, por IP e por usuário",
        "<b>Interceptor 401:</b> OkHttp detecta token expirado e redireciona automaticamente para LoginActivity",
    ])

    story.append(Paragraph("Sistema de Licença RSA", s["h1"]))
    hr(story)
    story.append(Paragraph(
        "A licença é um JWT RS256 gerado com a chave privada RSA 2048-bit "
        "(licenca_privada.pem — uso exclusivo Pontual Tecnologia). "
        "O servidor embute a chave pública em app/licenca.py e valida o token na inicialização. "
        "Se a licença for inválida ou expirada, o servidor encerra com sys.exit(1).", s["corpo"]))
    story.append(Paragraph(
        "Campos do JWT de licença: cliente (nome), cnpj, emitido_em, expira_em (vazio = permanente).",
        s["nota"]))

    story.append(Paragraph("Banco de Dados", s["h1"]))
    hr(story)
    story.append(Paragraph("Tabelas do Automec utilizadas", s["h2"]))
    tabela(story,
        ["Tabela", "Operação", "Observação"],
        [
            ["USUARIOS", "SELECT + UPDATE", "Colunas SENHAMOBILE e MOBILE_ADMIN adicionadas pelo Invec"],
            ["DEPOSITO", "SELECT", "Listagem de depósitos disponíveis"],
            ["PRODUTO + PRODUTO_CODBARRA", "SELECT", "Busca por código de barras (primary e secondary)"],
            ["MOVIMENTO", "SELECT", "QTDEATUAL por produto e depósito"],
            ["MOV_PRODUTO", "INSERT + SELECT", "Consolidação: TIPOMOVIMENTO=5, trigger atualiza MOVIMENTO"],
            ["SAIDAPRODUTO + SAIDAESTOQUE", "SELECT", "CE (Considerar Entrega) — pedidos pendentes de saída"],
            ["PRODUTOPRECO", "SELECT", "FATORCONV e VLCUSTO para cálculo do MOV_PRODUTO"],
        ],
        [3.8*cm, 2.8*cm, 9*cm],
    )
    story.append(Paragraph("Tabelas criadas pelo Invec", s["h2"]))
    tabela(story,
        ["Tabela", "Função"],
        [
            ["INVENTARIO_TEMP", "Armazena a sessão de contagem em andamento. Contém QTDEATUAL_SNAP "
                               "(snapshot do estoque no momento do 1º scan) e OPERADOR."],
            ["OPERADORES_APP", "Cadastro de operadores físicos de coleta (separado dos usuários do Automec)."],
            ["LOG_INVENTARIO", "Auditoria completa: TIPO, CDDEPOSITO, CDPRODUTO, PRODUTO, OPERADOR, "
                              "LOGIN_USUARIO, QTDE_ANTES, QTDE_DEPOIS, MOTIVO, DEVICE_ID, DATA_HORA."],
        ],
        [4*cm, 11.5*cm],
    )

    story.append(Paragraph("Fluxo de Bipagem", s["h1"]))
    hr(story)
    story.append(Paragraph(
        "Cada scan faz um POST /inventario/bipagem. O backend executa um UPDATE atômico com RETURNING "
        "para evitar race condition quando dois celulares bipam o mesmo produto simultaneamente:", s["corpo"]))
    story.append(Paragraph(
        "UPDATE INVENTARIO_TEMP SET QTDE = QTDE + ?, OPERADOR = ?\n"
        "WHERE CDPRODUTO = ? AND CDDEPOSITO = ? RETURNING QTDE", s["code"]))
    story.append(Paragraph(
        "Se o UPDATE retornar 0 linhas (primeiro scan do produto), executa um INSERT com o snapshot "
        "do estoque atual (QTDEATUAL_SNAP). O snapshot é tirado uma única vez — no momento do primeiro "
        "scan — e não é atualizado em scans subsequentes. Isso garante que o relatório e a consolidação "
        "usem o mesmo valor de referência independente de movimentações que ocorram entre o scan e a consolidação.",
        s["corpo"]))

    story.append(Paragraph("Fluxo de Consolidação", s["h1"]))
    hr(story)
    lista(story, s, [
        "Busca todos os itens de INVENTARIO_TEMP para o depósito",
        "Consulta pedidos pendentes em SAIDAPRODUTO (CE — Considerar Entrega). Envolvido em try/except "
        "para compatibilidade com versões antigas do Automec sem essas tabelas",
        "Calcula divergências: compara qtde_contada com qtde_atual + qtdeentrega",
        "Se divergências ≥ 30% e ≥ 5 itens: lança HTTP 422 — recontagem obrigatória",
        "Se há divergências: valida credenciais do supervisor (gerente/admin diferente do operador)",
        "Gera IDINVENTARIO via GEN_ID(GEN_MOV_PRODUTO, 1)",
        "Para cada item: INSERT em MOV_PRODUTO com TIPOMOVIMENTO=5. O trigger TG_INSERT_MOV_PRODUTO "
        "do Automec atualiza MOVIMENTO.QTDEATUAL automaticamente",
        "DELETE FROM INVENTARIO_TEMP para o depósito (mesma transação)",
        "Grava CONSOLIDACAO no LOG_INVENTARIO e salva relatório .txt em C:\\Invec\\relatorios\\",
    ])
    story.append(Paragraph(
        "O lock _consolidando (threading.Lock + set) impede que dois celulares consolidem o mesmo "
        "depósito simultaneamente.", s["nota"]))

    story.append(Paragraph("Considerar Entrega (CE)", s["h1"]))
    hr(story)
    story.append(Paragraph(
        "Quando há pedidos de saída pendentes (faturados mas ainda não entregues), o estoque real "
        "do depósito é: QTDEATUAL + QTDEENTREGA. O Invec considera isso tanto no cálculo de divergências "
        "quanto na consolidação, usando a mesma fórmula do Automec (GravarMov_Produto_Entrega):", s["corpo"]))
    tabela(story,
        ["Situação", "QTENTRADA", "QTSAIDA", "VL_PERDA_GANHO"],
        [
            ["Com entrega pendente e contado > atual", "contado − atual", "qtdeentrega", "NULL (Automec calcula)"],
            ["Com entrega pendente e contado < atual", "0", "(atual − contado) + qtdeentrega", "NULL"],
            ["Com entrega pendente e contado = atual", "0", "qtdeentrega", "NULL"],
            ["Sem entrega e contado > atual", "contado − atual", "0", "(contado − atual) × vlcusto"],
            ["Sem entrega e contado < atual", "0", "atual − contado", "(contado − atual) × vlcusto"],
            ["Sem entrega e contado = atual", "0", "0", "0"],
        ],
        [5*cm, 3*cm, 3.5*cm, 4*cm],
    )

    story.append(Paragraph("Endpoints Completos", s["h1"]))
    hr(story)
    tabela(story,
        ["Método", "Rota", "Descrição", "Acesso"],
        [
            ["POST", "/auth/login", "Login com rate limit", "Público"],
            ["GET", "/auth/usuarios", "Lista usuários mobile", "Admin mobile"],
            ["PUT", "/auth/usuarios/{id}/senha-mobile", "Define senha mobile", "Admin mobile"],
            ["PUT", "/auth/usuarios/{id}/toggle-admin", "Alterna admin mobile", "Usuário MI"],
            ["GET", "/depositos", "Lista depósitos Firebird", "Autenticado"],
            ["GET", "/produtos/barcode/{codigo}", "Busca por código de barras", "Autenticado"],
            ["GET", "/produtos/busca", "Busca por descrição", "Autenticado"],
            ["POST", "/inventario/bipagem", "Registra scan (atômico)", "Autenticado"],
            ["GET", "/inventario/relatorio/{dep}", "Relatório da sessão", "Autenticado"],
            ["GET", "/inventario/resumo/{dep}", "Produtos não contados", "Autenticado"],
            ["POST", "/inventario/consolidar", "Consolida no Automec", "Autenticado"],
            ["PUT", "/inventario/bipagem/{id}", "Edita quantidade (auditado)", "Autenticado"],
            ["DELETE", "/inventario/bipagem/{id}", "Remove item (auditado)", "Autenticado"],
            ["GET", "/inventario/historico/{dep}", "Histórico de consolidações", "Autenticado"],
            ["GET", "/inventario/log/{dep}", "Log de auditoria", "Gerente/Admin"],
            ["GET", "/operadores", "Lista operadores de coleta", "Autenticado"],
            ["POST", "/operadores", "Cria operador", "Gerente/Admin"],
            ["PUT", "/operadores/{id}/toggle", "Ativa/desativa operador", "Gerente/Admin"],
        ],
        [1.8*cm, 5.5*cm, 6*cm, 3*cm],
    )

    story.append(Paragraph("Segurança e Auditoria", s["h1"]))
    hr(story)
    tabela(story,
        ["Mecanismo", "Implementação"],
        [
            ["Rate limit de login", "5 falhas em 60s → bloqueio 300s, por IP e por usuário (dicts em memória)"],
            ["Supervisor obrigatório", "Divergências → gerente/admin diferente do operador deve autorizar com senha mobile"],
            ["EDICAO_SUSPEITA", "Detecta quando edição faz a contagem coincidir exatamente com o estoque do sistema"],
            ["ALERTA_REESCAN", "Detecta produto excluído da contagem e re-escaneado na mesma sessão (janela 12h)"],
            ["ALERTA de quantidade", "Quantidade > 2× estoque e estoque ≥ 10 un gera alerta e aviso no app"],
            ["device_id", "ID único por instalação do app, gravado em todos os eventos do LOG_INVENTARIO"],
            ["Retenção de logs", "BIPAGEM: 90 dias. Geral: 365 dias. EDICAO_SUSPEITA e ALERTA_REESCAN: permanente"],
        ],
        [4.5*cm, 11*cm],
    )

    story.append(Paragraph("Migrations Automáticas", s["h1"]))
    hr(story)
    story.append(Paragraph(
        "Na inicialização, run_migrations() executa DDL idempotente (verifica antes de criar). "
        "Isso permite atualizar o servidor sem scripts manuais de banco:", s["corpo"]))
    lista(story, s, [
        "Cria OPERADORES_APP se não existir",
        "Adiciona coluna OPERADOR em INVENTARIO_TEMP e INVENTARIO se não existir",
        "Adiciona coluna QTDEATUAL_SNAP em INVENTARIO_TEMP se não existir",
        "Adiciona coluna MOBILE_ADMIN em USUARIOS se não existir",
        "Cria LOG_INVENTARIO se não existir",
        "Cria índices IDX_LOG_INV_DEPOSITO, IDX_LOG_INV_DATA, IDX_INVTEMP_PROD_DEP, IDX_LOG_INV_TIPO",
        "Remove logs antigos conforme política de retenção",
        "Remove relatórios .txt com mais de 180 dias",
    ])

    story.append(Paragraph("Build e Distribuição", s["h1"]))
    hr(story)
    story.append(Paragraph("Servidor", s["h2"]))
    story.append(Paragraph(
        "cd api\n"
        "pyinstaller servidor.spec --clean --noconfirm   → dist/InvecServidor.exe\n"
        "pyinstaller instalador.spec --clean --noconfirm → dist/Instalar-Invec.exe", s["code"]))
    story.append(Paragraph(
        "O instalador.spec bundla InvecServidor.exe + nssm.exe em um único executável GUI. "
        "O cliente recebe apenas Instalar-Invec.exe — sem Python, sem dependências extras.",
        s["corpo"]))
    story.append(Paragraph("App Android", s["h2"]))
    story.append(Paragraph(
        ".\\gradlew assembleRelease\n"
        "# → app/build/outputs/apk/release/app-release.apk", s["code"]))
    story.append(Paragraph(
        "O build usa R8/ProGuard para minificação e ofuscação. O APK é assinado com a keystore "
        "em app/release/ (não commitada no git).", s["corpo"]))

    doc.build(story)
    print(f"Técnico gerado: {caminho}")


if __name__ == "__main__":
    out = os.path.dirname(os.path.abspath(__file__))
    gerar_manual(os.path.join(out, "Invec_Manual.pdf"))
    gerar_tecnico(os.path.join(out, "Invec_Tecnico.pdf"))
    print("Concluído.")
