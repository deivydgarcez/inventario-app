"""
Gera Invec_Relatorio_Mudancas.pdf — relatório unificado de mudanças.
Combina sprint 28/09/2026 + v1.8.0 (30/09/2026) com detalhamento do
sistema de licenciamento por dispositivo.
"""
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
import os

OUT = os.path.join(os.path.dirname(__file__), "../docs/Invec_Relatorio_Mudancas.pdf")

# ── Cores da marca ─────────────────────────────────────────────────────────────
ORANGE      = colors.HexColor("#CC5B2A")
ORANGE_DARK = colors.HexColor("#9E3A0C")
BLUE        = colors.HexColor("#0277BD")
DARK        = colors.HexColor("#1A1A1A")
GRAY        = colors.HexColor("#757575")
LIGHT_GRAY  = colors.HexColor("#F5F5F5")
LIGHT_ORANGE= colors.HexColor("#FFF3EE")
LIGHT_BLUE  = colors.HexColor("#E3F2FD")
GREEN       = colors.HexColor("#2E7D32")
RED         = colors.HexColor("#C62828")
WHITE       = colors.white

# ── Estilos ───────────────────────────────────────────────────────────────────
ss = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

TITLE      = S("Title",    fontName="Helvetica-Bold",   fontSize=22, textColor=WHITE,  spaceAfter=4,  alignment=TA_CENTER)
SUBTITLE   = S("Subtitle", fontName="Helvetica",        fontSize=11, textColor=WHITE,  spaceAfter=2,  alignment=TA_CENTER)
H1         = S("H1",       fontName="Helvetica-Bold",   fontSize=16, textColor=ORANGE, spaceBefore=14, spaceAfter=6)
H2         = S("H2",       fontName="Helvetica-Bold",   fontSize=13, textColor=DARK,   spaceBefore=10, spaceAfter=4)
H3         = S("H3",       fontName="Helvetica-Bold",   fontSize=11, textColor=DARK,   spaceBefore=6,  spaceAfter=3)
BODY       = S("Body",     fontName="Helvetica",        fontSize=9,  textColor=DARK,   spaceAfter=4,   leading=14, alignment=TA_JUSTIFY)
BULLET     = S("Bullet",   fontName="Helvetica",        fontSize=9,  textColor=DARK,   spaceAfter=3,   leading=14, leftIndent=14, bulletIndent=4)
CODE       = S("Code",     fontName="Courier",          fontSize=8,  textColor=DARK,   spaceAfter=3,   leading=12, backColor=LIGHT_GRAY, leftIndent=8, rightIndent=8)
NOTE       = S("Note",     fontName="Helvetica-Oblique",fontSize=8,  textColor=GRAY,   spaceAfter=6,   leading=12)
CAPTION    = S("Caption",  fontName="Helvetica-Bold",   fontSize=9,  textColor=GRAY,   spaceAfter=2,   alignment=TA_CENTER)
TAG_ANDROID= S("TagA",     fontName="Helvetica-Bold",   fontSize=7,  textColor=WHITE,  backColor=GREEN)
TAG_API    = S("TagApi",   fontName="Helvetica-Bold",   fontSize=7,  textColor=WHITE,  backColor=BLUE)
TAG_NEW    = S("TagNew",   fontName="Helvetica-Bold",   fontSize=7,  textColor=WHITE,  backColor=ORANGE)

def hr():
    return HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E0E0E0"), spaceAfter=6)

def sp(h=4):
    return Spacer(1, h * mm)

def tag(text, color):
    return f'<font color="white"><b> {text} </b></font>'

def bullet(text):
    return Paragraph(f"• {text}", BULLET)

def code_block(lines):
    elems = []
    for line in lines:
        elems.append(Paragraph(line.replace(" ", "&nbsp;").replace("<", "&lt;").replace(">", "&gt;"), CODE))
    return elems

def section_box(label, color=ORANGE):
    """Caixa colorida de título de seção."""
    data = [[Paragraph(label, ParagraphStyle("BL", fontName="Helvetica-Bold",
        fontSize=12, textColor=WHITE))]]
    t = Table(data, colWidths=["100%"])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), color),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ]))
    return t

