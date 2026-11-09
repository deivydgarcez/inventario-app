APP_VERSION = "1.9.8"

CHANGELOG = {
    "1.9.8": [
        "Correção: consolidação ficava em loop pedindo login do supervisor (senha mobile não podia ser cadastrada)",
        "Supervisor autoriza com a senha mobile ou com a mesma senha do Automec",
    ],
    "1.9.7": [
        "Correção: consolidação falhava com erro de chave estrangeira (FK_MP_PRODUTO) para produtos com CDPRODUTO iniciando em zero",
    ],
    "1.9.6": [
        "Correção: produtos com código iniciando em zero não eram registrados na bipagem (relatório vazio)",
    ],
    "1.9.5": [
        "Correção: produtos com código iniciando em zero (ex: 000646) causavam erro ao editar/excluir",
    ],
    "1.9.4": [
        "Endpoint /versao exibe novidades da versão atual no app",
    ],
    "1.9.3": [
        "Auto-atualização automática do servidor (InvecAutoUpdate)",
        "Licença vinculada ao ID da máquina",
        "Produto sem código de barras: suporte a entrada manual",
    ],
    "1.9.2": [
        "Correção no relatório de diferença de estoque",
        "Melhoria na estabilidade da conexão com Firebird remoto",
    ],
    "1.9.1": [
        "Sistema de licença RSA com expiração e vínculo por máquina",
        "Instalador com campo de chave de licença e ID da máquina",
        "Logs de serviço com rotação automática (10 MB)",
    ],
}
