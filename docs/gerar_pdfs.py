"""Gera os PDFs de documentacao do Invec usando ReportLab."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Preformatted,
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import ListFlowable, ListItem
import os

LARANJA     = colors.HexColor("#CC5B2A")
CINZA_CLARO = colors.HexColor("#F5F5F5")
CINZA_BORDA = colors.HexColor("#DDDDDD")
PRETO       = colors.HexColor("#212121")
CINZA_TEXTO = colors.HexColor("#555555")
VERMELHO    = colors.HexColor("#B71C1C")

W, H   = A4
MARGEM = 2.2 * cm

# ── Estilos (todos nomeados unicamente para evitar conflito no registro global) ─

def estilos():
    s = {}
    s["capa_invec"]  = ParagraphStyle("s_capa_invec",
        fontName="Helvetica-Bold", fontSize=32, textColor=LARANJA,
        leading=38, alignment=TA_CENTER)
    s["capa_doc"]    = ParagraphStyle("s_capa_doc",
        fontName="Helvetica-Bold", fontSize=19, textColor=PRETO,
        leading=24, alignment=TA_CENTER)
    s["capa_sub"]    = ParagraphStyle("s_capa_sub",
        fontName="Helvetica", fontSize=13, textColor=CINZA_TEXTO,
        leading=18, alignment=TA_CENTER)
    s["capa_rodape"] = ParagraphStyle("s_capa_rodape",
        fontName="Helvetica", fontSize=9, textColor=CINZA_TEXTO,
        leading=13, alignment=TA_CENTER)
    s["h1"] = ParagraphStyle("s_h1",
        fontName="Helvetica-Bold", fontSize=15, textColor=LARANJA,
        leading=20, spaceBefore=14, spaceAfter=4)
    s["h2"] = ParagraphStyle("s_h2",
        fontName="Helvetica-Bold", fontSize=11, textColor=PRETO,
        leading=16, spaceBefore=10, spaceAfter=3)
    s["corpo"] = ParagraphStyle("s_corpo",
        fontName="Helvetica", fontSize=9.5, textColor=PRETO,
        leading=15, spaceAfter=5, alignment=TA_JUSTIFY)
    s["cel"] = ParagraphStyle("s_cel",
        fontName="Helvetica", fontSize=8.5, textColor=PRETO,
        leading=13, spaceAfter=0, wordWrap="LTR")
    s["cel_hdr"] = ParagraphStyle("s_cel_hdr",
        fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.white,
        leading=13, spaceAfter=0, wordWrap="LTR")
    s["nota"] = ParagraphStyle("s_nota",
        fontName="Helvetica-Oblique", fontSize=8.5, textColor=CINZA_TEXTO,
        leading=13, spaceAfter=4)
    s["aviso"] = ParagraphStyle("s_aviso",
        fontName="Helvetica-Bold", fontSize=9, textColor=VERMELHO,
        leading=13, spaceAfter=4)
    s["pre"] = ParagraphStyle("s_pre",
        fontName="Courier", fontSize=7.8, textColor=PRETO,
        leading=12, leftIndent=0, rightIndent=0,
        backColor=CINZA_CLARO, spaceAfter=5)
    return s


# ── Componentes reutilizaveis ────────────────────────────────────────────────

def capa(story, s, doc_titulo, subtitulo, versao="v1.0"):
    story.append(Spacer(1, 5 * cm))
    story.append(Paragraph("INVEC", s["capa_invec"]))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(doc_titulo, s["capa_doc"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(subtitulo, s["capa_sub"]))
    story.append(Spacer(1, 1.2 * cm))
    story.append(HRFlowable(width="55%", thickness=2, color=LARANJA, hAlign="CENTER"))
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph("Pontual Tecnologia", s["capa_rodape"]))
    story.append(Paragraph(versao + "  |  2026", s["capa_rodape"]))
    story.append(PageBreak())


def hr(story):
    story.append(HRFlowable(width="100%", thickness=0.5, color=CINZA_BORDA))
    story.append(Spacer(1, 5))


def code(story, s, texto):
    story.append(Preformatted(texto, s["pre"]))


def c(texto, s, hdr=False):
    return Paragraph(str(texto), s["cel_hdr"] if hdr else s["cel"])


def tabela(story, s, cab, linhas, widths):
    data = [[c(h, s, hdr=True) for h in cab]] + \
           [[c(v, s) for v in linha] for linha in linhas]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1,  0), LARANJA),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, CINZA_CLARO]),
        ("GRID",          (0, 0), (-1, -1), 0.3, CINZA_BORDA),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))


def lista(story, s, itens):
    items = [ListItem(Paragraph(i, s["corpo"]), bulletColor=LARANJA, leftIndent=14)
             for i in itens]
    story.append(ListFlowable(items, bulletType="bullet", start="•"))
    story.append(Spacer(1, 3))


# ════════════════════════════════════════════════════════════════════════════
# MANUAL DE INSTALACAO E USO
# ════════════════════════════════════════════════════════════════════════════

def gerar_manual(caminho):
    doc = SimpleDocTemplate(caminho, pagesize=A4,
        leftMargin=MARGEM, rightMargin=MARGEM,
        topMargin=MARGEM, bottomMargin=MARGEM,
        title="Invec - Manual de Instalacao e Uso")
    s = estilos()
    st = []

    capa(st, s, "Manual de Instalacao e Uso",
         "Guia completo: servidor Windows e aplicativo Android")

    # ── PARTE 1: SERVIDOR ───────────────────────────────────────────────────
    st.append(Paragraph("PARTE 1 - INSTALACAO DO SERVIDOR", s["h1"]))
    hr(st)

    st.append(Paragraph("Como o sistema funciona", s["h2"]))
    st.append(Paragraph(
        "O Invec e dividido em dois componentes que trabalham juntos pela rede da empresa: "
        "o <b>servidor</b>, instalado no computador da loja, e o <b>aplicativo</b>, instalado "
        "nos celulares Android. O servidor e quem acessa o banco de dados do Automec (Firebird) "
        "e processa todas as operacoes. Os celulares se comunicam com o servidor pelo Wi-Fi "
        "interno sem precisar de internet.", s["corpo"]))

    st.append(Paragraph("Pre-requisitos", s["h2"]))
    lista(st, s, [
        "Windows 10 ou 11 (64-bit) no computador que sera o servidor",
        "Automec instalado e funcionando com Firebird 5",
        "Acesso de <b>Administrador</b> nesse computador",
        "Arquivo <b>Instalar-Invec.exe</b> fornecido pela Pontual Tecnologia",
        "Chave de <b>licenca</b> fornecida pela Pontual Tecnologia (string eyJ...)",
        "Rede Wi-Fi interna para os celulares acessarem o servidor",
    ])

    st.append(Paragraph("Passo 1 - Executar o instalador como Administrador", s["h2"]))
    st.append(Paragraph(
        "Clique com o botao direito no arquivo <b>Instalar-Invec.exe</b> e selecione "
        "<b>Executar como administrador</b>. Se aparecer o aviso do Windows (UAC), clique em Sim. "
        "O instalador so funciona com permissao de Administrador.", s["corpo"]))

    st.append(Paragraph("Passo 2 - Preencher os campos", s["h2"]))
    tabela(st, s,
        ["Campo", "O que preencher", "Exemplo"],
        [
            ["Banco de dados Firebird", "Caminho completo do arquivo .FDB do Automec. Clique no botao ... para navegar.", r"C:\Automec\Dados\empresa.FDB"],
            ["Host Firebird", "Deixar localhost. So muda se o banco estiver em outro servidor.", "localhost"],
            ["Usuario Firebird", "Usuario do banco Firebird, normalmente SYSDBA.", "SYSDBA"],
            ["Senha Firebird", "Senha do banco Firebird. Padrao de instalacao: masterkey.", "masterkey"],
            ["Porta da API", "Porta TCP que o app usara. Padrao 8000. Nao mude sem necessidade.", "8000"],
            ["Chave de Licenca", "String JWT fornecida pela Pontual Tecnologia. Obrigatoria.", "eyJhbGciOiJSUzI1NiJ9..."],
        ],
        [3.8*cm, 5.7*cm, 5.5*cm],
    )
    st.append(Paragraph(
        "O caminho do banco pode ser visto no Automec em Arquivo > Configuracoes > Banco de dados.",
        s["nota"]))

    st.append(Paragraph('Passo 3 - Clicar em "Instalar / Atualizar"', s["h2"]))
    lista(st, s, [
        "Cria a pasta C:\\Invec\\ e subpastas logs\\ e relatorios\\",
        "Copia o servidor para C:\\Invec\\InvecServidor.exe",
        "Salva todas as configuracoes em C:\\Invec\\.env (incluindo a licenca)",
        "Registra o servico Windows <b>InvecAPI</b> que inicia automaticamente com o Windows",
        "Libera a porta no Firewall do Windows",
        "Inicia o servico",
    ])
    st.append(Paragraph(
        'Ao concluir aparece a mensagem <b>"Servico instalado e iniciado com sucesso!"</b>.',
        s["corpo"]))

    st.append(Paragraph("Passo 4 - Confirmar que o servidor subiu", s["h2"]))
    st.append(Paragraph(
        "Abra o navegador <b>no proprio computador servidor</b> e acesse:", s["corpo"]))
    code(st, s, "http://localhost:8000/")
    st.append(Paragraph(
        'Deve aparecer: {"status": "ok", "versao": "1.0.0"}. '
        r"Se aparecer erro de conexao, consulte C:\Invec\logs\servico.log.", s["corpo"]))

    st.append(Paragraph("Passo 5 - Descobrir o IP da rede para os celulares", s["h2"]))
    st.append(Paragraph(
        "Abra o Prompt de Comando (Win+R > cmd > Enter) e execute:", s["corpo"]))
    code(st, s, "ipconfig")
    st.append(Paragraph(
        "Procure a linha <b>Endereco IPv4</b> na placa de rede da empresa (ex: 192.168.1.31). "
        "Anote esse IP - e o que voce vai digitar nos celulares:", s["corpo"]))
    code(st, s, "http://192.168.1.31:8000/")
    st.append(Paragraph(
        "Recomendavel configurar IP fixo no roteador para este computador, assim o IP nao muda.",
        s["nota"]))

    st.append(Paragraph("Licenca: o que e e o que fazer quando expira", s["h2"]))
    st.append(Paragraph(
        "A chave de licenca e um codigo digital que identifica o cliente e autoriza o uso do Invec. "
        "O servidor verifica a licenca toda vez que e iniciado. Se nao encontrar uma licenca valida, "
        "<b>nao sobe</b> e registra o motivo no log.", s["corpo"]))
    tabela(st, s,
        ["Situacao", "Mensagem no log", "O que fazer"],
        [
            ["Sem licenca", "Licenca nao encontrada. Configure LICENSE_KEY no arquivo .env.", "Abrir o instalador, colar a chave e clicar em Reiniciar Servico"],
            ["Licenca invalida", "Licenca invalida ou corrompida", "Contatar a Pontual Tecnologia para obter uma nova chave"],
            ["Licenca expirada", "Licenca expirada em YYYY-MM-DD", "Contatar a Pontual Tecnologia para renovar"],
        ],
        [3.5*cm, 6*cm, 5.5*cm],
    )
    st.append(Paragraph(
        r"Log de licenca: C:\Invec\logs\servico.log - procure por linhas com [LICENCA].",
        s["nota"]))

    st.append(Paragraph("Instalar o app nos celulares Android", s["h2"]))
    st.append(Paragraph(
        "Transfira o arquivo <b>invec-app.apk</b> para o celular (cabo USB, WhatsApp ou e-mail). "
        "No celular, abra o arquivo para instalar. Se aparecer aviso de 'fonte desconhecida', "
        "toque em Configuracoes > permitir para este app > volte e instale.", s["corpo"]))
    lista(st, s, [
        "Abra o app Invec no celular",
        "Na tela de Login, toque no campo <b>URL do servidor</b> e informe o endereco completo (ex: http://192.168.1.31:8000/)",
        "Toque em <b>Salvar servidor</b> - o app salva esse endereco para os proximos acessos",
        "Faca login com seu usuario e senha mobile",
    ])
    st.append(Paragraph(
        "O campo URL so precisa ser configurado uma vez por celular. "
        "Se o IP do servidor mudar, abra o app e atualize o campo antes de fazer login.",
        s["nota"]))

    st.append(Paragraph("Atualizar o app nos celulares", s["h2"]))
    st.append(Paragraph(
        "Quando receber uma nova versao do APK da Pontual Tecnologia, transfira para o celular "
        "e instale normalmente por cima da versao anterior. Nao precisa desinstalar antes - "
        "as configuracoes (URL do servidor) sao mantidas.", s["corpo"]))

    st.append(Paragraph("Atualizar o servidor", s["h2"]))
    st.append(Paragraph(
        "Quando receber um novo <b>Instalar-Invec.exe</b>, execute-o como Administrador "
        "e clique em <b>Instalar / Atualizar</b>. O servico e parado, atualizado e reiniciado "
        "sem perda de dados. A licenca e reaproveitada automaticamente do .env existente.",
        s["corpo"]))

    st.append(Paragraph("Gerenciar o servico manualmente", s["h2"]))
    st.append(Paragraph(
        "Abra o Prompt de Comando como Administrador para controlar o servico:", s["corpo"]))
    code(st, s,
        "net stop InvecAPI     # para o servidor\n"
        "net start InvecAPI    # inicia o servidor\n"
        "sc query InvecAPI     # mostra o status atual")

    st.append(Paragraph("Solucao de problemas", s["h2"]))
    tabela(st, s,
        ["Problema", "Causa provavel", "Solucao"],
        [
            ["Servidor nao sobe", "Licenca ausente ou invalida", r"Ver C:\Invec\logs\servico.log e contatar Pontual Tecnologia"],
            ["Servidor nao sobe", "Caminho do banco .FDB errado", "Abrir o instalador, corrigir o caminho e reinstalar"],
            ["Servidor nao sobe", "Firebird nao esta rodando", "Verificar se o Automec esta aberto e funcionando"],
            ["App nao conecta ao servidor", "IP errado no campo URL do app", "Verificar IP com ipconfig e testar no navegador do celular"],
            ["App nao conecta ao servidor", "Firewall bloqueando a porta", "Executar o instalador novamente para reabrir a porta"],
            ["Sessao encerrada automaticamente", "15 minutos sem usar o app", "Normal - faca login novamente"],
            ["Login recusado no app", "Usuario sem senha mobile cadastrada", "Admin mobile deve cadastrar a senha na tela Usuarios"],
            ["Erro ao consolidar", "Banco Firebird indisponivel", "Verificar se o Automec esta acessivel e reiniciar o servico"],
        ],
        [4*cm, 4.5*cm, 6.5*cm],
    )

    st.append(PageBreak())

    # ── PARTE 2: USO DO APP ─────────────────────────────────────────────────
    st.append(Paragraph("PARTE 2 - USO DO APLICATIVO", s["h1"]))
    hr(st)

    st.append(Paragraph("Permissoes necessarias no celular", s["h2"]))
    st.append(Paragraph(
        "Na primeira vez que abrir o app, o Android pedira permissao para:", s["corpo"]))
    tabela(st, s,
        ["Permissao", "Para que serve"],
        [
            ["Camera", "Leitura de codigos de barras pelo modo camera"],
            ["Bluetooth", "Conexao com leitores de codigo Bluetooth"],
        ],
        [4*cm, 11.5*cm],
    )
    st.append(Paragraph("Aceite as permissoes solicitadas para o app funcionar corretamente.", s["nota"]))

    st.append(Paragraph("Tela de Login", s["h2"]))
    st.append(Paragraph(
        "Informe o <b>login</b> (mesmo do Automec) e a <b>senha mobile</b>. A senha mobile e "
        "separada da senha do Automec e e configurada pelo admin mobile na tela Usuarios. "
        "Se for o primeiro acesso, solicite ao gerente ou admin que cadastre sua senha mobile.",
        s["corpo"]))
    lista(st, s, [
        "Apos <b>5 tentativas erradas</b> seguidas, o login fica bloqueado por <b>5 minutos</b>",
        "A sessao dura <b>8 horas</b> a partir do login",
        "O app encerra a sessao automaticamente apos <b>15 minutos sem tocar na tela</b>",
        "Se o app mostrar 'sessao expirada', faca login novamente - os dados de bipagem sao mantidos no servidor",
    ])

    st.append(Paragraph("Tela Inicial", s["h2"]))
    lista(st, s, [
        "<b>Selecionar Deposito</b> - escolhe qual deposito sera inventariado nesta sessao",
        "<b>Selecionar Operador</b> - define quem esta fisicamente bipando os produtos (pode ser diferente do usuario logado)",
        "<b>Iniciar Bipagem</b> - so fica disponivel apos selecionar um deposito",
        "<b>Relatorio</b> - abre o relatorio da sessao atual do deposito selecionado",
        "<b>Operadores</b> - cadastrar e gerenciar operadores de coleta (gerentes e admins)",
        "<b>Usuarios</b> - gerenciar acesso mobile (apenas admin mobile)",
        "<b>Sair</b> - encerra a sessao e volta para o login",
    ])

    st.append(Paragraph("Tela de Scanner - Modo Camera", s["h2"]))
    st.append(Paragraph(
        "Toque em <b>Escanear</b> e aponte a camera traseira do celular para o codigo de barras. "
        "Mantenha o celular a cerca de 15-20 cm do codigo e aguarde o app reconhecer automaticamente.", s["corpo"]))
    lista(st, s, [
        "Cada leitura soma <b>1 unidade</b> ao produto. Bipe novamente para adicionar mais",
        "Ative o switch <b>Multiplos</b> para ler produtos em sequencia sem tocar em Escanear entre cada um",
        "Desative Multiplos quando for bipar o mesmo produto varias vezes seguidas (evita scan acidental)",
        "Apos cada scan bem-sucedido: o painel inferior mostra o nome do produto e o total acumulado",
    ])

    st.append(Paragraph("Tela de Scanner - Modo Bluetooth", s["h2"]))
    st.append(Paragraph(
        "Conecte o leitor de codigo de barras Bluetooth ao celular pelo menu de Bluetooth do Android "
        "(configuracoes do celular > Bluetooth > parear dispositivo). Apos pareado, toque no botao "
        "<b>BT</b> no scanner para mudar para o modo Bluetooth. O app captura os codigos automaticamente "
        "conforme o leitor os envia.", s["corpo"]))

    st.append(Paragraph("Tela de Scanner - Digitar Codigo Manualmente", s["h2"]))
    st.append(Paragraph(
        "Toque em <b>Digitar codigo</b> para abrir o teclado e informar o codigo manualmente. "
        "Util para codigos de barras danificados, ilegíveis ou muito pequenos para a camera.",
        s["corpo"]))

    st.append(Paragraph("Travamento do Operador", s["h2"]))
    st.append(Paragraph(
        "O campo <b>Operador</b> na tela de scanner fica travado apos a primeira bipagem da sessao. "
        "Isso garante que todos os scans da sessao fiquem registrados para o mesmo operador. "
        "Se precisar trocar de operador no meio da sessao, volte para a tela Inicial e selecione "
        "o novo operador antes de continuar bipando.", s["corpo"]))
    st.append(Paragraph(
        "Alerta de quantidade suspeita: se a quantidade bipada ultrapassar o dobro do estoque "
        "registrado no sistema (e o estoque for maior que 10 unidades), o app exibe um aviso "
        "pedindo confirmacao antes de registrar.", s["nota"]))

    st.append(Paragraph("Tela de Relatorio", s["h2"]))
    tabela(st, s,
        ["Coluna", "O que significa"],
        [
            ["Sistema", "Quantidade no Automec no momento do primeiro scan deste produto nesta sessao"],
            ["Contada", "Total de unidades bipadas ate agora para este produto"],
            ["Dif", "Contada menos Sistema. Verde = sobra, Vermelho = falta, Cinza = igual"],
        ],
        [3*cm, 12.5*cm],
    )
    lista(st, s, [
        "Toque num produto para <b>editar a quantidade</b> - e obrigatorio informar o motivo",
        "Deslize um produto para a esquerda ou direita para <b>remover</b> - motivo tambem obrigatorio",
        "O aviso no topo mostra quantos produtos com estoque positivo no sistema ainda nao foram bipados",
        "O botao <b>Recontagem</b> fica verde quando ha divergencias, indicando que e recomendada",
        "O botao <b>Consolidar</b> fecha o inventario e atualiza o Automec definitivamente",
    ])

    st.append(Paragraph("Tela de Recontagem", s["h2"]))
    st.append(Paragraph(
        "A recontagem permite fazer uma segunda passagem pelos produtos para confirmar os valores. "
        "O app bipa normalmente e compara a 1a e a 2a contagem lado a lado, destacando as diferencas.",
        s["corpo"]))
    st.append(Paragraph(
        "Se mais de 30% dos itens bipados tiverem divergencia com o estoque do sistema, "
        "a recontagem se torna <b>obrigatoria</b> antes de consolidar.", s["aviso"]))
    tabela(st, s,
        ["Opcao apos recontagem", "O que acontece"],
        [
            ["Consolidar agora", "Aplica os valores da 2a contagem e ja consolida no Automec"],
            ["Aplicar 2a contagem", "Atualiza o relatorio com os valores da 2a contagem para revisao final antes de consolidar"],
            ["Manter 1a contagem", "Descarta a 2a contagem e volta ao relatorio original"],
            ["Continuar recontando", "Fecha o dialogo e permite continuar bipando na mesma sessao de recontagem"],
        ],
        [4*cm, 11.5*cm],
    )

    st.append(Paragraph("Consolidacao", s["h2"]))
    st.append(Paragraph(
        "A consolidacao grava os dados definitivamente no Automec (tabela MOV_PRODUTO). "
        "<b>Esta operacao nao pode ser desfeita.</b>", s["aviso"]))
    lista(st, s, [
        "<b>Sem divergencias:</b> toque em Consolidar - nenhum supervisor e necessario",
        "<b>Com divergencias:</b> e exigido login e senha mobile de um gerente ou administrador para autorizar",
        "Operadores precisam de um gerente ou admin <b>diferente</b> para autorizar",
        "Gerentes e admins podem autorizar usando as proprias credenciais",
        "Se mais de 30% dos itens divergirem, a consolidacao e bloqueada ate que a recontagem seja feita",
    ])

    st.append(Paragraph("Tela de Historico", s["h2"]))
    st.append(Paragraph(
        "Exibe todas as consolidacoes ja realizadas para o deposito selecionado, com produto, "
        "quantidade contada, quantidade do sistema na epoca e data da consolidacao.", s["corpo"]))

    st.append(Paragraph("Tela de Auditoria (Gerentes e Admins)", s["h2"]))
    tabela(st, s,
        ["Tipo de evento", "O que significa"],
        [
            ["EDICAO", "Quantidade de um item foi alterada manualmente no relatorio"],
            ["EDICAO_SUSPEITA", "A edicao fez o valor contado coincidir exatamente com o estoque do sistema (possivel fraude)"],
            ["EXCLUSAO", "Item foi removido da contagem com justificativa"],
            ["CONSOLIDACAO", "Inventario consolidado no Automec com sucesso"],
            ["ALERTA", "Quantidade bipada muito acima do estoque esperado - requer confirmacao do operador"],
            ["ALERTA_REESCAN", "Um produto foi excluido e re-escaneado na mesma sessao - possivel tentativa de manipulacao"],
        ],
        [4*cm, 11.5*cm],
    )

    st.append(Paragraph("Tela de Operadores", s["h2"]))
    st.append(Paragraph(
        "Gerentes e admins podem cadastrar os operadores fisicos de coleta. "
        "Operadores aparecem na lista de selecao antes de comecar a bipar. "
        "Use Ativar/Desativar para controlar quem pode ser selecionado.", s["corpo"]))

    st.append(Paragraph("Tela de Usuarios (Admin Mobile)", s["h2"]))
    st.append(Paragraph(
        "Disponivel apenas para o admin mobile (geralmente o usuario MI e quem ele delegar). "
        "Exibe todos os usuarios do Automec e permite:", s["corpo"]))
    lista(st, s, [
        "<b>Definir / Alterar senha mobile</b> - todo usuario precisa de uma senha mobile separada para acessar o app",
        "<b>Dar admin mobile</b> - permite que outro usuario tambem gerencie senhas e acessos",
        "<b>Remover admin mobile</b> - revoga a permissao de administracao do app",
    ])

    doc.build(st)
    print(f"Manual gerado: {caminho}")


# ════════════════════════════════════════════════════════════════════════════
# DOCUMENTACAO TECNICA
# ════════════════════════════════════════════════════════════════════════════

def gerar_tecnico(caminho):
    doc = SimpleDocTemplate(caminho, pagesize=A4,
        leftMargin=MARGEM, rightMargin=MARGEM,
        topMargin=MARGEM, bottomMargin=MARGEM,
        title="Invec - Documentacao Tecnica")
    s = estilos()
    st = []

    capa(st, s, "Documentacao Tecnica",
         "Arquitetura, seguranca, banco de dados e endpoints")

    # ── Visao Geral ─────────────────────────────────────────────────────────
    st.append(Paragraph("Visao Geral da Arquitetura", s["h1"]))
    hr(st)
    st.append(Paragraph(
        "O Invec e um sistema cliente-servidor composto por dois componentes independentes: "
        "um <b>backend FastAPI</b> (Python) que roda como servico Windows e acessa o banco "
        "Firebird do Automec, e um <b>app Android</b> (Kotlin) que se comunica com o backend "
        "via HTTP/JSON pelo Wi-Fi interno da empresa.", s["corpo"]))
    code(st, s,
        "[Celulares Android]  <--HTTP/JSON/Wi-Fi-->  [InvecServidor.exe / Windows Service]\n"
        "                                                        |\n"
        "                                            [Firebird 5 / Banco Automec]")
    lista(st, s, [
        "Varios celulares operam simultaneamente no mesmo deposito",
        "Servidor registrado como servico Windows (InvecAPI via NSSM) - inicia automaticamente com o Windows",
        "Toda comunicacao e autenticada via JWT Bearer token no header Authorization",
        "Operacoes de escrita no banco usam UPDATE ... RETURNING atomico para evitar race conditions",
    ])

    # ── Stack ────────────────────────────────────────────────────────────────
    st.append(Paragraph("Stack Tecnologica", s["h1"]))
    hr(st)
    tabela(st, s,
        ["Camada", "Tecnologia", "Versao / Detalhe"],
        [
            ["Backend linguagem", "Python", "3.13"],
            ["Backend framework", "FastAPI + Uvicorn", "FastAPI 0.115+, Uvicorn ASGI"],
            ["Banco de dados", "Firebird 5 via firebird-driver", "Driver nativo Python, sem ODBC"],
            ["Distribuicao servidor", "PyInstaller + NSSM", "Single-file EXE + servico Windows"],
            ["App linguagem", "Kotlin", "JVM target 17"],
            ["App SDK minimo", "Android 8.0 (API 26)", "Target API 35"],
            ["HTTP client app", "Retrofit2 + OkHttp3", "Retrofit 2.11, OkHttp 4.x"],
            ["Camera / barcode", "CameraX + ML Kit Barcode Scanning", "CameraX 1.3+, ML Kit offline"],
            ["UI app", "Material Design 3 + ViewBinding", "Material 1.12+"],
            ["Autenticacao", "JWT HS256 (sessao)", "python-jose 3.3+"],
            ["Licenca", "JWT RS256 / RSA 2048-bit", "cryptography 41+"],
            ["Validacao dados backend", "Pydantic v2", "via FastAPI"],
        ],
        [4*cm, 5*cm, 6.5*cm],
    )

    # ── Estrutura ────────────────────────────────────────────────────────────
    st.append(Paragraph("Estrutura do Repositorio (Monorepo)", s["h1"]))
    hr(st)
    code(st, s,
        "inventario-app/\n"
        "  api/                      # backend Python\n"
        "    main.py                 # FastAPI app + lifespan (licenca + migrations)\n"
        "    server.py               # entrypoint Uvicorn para PyInstaller\n"
        "    instalador.py           # GUI Tkinter do instalador Windows\n"
        "    servidor.spec           # PyInstaller spec do servidor\n"
        "    instalador.spec         # PyInstaller spec do instalador\n"
        "    requirements.txt\n"
        "    app/\n"
        "      database.py           # get_connection() context manager Firebird\n"
        "      security.py           # JWT HS256, get_current_user(), roles\n"
        "      licenca.py            # validacao RSA 2048-bit (chave publica embutida)\n"
        "      migrations.py         # DDL idempotente executado no startup\n"
        "      models/schemas.py     # modelos Pydantic (request + response)\n"
        "      routers/\n"
        "        auth.py             # login, rate limit, usuarios mobile\n"
        "        depositos.py        # listagem de depositos\n"
        "        produtos.py         # busca por codigo de barras / descricao\n"
        "        inventario.py       # bipagem, relatorio, consolidacao, auditoria\n"
        "        operadores.py       # CRUD de operadores fisicos\n"
        "  app/                      # Android Kotlin\n"
        "    src/main/java/br/com/inventario/\n"
        "      ui/base/TimeoutActivity.kt\n"
        "      ui/login/LoginActivity.kt\n"
        "      ui/main/MainActivity.kt\n"
        "      ui/scanner/ScannerActivity.kt\n"
        "      ui/relatorio/RelatorioActivity.kt\n"
        "      ui/recontagem/RecontagemActivity.kt\n"
        "      ui/historico/HistoricoActivity.kt\n"
        "      ui/auditoria/AuditoriaActivity.kt\n"
        "      ui/operadores/OperadoresActivity.kt\n"
        "      ui/usuarios/UsuariosActivity.kt\n"
        "      data/api/ApiService.kt        # interface Retrofit com todos os endpoints\n"
        "      data/api/RetrofitClient.kt    # OkHttp + interceptor Bearer + interceptor 401\n"
        "      data/model/Models.kt          # data classes request/response\n"
        "      util/SessionManager.kt        # SharedPreferences (token, url, deposito, etc.)\n"
        "  docs/                     # documentacao PDF\n"
        "  README.md")

    # ── Autenticacao ─────────────────────────────────────────────────────────
    st.append(Paragraph("Autenticacao e Controle de Sessao", s["h1"]))
    hr(st)

    st.append(Paragraph("Login e JWT de sessao", s["h2"]))
    st.append(Paragraph(
        "POST /auth/login recebe login e senha. O backend busca o usuario em USUARIOS e tenta "
        "autenticar em ordem: primeiro compara com SENHAMOBILE (hash bcrypt, coluna adicionada pelo Invec); "
        "se nao existir, tenta SENHA (senha original do Automec em texto puro - fallback de compatibilidade). "
        "Em caso de sucesso retorna um JWT HS256 assinado com JWT_SECRET (definido no .env).", s["corpo"]))
    st.append(Paragraph("Payload do token JWT de sessao:", s["corpo"]))
    code(st, s,
        '{"sub": "123",           # IDUSUARIO do Automec\n'
        ' "login": "joao",\n'
        ' "role": "operador",     # operador | gerente | admin\n'
        ' "idgrupo": 3,           # 1=admin, 2=gerente, 3=operador\n'
        ' "mobile_admin": false,  # permissao de gestao do app\n'
        ' "exp": 1718000000}      # expiracao: 8h a partir do login')

    st.append(Paragraph("Rate limiting de login", s["h2"]))
    st.append(Paragraph(
        "Implementado com dicionarios em memoria (sem Redis). Dois contadores independentes "
        "por IP remoto e por login tentado. Ao atingir 5 falhas em 60 segundos, bloqueia "
        "por 300 segundos. O contador e zerado apos bloqueio expirar.", s["corpo"]))

    st.append(Paragraph("Inatividade no app (TimeoutActivity)", s["h2"]))
    st.append(Paragraph(
        "Todas as Activities do app herdam de TimeoutActivity. Ela usa um Handler + Runnable "
        "que dispara apos 15 minutos. Qualquer toque na tela (onUserInteraction) reinicia o timer. "
        "Ao expirar, chama SessionManager.logout() e redireciona para LoginActivity com flag "
        "FLAG_ACTIVITY_NEW_TASK | FLAG_ACTIVITY_CLEAR_TASK para limpar a pilha.", s["corpo"]))

    st.append(Paragraph("Interceptor 401 no OkHttp", s["h2"]))
    st.append(Paragraph(
        "RetrofitClient configura um Interceptor que monitora todas as respostas. Se receber "
        "HTTP 401 (token expirado ou invalido), automaticamente limpa a sessao no SessionManager "
        "e redireciona para LoginActivity. O usuario ve a mensagem 'Sessao expirada' e pode "
        "logar novamente sem perder os dados de bipagem (que ficam no servidor).", s["corpo"]))

    st.append(Paragraph("SessionManager - SharedPreferences", s["h2"]))
    st.append(Paragraph("Dados persistidos localmente no celular:", s["corpo"]))
    tabela(st, s,
        ["Chave", "Conteudo"],
        [
            ["auth_token", "JWT Bearer token da sessao atual"],
            ["server_url", "URL base do servidor (ex: http://192.168.1.31:8000/)"],
            ["deposito_id", "Codigo do deposito selecionado na sessao atual"],
            ["deposito_nome", "Nome do deposito para exibicao"],
            ["device_id", "UUID gerado na primeira instalacao do app - identifica o dispositivo nos logs"],
            ["usuario_login", "Login do usuario logado"],
            ["usuario_role", "Role do usuario (operador/gerente/admin)"],
            ["mobile_admin", "Flag se o usuario tem admin mobile"],
        ],
        [4*cm, 11.5*cm],
    )

    # ── Licenca RSA ──────────────────────────────────────────────────────────
    st.append(Paragraph("Sistema de Licenca RSA", s["h1"]))
    hr(st)
    st.append(Paragraph(
        "A licenca usa criptografia assimetrica RSA 2048-bit com algoritmo JWT RS256. "
        "A chave privada (licenca_privada.pem) fica exclusivamente com a Pontual Tecnologia "
        "e e usada para assinar as licencas. A chave publica e embutida diretamente em "
        "app/licenca.py durante o build - o cliente nunca tem acesso a ela explicitamente.", s["corpo"]))
    tabela(st, s,
        ["Artefato", "Localizacao", "Distribuir ao cliente?"],
        [
            ["licenca_privada.pem", "C:\\\\Administracao\\\\inventario-api\\\\", "NAO - nunca"],
            ["gerar_licenca.py", "C:\\\\Administracao\\\\inventario-api\\\\", "NAO - nunca"],
            ["Chave publica (embutida)", "Dentro do InvecServidor.exe compilado", "Sim (implicitamente)"],
            ["LICENSE_KEY (JWT)", "C:\\\\Invec\\\\.env no servidor do cliente", "Sim - via instalador"],
        ],
        [4*cm, 5.5*cm, 5.5*cm],
    )

    st.append(Paragraph("Payload da licenca JWT:", s["corpo"]))
    code(st, s,
        '{"produto":    "Invec",\n'
        ' "cliente":    "Nome da Empresa Ltda",\n'
        ' "cnpj":       "00.000.000/0001-00",\n'
        ' "emitida_em": "2026-06-19",\n'
        ' "expira_em":  ""}   # vazio = licenca permanente')
    st.append(Paragraph(
        "Validacao no startup: main.py chama validar_licenca() no lifespan antes de aceitar "
        "qualquer requisicao. Se invalida ou expirada, sys.exit(1) encerra o processo e o "
        "NSSM registra o erro no log.", s["nota"]))

    st.append(Paragraph("Gerar licenca para novo cliente:", s["corpo"]))
    code(st, s,
        "cd C:\\Administracao\\inventario-api\n"
        "python gerar_licenca.py\n"
        "# Preenche: nome do cliente, CNPJ, validade em meses (Enter = permanente)\n"
        "# Saida: LICENSE_KEY=eyJhbGciOiJSUzI1NiJ9...")

    # ── Banco de dados ───────────────────────────────────────────────────────
    st.append(Paragraph("Banco de Dados Firebird", s["h1"]))
    hr(st)

    st.append(Paragraph("Tabelas do Automec utilizadas (somente leitura e insercao controlada)", s["h2"]))
    tabela(st, s,
        ["Tabela", "Operacao", "Observacao"],
        [
            ["USUARIOS", "SELECT, UPDATE", "Colunas SENHAMOBILE e MOBILE_ADMIN adicionadas pelo Invec via migration"],
            ["DEPOSITO", "SELECT", "Listagem de depositos para selecao no app"],
            ["PRODUTO", "SELECT", "Descricao, unidade e codigo do produto"],
            ["PRODUTO_CODBARRA", "SELECT", "Tabela de codigos de barras alternativos (JOIN com PRODUTO)"],
            ["MOVIMENTO", "SELECT", "QTDEATUAL: quantidade atual em estoque por produto e deposito"],
            ["MOV_PRODUTO", "INSERT, SELECT", "Consolidacao grava aqui com TIPOMOVIMENTO=5. Trigger do Automec atualiza MOVIMENTO.QTDEATUAL."],
            ["SAIDAPRODUTO", "SELECT", "Pedidos de saida pendentes para CE (Considerar Entrega)"],
            ["SAIDAESTOQUE", "SELECT", "Detalhe dos itens dos pedidos de saida"],
            ["PRODUTOPRECO", "SELECT", "FATORCONV e VLCUSTO para calcular QTENTRADA/QTSAIDA no MOV_PRODUTO"],
        ],
        [4*cm, 2.5*cm, 9*cm],
    )

    st.append(Paragraph("Tabelas criadas pelo Invec (DDL automatico no startup)", s["h2"]))
    tabela(st, s,
        ["Tabela / Coluna", "Definicao e proposito"],
        [
            ["INVENTARIO_TEMP", "Sessao de contagem em andamento. Colunas: CDDEPOSITO, CDPRODUTO, PRODUTO, QTDE, QTDEATUAL_SNAP (snapshot no 1o scan), OPERADOR, DATA_HORA."],
            ["OPERADORES_APP", "Cadastro de operadores fisicos. Colunas: ID (autoincrement), NOME, ATIVO."],
            ["LOG_INVENTARIO", "Auditoria completa. Colunas: ID, TIPO, CDDEPOSITO, CDPRODUTO, PRODUTO, OPERADOR, LOGIN_USUARIO, QTDE_ANTES, QTDE_DEPOIS, MOTIVO, DEVICE_ID, DATA_HORA."],
            ["USUARIOS.SENHAMOBILE", "Hash bcrypt da senha mobile do usuario. NULL = usuario nao tem acesso ao app."],
            ["USUARIOS.MOBILE_ADMIN", "CHAR(1) 'S'/'N' - indica se o usuario pode gerenciar outros usuarios no app."],
        ],
        [4.5*cm, 11*cm],
    )

    # ── Roles e Permissoes ───────────────────────────────────────────────────
    st.append(Paragraph("Roles e Permissoes", s["h1"]))
    hr(st)
    tabela(st, s,
        ["Role", "IDGRUPO Automec", "O que pode fazer no Invec"],
        [
            ["admin", "1", "Tudo: bipar, ver relatorio, editar, remover, consolidar com auto-autorizacao, ver auditoria, gerenciar operadores"],
            ["gerente", "2", "Igual ao admin, exceto gestao de usuarios mobile (se nao for mobile_admin)"],
            ["operador", "3", "Bipar e ver relatorio. Consolidar com divergencias exige autorizacao de gerente ou admin diferente."],
            ["mobile_admin", "qualquer", "Flag adicional. Pode gerenciar senhas mobile e delegar admin mobile a outros usuarios."],
        ],
        [2.5*cm, 3*cm, 10*cm],
    )

    # ── Fluxo de Bipagem ─────────────────────────────────────────────────────
    st.append(Paragraph("Fluxo de Bipagem (POST /inventario/bipagem)", s["h1"]))
    hr(st)
    st.append(Paragraph(
        "O endpoint recebe: cdproduto, cddeposito, operador, device_id. "
        "Executa um UPDATE atomico com RETURNING para evitar race condition:", s["corpo"]))
    code(st, s,
        "UPDATE INVENTARIO_TEMP\n"
        "   SET QTDE = QTDE + 1, OPERADOR = :operador\n"
        " WHERE CDPRODUTO = :prod AND CDDEPOSITO = :dep\n"
        "RETURNING QTDE")
    lista(st, s, [
        "Se UPDATE retornar 1 linha: produto ja existe na sessao - quantidade incrementada",
        "Se UPDATE retornar 0 linhas: primeiro scan do produto - executa INSERT com QTDEATUAL_SNAP = estoque atual do MOVIMENTO",
        "QTDEATUAL_SNAP e gravado apenas uma vez (no primeiro scan) e nao e alterado depois",
        "Se QTDE > 2 x QTDEATUAL_SNAP e QTDEATUAL_SNAP >= 10: grava ALERTA no LOG_INVENTARIO e retorna flag alerta=true para o app mostrar aviso",
        "Se produto foi previamente excluido na sessao e re-escaneado: grava ALERTA_REESCAN no log",
    ])

    # ── Scanner Android ──────────────────────────────────────────────────────
    st.append(Paragraph("Implementacao do Scanner Android", s["h1"]))
    hr(st)

    st.append(Paragraph("Modo Camera (CameraX + ML Kit)", s["h2"]))
    st.append(Paragraph(
        "ScannerActivity usa CameraX ImageAnalysis com um BarcodeScanner do ML Kit configurado "
        "para os formatos: EAN-13, EAN-8, Code 128, Code 39, QR Code, ITF, Codabar. "
        "A analise roda em background thread via ExecutorService. Ao detectar um barcode, "
        "o resultado e postado no MainThread via runOnUiThread antes de chamar o endpoint.", s["corpo"]))
    lista(st, s, [
        "Modo simples (switch Multiplos desativado): camera fica pausada apos cada scan, reativa ao tocar em Escanear",
        "Modo multiplos (switch ativo): camera permanece analisando continuamente com debounce de 1.5s por codigo",
        "Preview da camera exibido em PreviewView com AspectRatio.RATIO_16_9",
    ])

    st.append(Paragraph("Modo Bluetooth (HID Keyboard emulation)", s["h2"]))
    st.append(Paragraph(
        "Leitores Bluetooth operam em modo HID (Human Interface Device), emulando um teclado. "
        "O app usa um EditText invisivel com requestFocus() para capturar o input. "
        "Um TextWatcher detecta quando o leitor envia o codigo completo (terminado com \\n ou \\r) "
        "e dispara o scan automaticamente sem interacao do usuario.", s["corpo"]))

    # ── Consolidacao ─────────────────────────────────────────────────────────
    st.append(Paragraph("Fluxo de Consolidacao (POST /inventario/consolidar)", s["h1"]))
    hr(st)
    lista(st, s, [
        "Busca todos os itens de INVENTARIO_TEMP para o deposito",
        "Consulta SAIDAPRODUTO + SAIDAESTOQUE para CE (Considerar Entrega). Envolvido em try/except para compatibilidade com versoes do Automec sem essas tabelas",
        "Calcula divergencias: item diverge se |qtde_contada - (qtdeatual + qtdeentrega)| > 0",
        "Se pct_divergencias >= 30% E total_itens >= 5: retorna HTTP 422 'Recontagem obrigatoria'",
        "Se ha divergencias: valida credenciais do supervisor (POST /auth/login interno com role >= gerente, diferente do operador se for operador)",
        "Adquire lock: _consolidando_lock (threading.Lock) + _consolidando_depositos (set). Retorna 409 se o deposito ja esta sendo consolidado",
        "Gera IDINVENTARIO unico via GEN_ID(GEN_MOV_PRODUTO, 1)",
        "Para cada item: INSERT em MOV_PRODUTO com TIPOMOVIMENTO=5, calculando QTENTRADA/QTSAIDA conforme logica CE",
        "O trigger TG_INSERT_MOV_PRODUTO do Automec atualiza MOVIMENTO.QTDEATUAL automaticamente",
        "DELETE FROM INVENTARIO_TEMP para o deposito na mesma transacao",
        "Grava CONSOLIDACAO no LOG_INVENTARIO e salva relatorio .txt em C:\\Invec\\relatorios\\",
        "Libera o lock",
    ])

    # ── Considerar Entrega ───────────────────────────────────────────────────
    st.append(Paragraph("Considerar Entrega (CE) - Logica de Calculo", s["h1"]))
    hr(st)
    st.append(Paragraph(
        "Pedidos de saida faturados mas ainda nao entregues representam estoque fisicamente "
        "presente mas ja comprometido. O Invec considera essa quantidade tanto no calculo de "
        "divergencias quanto na geracao do MOV_PRODUTO (replica a logica GravarMov_Produto_Entrega do Automec):",
        s["corpo"]))
    tabela(st, s,
        ["Cenario", "QTENTRADA", "QTSAIDA", "VL_PERDA_GANHO"],
        [
            ["Com entrega pendente e contado > atual", "contado - atual", "qtdeentrega", "NULL (Automec calcula)"],
            ["Com entrega pendente e contado < atual", "0", "(atual - contado) + qtdeentrega", "NULL"],
            ["Com entrega pendente e contado = atual", "0", "qtdeentrega", "NULL"],
            ["Sem entrega e contado > atual (ganho)", "contado - atual", "0", "(contado - atual) x vlcusto"],
            ["Sem entrega e contado < atual (perda)", "0", "atual - contado", "(contado - atual) x vlcusto (negativo)"],
            ["Sem entrega e contado = atual", "0", "0", "0 (registro de auditoria apenas)"],
        ],
        [5*cm, 3*cm, 3.5*cm, 4*cm],
    )
    st.append(Paragraph(
        "vlcusto vem de PRODUTOPRECO.VLCUSTO / PRODUTOPRECO.FATORCONV para o produto. "
        "A consulta CE e envolvida em try/except para degradar graciosamente em versoes "
        "antigas do Automec que nao possuem as tabelas SAIDAPRODUTO ou SAIDAESTOQUE.", s["nota"]))

    # ── Seguranca e Auditoria ────────────────────────────────────────────────
    st.append(Paragraph("Seguranca e Auditoria", s["h1"]))
    hr(st)
    tabela(st, s,
        ["Mecanismo", "Implementacao"],
        [
            ["Rate limit", "5 falhas em 60s -> bloqueio 300s. Dicts em memoria: {ip: [timestamps]} e {login: [timestamps]}. Nao persiste entre reinicializacoes do servidor."],
            ["JWT_SECRET", "String arbitraria de minimo 32 caracteres definida no .env. Assina todos os tokens de sessao HS256."],
            ["Supervisor obrigatorio", "Consolidacao com divergencias requer login/senha de gerente ou admin via endpoint de autenticacao interno. Operadores nao podem autorizar a si mesmos."],
            ["EDICAO_SUSPEITA", "Edicao detectada como suspeita quando qtde_nova == qtdeatual_snap (contagem passou a coincidir exatamente com o estoque do sistema)."],
            ["ALERTA_REESCAN", "Se produto tem registro de EXCLUSAO no LOG_INVENTARIO nas ultimas 12h para o mesmo deposito e o mesmo device_id re-escaneia: grava ALERTA_REESCAN."],
            ["ALERTA de quantidade", "qtde_nova > 2 * qtdeatual_snap AND qtdeatual_snap >= 10: grava ALERTA e retorna flag para o app exibir confirmacao."],
            ["device_id", "UUID v4 gerado na primeira abertura do app, salvo em SharedPreferences. Gravado em todos os eventos do LOG_INVENTARIO para rastreabilidade por dispositivo."],
            ["Retencao de logs", "run_migrations() remove: LOG com TIPO=BIPAGEM com mais de 90 dias; demais logs com mais de 365 dias; EDICAO_SUSPEITA e ALERTA_REESCAN mantidos permanentemente."],
        ],
        [4.5*cm, 11*cm],
    )

    # ── Endpoints ────────────────────────────────────────────────────────────
    st.append(Paragraph("Endpoints da API", s["h1"]))
    hr(st)
    tabela(st, s,
        ["Metodo", "Rota", "Descricao", "Acesso minimo"],
        [
            ["POST", "/auth/login", "Autenticacao com rate limit. Retorna JWT.", "Publico"],
            ["GET",  "/auth/usuarios", "Lista usuarios do Automec com flags mobile.", "mobile_admin"],
            ["PUT",  "/auth/usuarios/{id}/senha-mobile", "Define ou altera senha mobile (hash bcrypt).", "mobile_admin"],
            ["PUT",  "/auth/usuarios/{id}/toggle-admin", "Ativa/desativa mobile_admin. So usuario MI pode executar.", "Usuario MI"],
            ["GET",  "/depositos", "Lista depositos do Automec.", "Autenticado"],
            ["GET",  "/produtos/barcode/{codigo}", "Busca produto pelo codigo de barras (PRODUTO_CODBARRA e PRODUTO).", "Autenticado"],
            ["GET",  "/produtos/busca?q=", "Busca produto por descricao parcial.", "Autenticado"],
            ["POST", "/inventario/bipagem", "Registra scan atomico. Retorna qtde acumulada e flag de alerta.", "Autenticado"],
            ["GET",  "/inventario/relatorio/{dep}", "Lista itens de INVENTARIO_TEMP para o deposito.", "Autenticado"],
            ["GET",  "/inventario/resumo/{dep}", "Lista produtos com estoque > 0 que ainda nao foram bipados.", "Autenticado"],
            ["PUT",  "/inventario/bipagem/{id}", "Edita quantidade de um item. Grava EDICAO ou EDICAO_SUSPEITA no log.", "Autenticado"],
            ["DELETE","/inventario/bipagem/{id}", "Remove item da contagem. Grava EXCLUSAO no log.", "Autenticado"],
            ["POST", "/inventario/consolidar", "Consolida no Automec com validacao de divergencias e supervisor.", "Autenticado"],
            ["GET",  "/inventario/historico/{dep}", "Lista consolidacoes anteriores (MOV_PRODUTO com TIPOMOVIMENTO=5).", "Autenticado"],
            ["GET",  "/inventario/log/{dep}", "Log de auditoria do deposito (LOG_INVENTARIO).", "Gerente/Admin"],
            ["GET",  "/operadores", "Lista operadores cadastrados em OPERADORES_APP.", "Autenticado"],
            ["POST", "/operadores", "Cria novo operador.", "Gerente/Admin"],
            ["PUT",  "/operadores/{id}/toggle", "Ativa ou desativa um operador.", "Gerente/Admin"],
        ],
        [1.7*cm, 5.3*cm, 6.2*cm, 3*cm],
    )

    # ── Migrations ───────────────────────────────────────────────────────────
    st.append(Paragraph("Migrations Automaticas (run_migrations)", s["h1"]))
    hr(st)
    st.append(Paragraph(
        "Executadas no lifespan do FastAPI antes de aceitar requisicoes. "
        "Cada operacao e idempotente: verifica se ja existe antes de criar/alterar.", s["corpo"]))
    lista(st, s, [
        "CREATE TABLE INVENTARIO_TEMP se nao existir",
        "ALTER TABLE INVENTARIO_TEMP ADD COLUMN OPERADOR se nao existir",
        "ALTER TABLE INVENTARIO_TEMP ADD COLUMN QTDEATUAL_SNAP se nao existir",
        "CREATE TABLE OPERADORES_APP se nao existir",
        "ALTER TABLE USUARIOS ADD COLUMN SENHAMOBILE se nao existir",
        "ALTER TABLE USUARIOS ADD COLUMN MOBILE_ADMIN CHAR(1) DEFAULT 'N' se nao existir",
        "CREATE TABLE LOG_INVENTARIO se nao existir",
        "CREATE INDEX IDX_LOG_INV_DEPOSITO, IDX_LOG_INV_DATA, IDX_INVTEMP_PROD_DEP, IDX_LOG_INV_TIPO",
        "DELETE logs expirados conforme politica de retencao",
        r"DELETE arquivos .txt em C:\Invec\relatorios\ com mais de 180 dias",
    ])

    # ── Build ────────────────────────────────────────────────────────────────
    st.append(Paragraph("Build e Distribuicao", s["h1"]))
    hr(st)

    st.append(Paragraph("Servidor Windows", s["h2"]))
    code(st, s,
        "cd C:\\Administracao\\inventario-api\n\n"
        "# 1. Compilar o servidor\n"
        "pyinstaller servidor.spec --clean --noconfirm\n"
        "# -> dist/InvecServidor.exe  (~21 MB, single-file)\n\n"
        "# 2. Compilar o instalador (bundla InvecServidor.exe + nssm.exe)\n"
        "pyinstaller instalador.spec --clean --noconfirm\n"
        "# -> dist/Instalar-Invec.exe (~32 MB, entrega ao cliente)")
    st.append(Paragraph(
        "O instalador.spec usa datas=[(InvecServidor.exe, '.'), (nssm.exe, '.')] para incluir "
        "os binarios. O cliente recebe apenas Instalar-Invec.exe - sem Python nem dependencias.",
        s["corpo"]))

    st.append(Paragraph("Gerar nova licenca para cliente", s["h2"]))
    code(st, s,
        "python gerar_licenca.py\n"
        "# -> imprime: LICENSE_KEY=eyJhbGciOiJSUzI1NiJ9...\n"
        "# Enviar esta string ao cliente para colar no campo do instalador")

    st.append(Paragraph("App Android", s["h2"]))
    code(st, s,
        "cd C:\\Administracao\\inventario-app\n\n"
        ".\\gradlew assembleRelease\n"
        "# -> app/build/outputs/apk/release/app-release.apk\n\n"
        "# APK assinado com keystore em app/release/invec-app.jks\n"
        "# Configuracoes de assinatura em app/build.gradle (signingConfigs)")
    st.append(Paragraph(
        "O build usa R8 (ProGuard) para minificacao e ofuscacao do bytecode. "
        "A keystore NAO e commitada no git.", s["corpo"]))

    doc.build(st)
    print(f"Tecnico gerado: {caminho}")


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    out = os.path.dirname(os.path.abspath(__file__))
    gerar_manual(os.path.join(out, "Invec_Manual.pdf"))
    gerar_tecnico(os.path.join(out, "Invec_Tecnico.pdf"))
    print("Concluido.")


