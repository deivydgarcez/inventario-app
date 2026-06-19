"""Gera os PDFs de documentação do Invec usando ReportLab."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Preformatted,
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

    s["corpo"] = ParagraphStyle("corpo",
        fontName="Helvetica", fontSize=9.5, textColor=PRETO,
        leading=16, spaceAfter=6, alignment=TA_JUSTIFY)

    s["corpo_cel"] = ParagraphStyle("corpo_cel",
        fontName="Helvetica", fontSize=8.5, textColor=PRETO,
        leading=14, spaceAfter=0, wordWrap="LTR")

    s["header_cel"] = ParagraphStyle("header_cel",
        fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.white,
        leading=14, spaceAfter=0, wordWrap="LTR")

    s["nota"] = ParagraphStyle("nota",
        fontName="Helvetica-Oblique", fontSize=8.5, textColor=CINZA_TEXTO,
        leading=14, spaceAfter=4)

    s["aviso"] = ParagraphStyle("aviso",
        fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#B71C1C"),
        leading=14, spaceAfter=4)

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
    story.append(Paragraph(versao + "  -  2026", s["nota"]))
    story.append(PageBreak())


def hr(story):
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=0.5, color=CINZA_BORDA))
    story.append(Spacer(1, 6))


def code(story, texto):
    """Bloco de código com fonte monoespaçada e fundo cinza."""
    pre = Preformatted(texto, ParagraphStyle("pre",
        fontName="Courier", fontSize=8, textColor=PRETO,
        leading=13, leftIndent=10, rightIndent=10,
        backColor=CINZA_CLARO, borderPadding=(6, 8, 6, 8),
        spaceAfter=6))
    story.append(pre)


def cel(texto, s, bold=False):
    """Converte texto em Paragraph para célula de tabela (com quebra de linha automática)."""
    estilo = s["header_cel"] if bold else s["corpo_cel"]
    return Paragraph(str(texto), estilo)


def tabela(story, s, cabecalho, linhas, col_widths):
    data = [[cel(h, s, bold=True) for h in cabecalho]] + \
           [[cel(c, s) for c in linha] for linha in linhas]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LARANJA),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CINZA_CLARO]),
        ("GRID", (0, 0), (-1, -1), 0.3, CINZA_BORDA),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
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
        title="Invec - Manual de Instalacao e Uso")
    s = estilos()
    story = []

    capa(story, s, "Manual de Instalacao e Uso",
         "Guia completo para instalacao do servidor e uso do aplicativo")

    # ── PARTE 1: INSTALAÇÃO ──────────────────
    story.append(Paragraph("PARTE 1 - INSTALACAO DO SERVIDOR", s["h1"]))
    hr(story)

    story.append(Paragraph("O que e o servidor Invec", s["h2"]))
    story.append(Paragraph(
        "O Invec funciona em dois componentes: o <b>servidor</b> (instalado no computador da loja) "
        "e o <b>aplicativo</b> (instalado nos celulares Android). O servidor e quem se conecta ao "
        "banco de dados do Automec e processa todas as operacoes. Os celulares se comunicam com o "
        "servidor pelo Wi-Fi da empresa.", s["corpo"]))

    story.append(Paragraph("Pre-requisitos", s["h2"]))
    lista(story, s, [
        "Windows 10 ou 11 (64-bit)",
        "Automec instalado e funcionando com Firebird 5",
        "Acesso de <b>Administrador</b> no computador servidor",
        "Arquivo <b>Instalar-Invec.exe</b> fornecido pela Pontual Tecnologia",
        "Chave de <b>licenca</b> fornecida pela Pontual Tecnologia",
        "Rede Wi-Fi que conecte o servidor aos celulares",
    ])

    story.append(Paragraph("Passo 1 - Executar o instalador", s["h2"]))
    story.append(Paragraph(
        "Clique com o botao direito no arquivo <b>Instalar-Invec.exe</b> e selecione "
        "<b>Executar como administrador</b>. Se aparecer o aviso do Windows (UAC), clique em Sim.",
        s["corpo"]))

    story.append(Paragraph("Passo 2 - Preencher as configuracoes", s["h2"]))
    story.append(Paragraph("O instalador abrira uma janela com os campos de configuracao:", s["corpo"]))
    tabela(story, s,
        ["Campo", "O que preencher", "Exemplo"],
        [
            ["Banco de dados Firebird", "Caminho completo do arquivo .FDB do Automec", r"C:\Automec\dados\empresa.FDB"],
            ["Host Firebird", "Deixar localhost se o banco esta na mesma maquina", "localhost"],
            ["Usuario Firebird", "Normalmente SYSDBA", "SYSDBA"],
            ["Senha Firebird", "Senha do Firebird (padrao: masterkey)", "masterkey"],
            ["Porta da API", "Porta TCP que o app usara para conectar", "8000"],
            ["JWT Secret", "Texto longo e aleatorio (minimo 32 caracteres)", "minha-chave-secreta-2026"],
            ["License Key", "Chave de licenca fornecida pela Pontual Tecnologia", "eyJhbGciOiJSUzI1NiJ9..."],
        ],
        [4*cm, 5.5*cm, 5.5*cm],
    )
    story.append(Paragraph(
        "O caminho do banco pode ser encontrado nas configuracoes do Automec em "
        "Arquivo > Configuracoes > Banco de dados.", s["nota"]))

    story.append(Paragraph('Passo 3 - Clicar em "Instalar / Atualizar"', s["h2"]))
    story.append(Paragraph("O instalador ira automaticamente:", s["corpo"]))
    lista(story, s, [
        r"Criar a pasta C:\Invec\\",
        r"Copiar o servidor para C:\Invec\InvecServidor.exe",
        r"Gravar as configuracoes em C:\Invec\.env",
        "Registrar o servico Windows <b>InvecAPI</b> (inicia com o Windows automaticamente)",
        "Abrir a porta configurada no Firewall do Windows",
        "Iniciar o servidor",
    ])
    story.append(Paragraph(
        'Ao final aparecera a mensagem <b>"Instalacao concluida com sucesso"</b>.', s["corpo"]))

    story.append(Paragraph("Passo 4 - Verificar se o servidor subiu", s["h2"]))
    story.append(Paragraph(
        "Abra o navegador no computador servidor e acesse:", s["corpo"]))
    code(story, "http://localhost:8000/")
    story.append(Paragraph(
        'Deve aparecer: {"status": "ok", "versao": "1.0.0"}. '
        r"Se aparecer erro, consulte o log em C:\Invec\logs\servico.log.", s["corpo"]))

    story.append(Paragraph("Passo 5 - Descobrir o IP para os celulares", s["h2"]))
    story.append(Paragraph(
        "Abra o Prompt de Comando e digite <b>ipconfig</b>. "
        "Procure por <b>Endereco IPv4</b> na placa de rede da empresa (ex: 192.168.1.31). "
        "O endereco que voce vai configurar nos celulares sera:", s["corpo"]))
    code(story, "http://192.168.1.31:8000/")

    story.append(Paragraph("Quando e pedida a licenca?", s["h2"]))
    story.append(Paragraph(
        "O servidor valida a licenca toda vez que e iniciado. Se a licenca estiver ausente, "
        "invalida ou expirada, o servidor <b>nao sobe</b> e registra o erro no log. "
        "Nesse caso, entre em contato com a Pontual Tecnologia para obter ou renovar a chave. "
        "A chave (<b>License Key</b>) precisa ser inserida no campo correspondente do instalador "
        "e o servidor reiniciado.", s["corpo"]))
    story.append(Paragraph(
        r"Para verificar o erro de licenca: abra C:\Invec\logs\servico.log e procure por "
        "linhas com [LICENCA].", s["nota"]))

    story.append(Paragraph("Instalar o app nos celulares", s["h2"]))
    story.append(Paragraph(
        "Copie o arquivo <b>app-release.apk</b> para o celular (via cabo USB, WhatsApp ou e-mail) "
        "e abra o arquivo no celular para instalar. Se o Android pedir permissao para instalar de "
        "fontes desconhecidas, aceite.", s["corpo"]))
    lista(story, s, [
        "No celular, abra o app Invec",
        "Na tela de login, preencha o campo <b>URL</b> com o endereco do servidor (ex: http://192.168.1.31:8000/)",
        "Toque em <b>Salvar servidor</b>",
        "Faca login com seu usuario",
    ])

    story.append(Paragraph("Atualizar o servidor (nova versao)", s["h2"]))
    story.append(Paragraph(
        "Quando receber um novo <b>Instalar-Invec.exe</b> da Pontual Tecnologia, execute-o novamente "
        "como Administrador e clique em <b>Instalar / Atualizar</b>. O servico sera parado, "
        "atualizado e reiniciado automaticamente, sem perda de dados.", s["corpo"]))

    story.append(Paragraph("Gerenciar o servico manualmente", s["h2"]))
    story.append(Paragraph("Abra o Prompt de Comando como Administrador:", s["corpo"]))
    code(story,
        "net stop InvecAPI    # para o servidor\n"
        "net start InvecAPI   # inicia o servidor\n"
        "sc query InvecAPI    # verifica o status")

    story.append(Paragraph("Solucao de problemas comuns", s["h2"]))
    tabela(story, s,
        ["Problema", "Causa provavel", "Solucao"],
        [
            ["Servidor nao sobe", "Licenca invalida ou expirada", "Ver servico.log e contatar Pontual Tecnologia"],
            ["Servidor nao sobe", "Caminho do banco errado", r"Verificar C:\Invec\.env e reinstalar"],
            ["App nao conecta", "IP errado no app", "Verificar IP com ipconfig e testar no navegador"],
            ["App nao conecta", "Porta bloqueada no firewall", "Executar o instalador novamente"],
            ["Login recusado no app", "Usuario sem senha mobile", "Cadastrar senha mobile na tela Usuarios"],
            ["Erro ao consolidar", "Banco Firebird fora do ar", "Verificar se o Automec esta funcionando"],
        ],
        [4*cm, 4.5*cm, 6.5*cm],
    )

    story.append(PageBreak())

    # ── PARTE 2: USO DO APP ──────────────────
    story.append(Paragraph("PARTE 2 - USO DO APLICATIVO", s["h1"]))
    hr(story)

    story.append(Paragraph("Tela de Login", s["h2"]))
    story.append(Paragraph(
        "Na primeira utilizacao em um celular novo, preencha o campo <b>URL</b> com o endereco do "
        "servidor (ex: http://192.168.1.31:8000/) e toque em <b>Salvar servidor</b>. "
        "Em seguida, informe o <b>login</b> e a <b>senha mobile</b> cadastrados pelo administrador. "
        "A senha mobile e separada da senha do Automec e e configurada na tela de Usuarios do app.",
        s["corpo"]))
    lista(story, s, [
        "Apos <b>5 tentativas erradas</b>, o login fica bloqueado por <b>5 minutos</b>",
        "A sessao dura <b>8 horas</b> - apos isso, e necessario fazer login novamente",
        "O app encerra a sessao automaticamente apos <b>15 minutos sem uso</b>",
    ])

    story.append(Paragraph("Tela Inicial", s["h2"]))
    story.append(Paragraph(
        "Apos o login, a tela inicial mostra o nome do usuario logado e permite:", s["corpo"]))
    lista(story, s, [
        "<b>Selecionar Deposito</b> - escolhe qual deposito sera inventariado",
        "<b>Selecionar Operador</b> - define quem esta fazendo a coleta fisica",
        "<b>Iniciar Bipagem</b> - abre o scanner (so disponivel apos selecionar um deposito)",
        "<b>Relatorio</b> - abre o relatorio da sessao atual",
        "<b>Operadores</b> - gerenciar operadores de coleta (gerentes/admins)",
        "<b>Usuarios</b> - gerenciar acesso mobile (apenas admin mobile)",
        "<b>Sair</b> - encerra a sessao",
    ])

    story.append(Paragraph("Tela de Scanner (Bipagem)", s["h2"]))
    story.append(Paragraph(
        "E a tela principal de coleta. Suporta tres modos de leitura:", s["corpo"]))
    tabela(story, s,
        ["Modo", "Como usar"],
        [
            ["Camera", "Toque em Escanear e aponte a camera para o codigo de barras. Ative o switch Multiplos para ler em sequencia sem tocar em Escanear a cada produto."],
            ["Bluetooth", "Conecte o leitor BT ao celular pelo Bluetooth do Android. O app captura o codigo automaticamente quando o leitor faz a leitura."],
            ["Manual", "Toque em Digitar codigo e informe o codigo pelo teclado. Util para codigos de barras danificados."],
        ],
        [3.5*cm, 12*cm],
    )
    story.append(Paragraph(
        "Cada leitura soma 1 unidade ao produto. Se o mesmo codigo for bipado varias vezes, "
        "a quantidade acumula. O campo <b>Operador</b> trava apos a primeira bipagem - "
        "escolha o operador correto antes de comecar.", s["corpo"]))
    story.append(Paragraph(
        "Se a quantidade contada for mais de 2x o estoque do sistema, o app exibe um alerta pedindo confirmacao.",
        s["nota"]))

    story.append(Paragraph("Tela de Relatorio", s["h2"]))
    story.append(Paragraph(
        "Exibe todos os produtos bipados na sessao com tres colunas:", s["corpo"]))
    tabela(story, s,
        ["Coluna", "O que significa"],
        [
            ["Sistema", "Quantidade registrada no Automec no momento do primeiro scan do produto"],
            ["Contada", "Total de unidades bipadas na sessao"],
            ["Dif", "Diferenca entre Contada e Sistema. Verde = sobra, Vermelho = falta, Cinza = sem diferenca"],
        ],
        [3.5*cm, 12*cm],
    )
    lista(story, s, [
        "<b>Toque em um produto</b> para editar a quantidade (motivo obrigatorio para auditoria)",
        "<b>Deslize o produto</b> para a esquerda ou direita para remover da contagem (motivo obrigatorio)",
        "O aviso no topo informa quantos produtos com estoque positivo ainda nao foram bipados",
        "O botao <b>Recontagem</b> fica verde quando ha divergencias",
        "O botao <b>Consolidar</b> fecha o inventario e atualiza o Automec",
    ])

    story.append(Paragraph("Tela de Recontagem", s["h2"]))
    story.append(Paragraph(
        "Permite fazer uma segunda contagem para confirmar os valores antes de consolidar. "
        "O app mostra a 1a e a 2a contagem lado a lado e destaca as diferencas.", s["corpo"]))
    story.append(Paragraph("Ao finalizar, o app apresenta 4 opcoes:", s["corpo"]))
    tabela(story, s,
        ["Opcao", "O que faz"],
        [
            ["Consolidar agora", "Aplica a 2a contagem e consolida diretamente no Automec"],
            ["Aplicar 2a contagem", "Atualiza os valores e volta ao relatorio para revisao final"],
            ["Manter 1a contagem", "Descarta a 2a contagem e volta ao relatorio com os valores originais"],
            ["Continuar recontando", "Fecha o dialogo e permite bipar mais produtos"],
        ],
        [4.5*cm, 11*cm],
    )

    story.append(Paragraph("Consolidacao", s["h2"]))
    story.append(Paragraph(
        "A consolidacao e a operacao que grava os dados no Automec. <b>Nao pode ser desfeita.</b>",
        s["aviso"]))
    story.append(Paragraph(
        "Ao tocar em <b>Consolidar</b>, o app exibe um resumo com o total de itens e a quantidade "
        "de divergencias encontradas:", s["corpo"]))
    lista(story, s, [
        "<b>Sem divergencias:</b> toque em Consolidar agora. Nenhum supervisor necessario.",
        "<b>Com divergencias:</b> informe o login e senha mobile de um <b>gerente ou administrador</b> para autorizar.",
        "<b>Se mais de 30% dos itens divergirem:</b> o app bloqueia e exige recontagem antes.",
    ])
    story.append(Paragraph(
        "Operadores precisam de um gerente ou admin diferente para autorizar. "
        "Gerentes e admins podem autorizar com as proprias credenciais.", s["nota"]))

    story.append(Paragraph("Tela de Historico", s["h2"]))
    story.append(Paragraph(
        "Mostra todas as consolidacoes realizadas para o deposito selecionado, com produto, "
        "quantidade contada, quantidade do sistema e data.", s["corpo"]))

    story.append(Paragraph("Tela de Auditoria", s["h2"]))
    story.append(Paragraph(
        "Disponivel apenas para gerentes e administradores. Exibe o log completo de operacoes:",
        s["corpo"]))
    tabela(story, s,
        ["Tipo de evento", "O que significa"],
        [
            ["EDICAO", "Quantidade de um produto foi editada manualmente"],
            ["EDICAO_SUSPEITA", "Edicao fez o valor coincidir exatamente com o estoque do sistema"],
            ["EXCLUSAO", "Item removido da contagem"],
            ["CONSOLIDACAO", "Inventario consolidado no Automec"],
            ["ALERTA", "Quantidade bipada muito acima do estoque esperado"],
            ["ALERTA_REESCAN", "Produto excluido e re-escaneado na mesma sessao (possivel fraude)"],
        ],
        [4.5*cm, 11*cm],
    )

    story.append(Paragraph("Tela de Operadores", s["h2"]))
    story.append(Paragraph(
        "Gerentes e administradores podem cadastrar e ativar/desativar os operadores de coleta. "
        "Operadores sao as pessoas que fazem a bipagem fisica - aparecem na lista de selecao "
        "antes do inicio da contagem.", s["corpo"]))

    story.append(Paragraph("Tela de Usuarios", s["h2"]))
    story.append(Paragraph(
        "Disponivel apenas para o <b>admin mobile</b>. Permite:", s["corpo"]))
    lista(story, s, [
        "<b>Definir senha mobile</b> - cada usuario precisa de uma senha mobile separada para acessar o app",
        "<b>Dar/remover admin mobile</b> - delega a outro usuario a capacidade de gerenciar senhas e acessos",
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
        title="Invec - Documentacao Tecnica")
    s = estilos()
    story = []

    capa(story, s, "Documentacao Tecnica",
         "Arquitetura, endpoints, banco de dados e seguranca")

    story.append(Paragraph("Visao Geral", s["h1"]))
    hr(story)
    story.append(Paragraph(
        "O Invec e composto por dois componentes: um <b>backend FastAPI</b> (Python) que se conecta "
        "ao banco Firebird do Automec, e um <b>app Android</b> (Kotlin) que se comunica com o backend "
        "via HTTP/JSON pelo Wi-Fi da empresa.", s["corpo"]))
    code(story, "[Celular Android]  --Wi-Fi--  [InvecServidor.exe]  --  [Firebird / Automec]")
    story.append(Paragraph(
        "O servidor roda como servico Windows (InvecAPI via NSSM). Varios celulares podem operar "
        "simultaneamente no mesmo deposito - as escritas no banco sao atomicas para evitar "
        "condicoes de corrida.", s["corpo"]))

    story.append(Paragraph("Stack Tecnologica", s["h1"]))
    hr(story)
    tabela(story, s,
        ["Componente", "Tecnologia", "Versao"],
        [
            ["Backend", "Python + FastAPI + Uvicorn", "Python 3.13, FastAPI 0.115+"],
            ["Banco de dados", "Firebird 5 via firebird-driver", "Firebird 5.0"],
            ["App mobile", "Android Kotlin", "Min SDK 26 (Android 8.0)"],
            ["HTTP client (app)", "Retrofit2 + OkHttp3", "Retrofit 2.11+"],
            ["Camera", "CameraX + ML Kit Barcode", "CameraX 1.3+"],
            ["UI", "Material Design 3 + ViewBinding", "Material 1.12+"],
            ["Autenticacao", "JWT HS256", "python-jose 3.3+"],
            ["Licenca", "JWT RS256 (RSA 2048-bit)", "cryptography 41+"],
            ["Distribuicao servidor", "PyInstaller + NSSM", "PyInstaller 6+"],
        ],
        [4*cm, 6*cm, 5.5*cm],
    )

    story.append(Paragraph("Estrutura do Projeto", s["h1"]))
    hr(story)
    story.append(Paragraph("Backend (api/)", s["h2"]))
    code(story,
        "api/main.py               # FastAPI app, lifespan (licenca + migrations)\n"
        "api/server.py             # entrypoint Uvicorn para PyInstaller\n"
        "api/app/database.py       # get_connection() context manager Firebird\n"
        "api/app/security.py       # JWT HS256, get_current_user()\n"
        "api/app/licenca.py        # validacao RSA 2048-bit\n"
        "api/app/migrations.py     # DDL idempotente na inicializacao\n"
        "api/app/models/schemas.py # modelos Pydantic\n"
        "api/app/routers/\n"
        "  auth.py                 # login, rate limit, usuarios mobile\n"
        "  depositos.py            # listagem de depositos\n"
        "  produtos.py             # busca por codigo de barras\n"
        "  inventario.py           # bipagem, relatorio, consolidacao, auditoria\n"
        "  operadores.py           # CRUD de operadores fisicos")

    story.append(Paragraph("App Android (app/)", s["h2"]))
    code(story,
        "ui/base/TimeoutActivity.kt          # base com timeout de inatividade 15min\n"
        "ui/login/LoginActivity.kt           # autenticacao\n"
        "ui/main/MainActivity.kt             # selecao de deposito e operador\n"
        "ui/scanner/ScannerActivity.kt       # bipagem camera + Bluetooth\n"
        "ui/relatorio/RelatorioActivity.kt   # relatorio, edicao, consolidacao\n"
        "ui/recontagem/RecontagemActivity.kt # segunda contagem\n"
        "ui/historico/HistoricoActivity.kt   # historico de consolidacoes\n"
        "ui/auditoria/AuditoriaActivity.kt   # log de auditoria\n"
        "ui/operadores/OperadoresActivity.kt # gestao de operadores\n"
        "ui/usuarios/UsuariosActivity.kt     # gestao de acesso mobile\n"
        "data/api/ApiService.kt              # endpoints Retrofit\n"
        "data/api/RetrofitClient.kt          # OkHttp + interceptor 401\n"
        "data/model/Models.kt                # data classes request/response\n"
        "util/SessionManager.kt              # SharedPreferences (token, deposito, etc.)")

    story.append(Paragraph("Autenticacao e Sessao", s["h1"]))
    hr(story)
    story.append(Paragraph(
        "O login e feito via POST /auth/login com login e senha. O backend verifica em USUARIOS "
        "comparando com SENHAMOBILE (coluna adicionada pelo Invec) ou SENHA (senha original do Automec). "
        "Em caso de sucesso, retorna um JWT HS256 assinado com JWT_SECRET.", s["corpo"]))
    story.append(Paragraph(
        "O token contem: sub (IDUSUARIO), login, role (operador/gerente/admin), "
        "idgrupo e mobile_admin.", s["corpo"]))
    lista(story, s, [
        "<b>Expiracao:</b> 8 horas",
        "<b>Inatividade:</b> 15 minutos (TimeoutActivity via Handler/Runnable)",
        "<b>Rate limit:</b> 5 tentativas em 60s - bloqueio de 300s, por IP e por usuario",
        "<b>Interceptor 401:</b> OkHttp detecta token expirado e redireciona para LoginActivity",
    ])

    story.append(Paragraph("Sistema de Licenca RSA", s["h1"]))
    hr(story)
    story.append(Paragraph(
        "A licenca e um JWT RS256 gerado com a chave privada RSA 2048-bit "
        "(licenca_privada.pem - uso exclusivo Pontual Tecnologia). "
        "O servidor embute a chave publica em app/licenca.py e valida o token na inicializacao. "
        "Se a licenca for invalida ou expirada, o servidor encerra com sys.exit(1).", s["corpo"]))
    story.append(Paragraph(
        "Campos do JWT de licenca: cliente, cnpj, emitido_em, expira_em (vazio = permanente).",
        s["nota"]))

    story.append(Paragraph("Banco de Dados", s["h1"]))
    hr(story)
    story.append(Paragraph("Tabelas do Automec utilizadas", s["h2"]))
    tabela(story, s,
        ["Tabela", "Operacao", "Observacao"],
        [
            ["USUARIOS", "SELECT + UPDATE", "Colunas SENHAMOBILE e MOBILE_ADMIN adicionadas pelo Invec"],
            ["DEPOSITO", "SELECT", "Listagem de depositos disponiveis"],
            ["PRODUTO + PRODUTO_CODBARRA", "SELECT", "Busca por codigo de barras (primary e secondary)"],
            ["MOVIMENTO", "SELECT", "QTDEATUAL por produto e deposito"],
            ["MOV_PRODUTO", "INSERT + SELECT", "Consolidacao: TIPOMOVIMENTO=5, trigger atualiza MOVIMENTO"],
            ["SAIDAPRODUTO + SAIDAESTOQUE", "SELECT", "CE (Considerar Entrega) - pedidos pendentes de saida"],
            ["PRODUTOPRECO", "SELECT", "FATORCONV e VLCUSTO para calculo do MOV_PRODUTO"],
        ],
        [3.8*cm, 2.8*cm, 8.9*cm],
    )
    story.append(Paragraph("Tabelas criadas pelo Invec", s["h2"]))
    tabela(story, s,
        ["Tabela", "Funcao"],
        [
            ["INVENTARIO_TEMP", "Armazena a sessao de contagem em andamento. Contem QTDEATUAL_SNAP (snapshot do estoque no momento do 1o scan) e OPERADOR."],
            ["OPERADORES_APP", "Cadastro de operadores fisicos de coleta, separado dos usuarios do Automec."],
            ["LOG_INVENTARIO", "Auditoria completa: TIPO, CDDEPOSITO, CDPRODUTO, PRODUTO, OPERADOR, LOGIN_USUARIO, QTDE_ANTES, QTDE_DEPOIS, MOTIVO, DEVICE_ID, DATA_HORA."],
        ],
        [4*cm, 11.5*cm],
    )

    story.append(Paragraph("Fluxo de Bipagem", s["h1"]))
    hr(story)
    story.append(Paragraph(
        "Cada scan faz um POST /inventario/bipagem. O backend executa um UPDATE atomico com "
        "RETURNING para evitar race condition quando dois celulares bipam o mesmo produto "
        "simultaneamente:", s["corpo"]))
    code(story,
        "UPDATE INVENTARIO_TEMP\n"
        "   SET QTDE = QTDE + ?, OPERADOR = ?\n"
        " WHERE CDPRODUTO = ? AND CDDEPOSITO = ?\n"
        "RETURNING QTDE")
    story.append(Paragraph(
        "Se o UPDATE retornar 0 linhas (primeiro scan do produto), executa um INSERT com o "
        "snapshot do estoque atual (QTDEATUAL_SNAP). O snapshot e tirado uma unica vez - no "
        "momento do primeiro scan - e nao e atualizado em scans subsequentes.", s["corpo"]))

    story.append(Paragraph("Fluxo de Consolidacao", s["h1"]))
    hr(story)
    lista(story, s, [
        "Busca todos os itens de INVENTARIO_TEMP para o deposito",
        "Consulta pedidos pendentes em SAIDAPRODUTO (CE). Envolvido em try/except para compatibilidade com versoes antigas do Automec",
        "Calcula divergencias: compara qtde_contada com qtde_atual + qtdeentrega",
        "Se divergencias >= 30% e >= 5 itens: lanca HTTP 422 - recontagem obrigatoria",
        "Se ha divergencias: valida credenciais do supervisor (gerente/admin)",
        "Gera IDINVENTARIO via GEN_ID(GEN_MOV_PRODUTO, 1)",
        "Para cada item: INSERT em MOV_PRODUTO com TIPOMOVIMENTO=5. O trigger TG_INSERT_MOV_PRODUTO do Automec atualiza MOVIMENTO.QTDEATUAL automaticamente",
        "DELETE FROM INVENTARIO_TEMP para o deposito (mesma transacao)",
        r"Grava CONSOLIDACAO no LOG_INVENTARIO e salva relatorio .txt em C:\Invec\relatorios\\",
    ])
    story.append(Paragraph(
        "O lock _consolidando (threading.Lock + set) impede que dois celulares consolidem o "
        "mesmo deposito simultaneamente.", s["nota"]))

    story.append(Paragraph("Considerar Entrega (CE)", s["h1"]))
    hr(story)
    story.append(Paragraph(
        "Quando ha pedidos de saida pendentes (faturados mas ainda nao entregues), o estoque real "
        "e QTDEATUAL + QTDEENTREGA. O Invec considera isso tanto no calculo de divergencias "
        "quanto na consolidacao:", s["corpo"]))
    tabela(story, s,
        ["Situacao", "QTENTRADA", "QTSAIDA", "VL_PERDA_GANHO"],
        [
            ["Com entrega e contado > atual", "contado - atual", "qtdeentrega", "NULL"],
            ["Com entrega e contado < atual", "0", "(atual - contado) + qtdeentrega", "NULL"],
            ["Com entrega e contado = atual", "0", "qtdeentrega", "NULL"],
            ["Sem entrega e contado > atual", "contado - atual", "0", "(contado - atual) x vlcusto"],
            ["Sem entrega e contado < atual", "0", "atual - contado", "(contado - atual) x vlcusto"],
            ["Sem entrega e contado = atual", "0", "0", "0"],
        ],
        [5*cm, 3*cm, 3.5*cm, 4*cm],
    )

    story.append(Paragraph("Endpoints Completos", s["h1"]))
    hr(story)
    tabela(story, s,
        ["Metodo", "Rota", "Descricao", "Acesso"],
        [
            ["POST", "/auth/login", "Login com rate limit", "Publico"],
            ["GET", "/auth/usuarios", "Lista usuarios mobile", "Admin mobile"],
            ["PUT", "/auth/usuarios/{id}/senha-mobile", "Define senha mobile", "Admin mobile"],
            ["PUT", "/auth/usuarios/{id}/toggle-admin", "Alterna admin mobile", "Usuario MI"],
            ["GET", "/depositos", "Lista depositos Firebird", "Autenticado"],
            ["GET", "/produtos/barcode/{codigo}", "Busca por codigo de barras", "Autenticado"],
            ["GET", "/produtos/busca", "Busca por descricao", "Autenticado"],
            ["POST", "/inventario/bipagem", "Registra scan (atomico)", "Autenticado"],
            ["GET", "/inventario/relatorio/{dep}", "Relatorio da sessao", "Autenticado"],
            ["GET", "/inventario/resumo/{dep}", "Produtos nao contados", "Autenticado"],
            ["POST", "/inventario/consolidar", "Consolida no Automec", "Autenticado"],
            ["PUT", "/inventario/bipagem/{id}", "Edita quantidade (auditado)", "Autenticado"],
            ["DELETE", "/inventario/bipagem/{id}", "Remove item (auditado)", "Autenticado"],
            ["GET", "/inventario/historico/{dep}", "Historico de consolidacoes", "Autenticado"],
            ["GET", "/inventario/log/{dep}", "Log de auditoria", "Gerente/Admin"],
            ["GET", "/operadores", "Lista operadores de coleta", "Autenticado"],
            ["POST", "/operadores", "Cria operador", "Gerente/Admin"],
            ["PUT", "/operadores/{id}/toggle", "Ativa/desativa operador", "Gerente/Admin"],
        ],
        [1.8*cm, 5.5*cm, 6*cm, 3*cm],
    )

    story.append(Paragraph("Seguranca e Auditoria", s["h1"]))
    hr(story)
    tabela(story, s,
        ["Mecanismo", "Implementacao"],
        [
            ["Rate limit de login", "5 falhas em 60s - bloqueio 300s, por IP e por usuario (dicts em memoria)"],
            ["Supervisor obrigatorio", "Divergencias - gerente/admin diferente do operador deve autorizar com senha mobile"],
            ["EDICAO_SUSPEITA", "Detecta quando edicao faz a contagem coincidir exatamente com o estoque do sistema"],
            ["ALERTA_REESCAN", "Detecta produto excluido e re-escaneado na mesma sessao (janela de 12h)"],
            ["ALERTA de quantidade", "Quantidade > 2x estoque e estoque >= 10 un gera alerta e aviso no app"],
            ["device_id", "ID unico por instalacao do app, gravado em todos os eventos do LOG_INVENTARIO"],
            ["Retencao de logs", "BIPAGEM: 90 dias. Geral: 365 dias. EDICAO_SUSPEITA e ALERTA_REESCAN: permanente"],
        ],
        [4.5*cm, 11*cm],
    )

    story.append(Paragraph("Migrations Automaticas", s["h1"]))
    hr(story)
    story.append(Paragraph(
        "Na inicializacao, run_migrations() executa DDL idempotente (verifica antes de criar), "
        "permitindo atualizar o servidor sem scripts manuais de banco:", s["corpo"]))
    lista(story, s, [
        "Cria OPERADORES_APP se nao existir",
        "Adiciona coluna OPERADOR em INVENTARIO_TEMP se nao existir",
        "Adiciona coluna QTDEATUAL_SNAP em INVENTARIO_TEMP se nao existir",
        "Adiciona coluna MOBILE_ADMIN em USUARIOS se nao existir",
        "Cria LOG_INVENTARIO se nao existir",
        "Cria indices IDX_LOG_INV_DEPOSITO, IDX_LOG_INV_DATA, IDX_INVTEMP_PROD_DEP, IDX_LOG_INV_TIPO",
        "Remove logs antigos conforme politica de retencao",
        "Remove relatorios .txt com mais de 180 dias",
    ])

    story.append(Paragraph("Build e Distribuicao", s["h1"]))
    hr(story)
    story.append(Paragraph("Servidor", s["h2"]))
    code(story,
        "cd api\n"
        "pyinstaller servidor.spec --clean --noconfirm   # -> dist/InvecServidor.exe\n"
        "pyinstaller instalador.spec --clean --noconfirm # -> dist/Instalar-Invec.exe")
    story.append(Paragraph(
        "O instalador.spec bundla InvecServidor.exe + nssm.exe em um unico executavel GUI. "
        "O cliente recebe apenas Instalar-Invec.exe - sem Python, sem dependencias extras.",
        s["corpo"]))
    story.append(Paragraph("App Android", s["h2"]))
    code(story,
        ".\\gradlew assembleRelease\n"
        "# -> app/build/outputs/apk/release/app-release.apk")
    story.append(Paragraph(
        "O build usa R8/ProGuard para minificacao e ofuscacao. O APK e assinado com a keystore "
        "em app/release/ (nao commitada no git).", s["corpo"]))

    doc.build(story)
    print(f"Tecnico gerado: {caminho}")


if __name__ == "__main__":
    out = os.path.dirname(os.path.abspath(__file__))
    gerar_manual(os.path.join(out, "Invec_Manual.pdf"))
    gerar_tecnico(os.path.join(out, "Invec_Tecnico.pdf"))
    print("Concluido.")
