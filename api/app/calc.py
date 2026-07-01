def calcular_delta_estoque(
    qtde_contada: float,
    qtde_atual: float,
    qtdeentrega: float,
    vlcusto: float,
) -> tuple[float, float, float, float, float]:
    """
    Calcula os campos de movimentação para MOV_PRODUTO a partir dos valores de contagem.

    Retorna: (qtdanterior, qtentrada, qtsaida, vl_perda_ganho, baseline_report)

    - qtdanterior    = MOVIMENTO.QTDEATUAL real (nunca inclui qtdeentrega)
    - qtentrada      = ganho de estoque disponível
    - qtsaida        = perda de estoque disponível
    - vl_perda_ganho = valor financeiro do ajuste
    - baseline_report = qtde_atual + qtdeentrega (usado no relatório de divergências)
    """
    qtdanterior = qtde_atual
    baseline_report = qtde_atual + qtdeentrega

    if qtdeentrega > 0:
        effective = qtde_contada - qtdeentrega
        if effective > qtde_atual:
            qtentrada = effective - qtde_atual
            qtsaida   = 0.0
        elif effective < qtde_atual:
            qtentrada = 0.0
            qtsaida   = qtde_atual - effective
        else:
            qtentrada = 0.0
            qtsaida   = 0.0
        vl_perda_ganho = round((effective - qtde_atual) * vlcusto, 2)
    else:
        if qtde_contada > qtde_atual:
            qtentrada = qtde_contada - qtde_atual
            qtsaida   = 0.0
        elif qtde_contada < qtde_atual:
            qtentrada = 0.0
            qtsaida   = qtde_atual - qtde_contada
        else:
            qtentrada = 0.0
            qtsaida   = 0.0
        vl_perda_ganho = round((qtde_contada - qtde_atual) * vlcusto, 2)

    return qtdanterior, qtentrada, qtsaida, vl_perda_ganho, baseline_report