def info_box(text, bg=LIGHT_ORANGE, border=ORANGE):
    data = [[Paragraph(text, ParagraphStyle("IB", fontName="Helvetica", fontSize=9,
        textColor=DARK, leading=13))]]
    t = Table(data, colWidths=["100%"])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), bg),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING",(0,0), (-1,-1), 10),
        ("TOPPADDING",  (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("BOX", (0,0), (-1,-1), 1.5, border),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return t


# ── Cabeçalho de página ───────────────────────────────────────────────────────
def cover_header():
    data = [[
        Paragraph("INVEC", ParagraphStyle("CH", fontName="Helvetica-Bold", fontSize=28,
            textColor=WHITE, spaceAfter=0)),
        Paragraph("Sistema de Inventário<br/><font size=11>Pontual Tecnologia</font>",
            ParagraphStyle("CH2", fontName="Helvetica", fontSize=13, textColor=WHITE,
                alignment=TA_LEFT)),
    ]]
    t = Table(data, colWidths=[50*mm, None])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), ORANGE),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 16),
        ("BOTTOMPADDING", (0,0), (-1,-1), 16),
        ("LEFTPADDING",   (0,0), (-1,-1), 16),
        ("LINEBELOW", (0,0), (-1,-1), 3, ORANGE_DARK),
    ]))
    return t


def build():
    doc = SimpleDocTemplate(
        OUT,
        pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm,
        topMargin=16*mm, bottomMargin=20*mm,
        title="Invec — Relatório de Mudanças",
        author="Pontual Tecnologia",
    )

    story = []

    # ── Capa ──────────────────────────────────────────────────────────────────
    story.append(cover_header())
    story.append(sp(6))

    capa_title = Table([[
        Paragraph("Relatório de Mudanças e Melhorias",
            ParagraphStyle("CT", fontName="Helvetica-Bold", fontSize=18, textColor=ORANGE,
                alignment=TA_CENTER)),
    ]], colWidths=["100%"])
    capa_title.setStyle(TableStyle([
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    story.append(capa_title)

    story.append(Paragraph("Gerado em 30/09/2026 · Sprint 28/09 + Versão v1.8.0",
        ParagraphStyle("CSubt", fontName="Helvetica", fontSize=10, textColor=GRAY,
            alignment=TA_CENTER)))
    story.append(sp(3))
    story.append(info_box(
        "Este documento descreve as mudanças implementadas nas últimas duas sprints. "
        "O APK e o servidor devem ser compilados e distribuídos após validação pela equipe técnica."
    ))
    story.append(sp(4))
    story.append(hr())

    # ── Índice ────────────────────────────────────────────────────────────────
    story.append(Paragraph("Conteúdo deste relatório", H2))
    indice = [
        ["Sprint 28/09/2026", "Busca múltipla, data retroativa, recontagem, melhorias"],
        ["v1.8.0 — Design Glassmorphism", "Novo visual em todas as telas do app"],
        ["v1.8.0 — Licenciamento por Dispositivo", "Sistema de controle de aparelhos por licença  ← NOVO"],
        ["Checklist de Testes", "Cenários para validação antes da entrega"],
    ]
    t = Table(
        [[Paragraph(f"<b>{r}</b>", ParagraphStyle("TI", fontName="Helvetica-Bold", fontSize=9)),
          Paragraph(d, ParagraphStyle("TD", fontName="Helvetica", fontSize=9, textColor=GRAY))]
         for r, d in indice],
        colWidths=[70*mm, None],
    )
    t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [WHITE, LIGHT_GRAY]),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#E0E0E0")),
    ]))
    story.append(t)

    # ══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())

    # ── SPRINT 28/09 ─────────────────────────────────────────────────────────
    story.append(section_box("Sprint 28/09/2026 — Novas Funcionalidades e Melhorias"))
    story.append(sp(3))

    story.append(Paragraph("Novas Funcionalidades", H1))

    story.append(Paragraph(
        "<b>1. Busca de produto por múltiplos critérios</b> "
        "<font color='#2E7D32' size=8>[Android + API]</font>", H2))
    story.append(Paragraph(
        "O botão 'digitar manualmente' no Scanner agora abre um menu com 3 opções:", BODY))
    for b in [
        "Por <b>código de barras</b> — comportamento anterior mantido.",
        "Por <b>código do produto</b> (número) — para produtos sem código de barras cadastrado.",
        "Por <b>nome / descrição</b> — digita parte do nome e exibe lista de resultados para escolher.",
        "Funciona <b>online</b> (API) e <b>offline</b> (cache local como fallback).",
    ]:
        story.append(bullet(b))
    story.append(sp(2))

    story.append(Paragraph(
        "<b>2. Data retroativa na consolidação</b> "
        "<font color='#2E7D32' size=8>[Android + API]</font>", H2))
    for b in [
        "Campo de data opcional na tela de consolidação.",
        "Permite registrar um inventário com data retroativa no Automec.",
        "Supervisor seleciona a data antes de confirmar — gravada em <b>DTMOVIMENTO</b>.",
    ]:
        story.append(bullet(b))
    story.append(sp(2))

    story.append(Paragraph(
        "<b>3. Recontagem: reiniciar contagem de depósito</b> "
        "<font color='#2E7D32' size=8>[Android + API]</font>", H2))
    for b in [
        "Botão 'Zerar Contagem' disponível para supervisores e usuários MI.",
        "Exige justificativa obrigatória (mínimo 10 caracteres).",
        "Registrado no <b>LOG_INVENTARIO</b> com tipo <b>ZERAR_CONTAGEM</b> para auditoria.",
        "Operadores comuns não têm acesso — bloqueio no servidor e no app.",
    ]:
        story.append(bullet(b))
    story.append(sp(3))

    story.append(hr())
    story.append(Paragraph("Melhorias", H1))

    story.append(Paragraph(
        "<b>4. Relatório: aviso de bipagens não sincronizadas</b> "
        "<font color='#2E7D32' size=8>[Android]</font>", H2))
    for b in [
        "Ao abrir o relatório, o app conta bipagens salvas localmente ainda não enviadas.",
        "Se houver pendentes: exibe aviso laranja e inclui esses itens na lista imediatamente.",
        "Aviso de 'produtos não contados' só aparece quando não há pendentes — evita confusão.",
    ]:
        story.append(bullet(b))
    story.append(sp(2))

    story.append(Paragraph(
        "<b>5. Retry automático no carregamento do relatório</b> "
        "<font color='#2E7D32' size=8>[Android]</font>", H2))
    for b in [
        "Em erro de rede ou HTTP 500, o app tenta até 2 vezes com intervalo de 1,5 s.",
        "Apenas após as 2 tentativas falharem o erro é exibido ao usuário.",
        "Erros passam a exibir código identificador <b>[INV-R01..R04, INV-C01..C02]</b> para facilitar suporte.",
    ]:
        story.append(bullet(b))
    story.append(sp(2))

    story.append(Paragraph(
        "<b>6. Migração automática de senhas para hash seguro</b> "
        "<font color='#0277BD' size=8>[API]</font>", H2))
    for b in [
        "Na primeira autenticação com senha em texto puro, converte para <b>bcrypt</b> automaticamente.",
        "Transparente para o usuário — sem necessidade de redefinir senha.",
        "Senhas já em bcrypt ($2b$) permanecem sem alteração.",
    ]:
        story.append(bullet(b))

    # ══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())

    # ── GLASSMORPHISM ─────────────────────────────────────────────────────────
    story.append(section_box("v1.8.0 — Design Glassmorphism (30/09/2026)"))
    story.append(sp(3))

    story.append(Paragraph(
        "Migração completa do design Neumorphism para <b>Glassmorphism</b> — "
        "visual de vidro fosco moderno em todas as telas do app.", BODY))
    story.append(sp(2))

    story.append(Paragraph("O que mudou visualmente", H2))
    rows = [
        ["Elemento",     "Antes (Neumorphism)", "Depois (Glassmorphism)"],
        ["Fundo",        "Cinza plano",         "Gradiente diagonal pêssego→azul"],
        ["Cards",        "Sombras duplas 3D",   "Semi-transparente + borda branca sutil"],
        ["Toolbar",      "Cor sólida",          "Branco fosco 94% opacidade"],
        ["Botão primário","Sombra interna",      "Laranja sólido #CC5B2A, cantos 16dp"],
        ["Botão secundário","Elevação Material", "Fundo 15% branco + borda 40% branca"],
        ["Botão scanner","FAB laranja",          "Círculo glass com núcleo laranja"],
    ]
    t = Table(rows, colWidths=[45*mm, 60*mm, None])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  ORANGE),
        ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT_GRAY]),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#E0E0E0")),
    ]))
    story.append(t)
    story.append(sp(3))

    story.append(Paragraph("Telas migradas", H2))
    story.append(Paragraph(
        "Login, Principal, Scanner, Relatório, Recontagem, Histórico, Auditoria, Usuários, Operadores — "
        "e todos os itens de lista (item_relatorio, item_historico, item_auditoria, item_recontagem, item_operador, item_usuario).", BODY))

    # ══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())

    # ── LICENCIAMENTO POR DISPOSITIVO ─────────────────────────────────────────
    story.append(section_box("v1.8.0 — Licenciamento por Dispositivo (30/09/2026)", BLUE))
    story.append(sp(3))

    story.append(info_box(
        "<b>Objetivo:</b> Controlar quantos celulares podem usar o app Invec por cliente. "
        "O limite é definido pela Pontual Tecnologia no momento da emissão da licença. "
        "Aparelhos já registrados nunca são bloqueados retroativamente — apenas novas tentativas além do limite são bloqueadas.",
        bg=LIGHT_BLUE, border=BLUE,
    ))
    story.append(sp(4))

    # --- Conceito ---
    story.append(Paragraph("Como funciona — visão geral", H2))

    flow_data = [
        [Paragraph("<b>Pontual emite licença</b>\nmax_dispositivos = 2",
            ParagraphStyle("FD", fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER))],
        [Paragraph("↓", ParagraphStyle("AR", fontName="Helvetica", fontSize=14,
            textColor=GRAY, alignment=TA_CENTER))],
        [Paragraph("Aparelho 1 faz login → <b>Registrado (slot 1/2)</b>",
            ParagraphStyle("FD2", fontName="Helvetica", fontSize=9, textColor=GREEN, alignment=TA_CENTER))],
        [Paragraph("Aparelho 2 faz login → <b>Registrado (slot 2/2)</b>",
            ParagraphStyle("FD3", fontName="Helvetica", fontSize=9, textColor=GREEN, alignment=TA_CENTER))],
        [Paragraph("Aparelho 3 faz login → <b>BLOQUEADO — limite atingido</b>",
            ParagraphStyle("FD4", fontName="Helvetica-Bold", fontSize=9, textColor=RED, alignment=TA_CENTER))],
        [Paragraph("↓ Admin remove Aparelho 1", ParagraphStyle("AR2", fontName="Helvetica-Oblique",
            fontSize=9, textColor=GRAY, alignment=TA_CENTER))],
        [Paragraph("Aparelho 3 faz login → <b>Registrado (slot 2/2) ✓</b>",
            ParagraphStyle("FD5", fontName="Helvetica-Bold", fontSize=9, textColor=GREEN, alignment=TA_CENTER))],
    ]
    t = Table(flow_data, colWidths=["100%"])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,0), colors.HexColor("#E3F2FD")),
        ("BACKGROUND", (0,2), (0,3), colors.HexColor("#E8F5E9")),
        ("BACKGROUND", (0,4), (0,4), colors.HexColor("#FFEBEE")),
        ("BACKGROUND", (0,6), (0,6), colors.HexColor("#E8F5E9")),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("BOX",    (0,0), (0,0), 1, BLUE),
        ("BOX",    (0,2), (0,3), 1, GREEN),
        ("BOX",    (0,4), (0,4), 1, RED),
        ("BOX",    (0,6), (0,6), 1, GREEN),
    ]))
    story.append(t)
    story.append(sp(4))

    # --- Gerador de licença ---
    story.append(Paragraph("1. Gerar licença com limite de dispositivos", H2))
    story.append(Paragraph(
        "O campo <b>max_dispositivos</b> foi adicionado ao <b>gerar_licenca.py</b>. "
        "Se deixado em branco, a licença é emitida sem limite.", BODY))
    story.append(sp(1))
    story.extend(code_block([
        "python gerar_licenca.py",
        "",
        "Nome do cliente       : Loja ABC",
        "CNPJ                  : 00.000.000/0001-00",
        "Validade (meses)      : 12",
        "ID da maquina         : [Enter — sem vinculo]",
        "Max dispositivos moveis: 3        <- CAMPO NOVO",
        "",
        "Max. disp. : 3",
        "LICENSE_KEY=eyJhbGciOiJSUzI1NiJ9...",
    ]))
    story.append(sp(1))
    story.append(Paragraph(
        "O valor fica codificado no JWT da licença como campo <b>max_dispositivos</b> "
        "e não pode ser alterado sem gerar uma nova licença.", NOTE))
    story.append(sp(3))

    # --- Banco de dados ---
    story.append(Paragraph("2. Banco de dados — nova tabela", H2))
    story.append(Paragraph(
        "A tabela <b>DISPOSITIVOS_AUTORIZADOS</b> é criada automaticamente na primeira inicialização "
        "do servidor após a atualização. Não requer ação manual.", BODY))
    story.append(sp(1))
    story.extend(code_block([
        "DISPOSITIVOS_AUTORIZADOS",
        "  ID               INTEGER (PK auto-increment)",
        "  DEVICE_ID        VARCHAR(128) UNIQUE  -- UUID gerado no celular",
        "  NOME_DISPOSITIVO VARCHAR(200)          -- ex.: Samsung Galaxy A54",
        "  PRIMEIRO_ACESSO  TIMESTAMP             -- quando o aparelho se registrou",
        "  ULTIMO_ACESSO    TIMESTAMP             -- última vez que fez login",
    ]))
    story.append(sp(1))
    story.append(Paragraph(
        "O campo <b>DEVICE_ID</b> é um UUID gerado na primeira instalação do app no celular e "
        "salvo permanentemente no dispositivo. É único por aparelho e não muda mesmo ao trocar de conta.", NOTE))
    story.append(sp(3))

    # --- Lógica de verificação ---
    story.append(Paragraph("3. Lógica de verificação no login (servidor)", H2))
    rows = [
        ["Situação", "Ação do servidor", "Resultado para o usuário"],
        ["Aparelho já registrado",     "Atualiza ULTIMO_ACESSO",       "Login normal ✓"],
        ["Aparelho novo + slots livres","Registra + continua",          "Login normal ✓"],
        ["Aparelho novo + limite cheio","Retorna HTTP 403",             "Dialog de erro no app"],
        ["Sem max_dispositivos na licença","Ignora verificação",         "Login normal ✓ (ilimitado)"],
    ]
    t = Table(rows, colWidths=[52*mm, 58*mm, None])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT_BLUE]),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("BOX",           (0,0), (-1,-1), 0.5, BLUE),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#BBDEFB")),
    ]))
    story.append(t)
    story.append(sp(3))

    # --- App Android ---
    story.append(Paragraph("4. Mudanças no app Android", H2))

    story.append(Paragraph("<b>Tela de Login</b>", H3))
    for b in [
        "Gera automaticamente um <b>UUID único</b> na primeira abertura e salva permanentemente no aparelho.",
        "Envia <b>device_id</b> e <b>device_name</b> (modelo do celular) em cada login.",
        "Se receber HTTP 403 do servidor, exibe um <b>Dialog de alerta</b> (não Toast) com a mensagem completa.",
    ]:
        story.append(bullet(b))

    story.append(sp(2))
    story.append(info_box(
        '<b>Mensagem exibida ao usuário quando bloqueado:</b>\n\n'
        '"Limite de Dispositivos — Limite de licença atingido (2 dispositivo(s) autorizado(s)). '
        'Contate o administrador para liberar um slot."',
        bg=LIGHT_ORANGE, border=ORANGE,
    ))
    story.append(sp(3))

    story.append(Paragraph("<b>Tela Dispositivos Autorizados</b> (admin/MI)", H3))
    for b in [
        "Acessível pelo <b>menu ⋮ (três pontos)</b> na tela Usuários Mobile — visível apenas para MI e Admin Mobile.",
        "Lista todos os aparelhos registrados com: nome do modelo, ID parcial, data de cadastro e último acesso.",
        "Botão <b>'Remover'</b> em cada linha — exige confirmação antes de executar.",
        "Ao remover, o slot é liberado imediatamente para o próximo aparelho que tentar login.",
    ]:
        story.append(bullet(b))
    story.append(sp(3))

    # --- API endpoints ---
    story.append(Paragraph("5. Novos endpoints de API", H2))
    rows = [
        ["Método", "Endpoint",              "Acesso",       "Descrição"],
        ["GET",    "/admin/dispositivos",   "Admin / MI",   "Lista todos os dispositivos registrados com timestamps"],
        ["DELETE", "/admin/dispositivos/{id}", "Admin / MI","Remove um dispositivo, liberando o slot imediatamente"],
    ]
    t = Table(rows, colWidths=[18*mm, 60*mm, 28*mm, None])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTNAME",      (0,1), (0,-1),  "Courier-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT_BLUE]),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("BOX",           (0,0), (-1,-1), 0.5, BLUE),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#BBDEFB")),
    ]))
    story.append(t)
    story.append(sp(2))
    story.append(Paragraph(
        "Ambos os endpoints exigem token Bearer de usuário MI ou com flag <b>mobile_admin = 1</b>. "
        "Tentativas sem autorização retornam HTTP 403.", NOTE))

    # ══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())

    # ── CHECKLIST ─────────────────────────────────────────────────────────────
    story.append(section_box("Checklist de Testes — v1.8.0"))
    story.append(sp(3))

    story.append(Paragraph("Sprint 28/09/2026 — testes anteriores", H2))
    rows_old = [
        ["#", "Cenário",                      "O que verificar",                          "OK"],
        ["1",  "Busca por nome",              "Nome parcial, produto inativo, sem resultado", "☐"],
        ["2",  "Busca por código interno",    "Produto sem código de barras",              "☐"],
        ["3",  "Data retroativa",             "Data de ontem/hoje; data futura deve bloquear", "☐"],
        ["4",  "Recomeçar contagem",          "Operador comum (negar) e supervisor (permitir)","☐"],
        ["5",  "Retry de rede",               "Simular queda ao abrir relatório",          "☐"],
        ["6",  "Aviso de pendentes",          "Bipar offline → abrir relatório → aviso laranja","☐"],
        ["7",  "Consolidação c/ data",        "Data retroativa → verificar DTMOVIMENTO no Firebird","☐"],
    ]
    t = Table(rows_old, colWidths=[8*mm, 45*mm, None, 10*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  colors.HexColor("#757575")),
        ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT_GRAY]),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("ALIGN",         (-1,0), (-1,-1), "CENTER"),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#E0E0E0")),
    ]))
    story.append(t)
    story.append(sp(4))

    story.append(Paragraph("v1.8.0 — testes novos (Glassmorphism + Dispositivos)", H2))
    rows_new = [
        ["#",  "Cenário",                          "O que verificar",                                    "OK"],
        ["8",  "Visual glassmorphism",              "Gradiente, cards glass, botões flat em todas as telas","☐"],
        ["9",  "Modo escuro",                       "Tokens navy, card 15% branco, toolbar escura",       "☐"],
        ["10", "Registro de dispositivo",           "1º login registra aparelho na tabela DISPOSITIVOS_AUTORIZADOS","☐"],
        ["11", "Login aparelho já registrado",      "2º login do mesmo aparelho apenas atualiza ULTIMO_ACESSO","☐"],
        ["12", "Bloqueio por limite",               "3º aparelho com licença max=2 deve receber Dialog de erro","☐"],
        ["13", "Mensagem de erro correta",          "Dialog exibe '(2 dispositivo(s) autorizado(s))' com número correto","☐"],
        ["14", "Listar dispositivos (admin)",       "Menu ⋮ → Dispositivos mostra lista com nomes e datas","☐"],
        ["15", "Remover dispositivo",               "Confirmar → aparelho removido da lista; slot liberado imediatamente","☐"],
        ["16", "Login após liberar slot",           "Aparelho bloqueado consegue logar após admin remover outro","☐"],
        ["17", "Licença sem max_dispositivos",      "Nenhum bloqueio ocorre — ilimitado funciona normalmente","☐"],
        ["18", "Dispositivos (acesso não-admin)",   "Menu ⋮ não aparece para operadores sem admin",        "☐"],
    ]
    t = Table(rows_new, colWidths=[8*mm, 52*mm, None, 10*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT_BLUE]),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("ALIGN",         (-1,0), (-1,-1), "CENTER"),
        ("BOX",           (0,0), (-1,-1), 0.5, BLUE),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#BBDEFB")),
    ]))
    story.append(t)
    story.append(sp(4))

    # ── Rodapé ────────────────────────────────────────────────────────────────
    story.append(hr())
    story.append(Paragraph(
        "Pontual Tecnologia · Invec Sistema de Inventário · 30/09/2026 · v1.8.0",
        ParagraphStyle("Footer", fontName="Helvetica", fontSize=8, textColor=GRAY, alignment=TA_CENTER),
    ))

    doc.build(story)
    print(f"PDF gerado: {OUT}")


if __name__ == "__main__":
    build()
