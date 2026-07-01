"""
Testes da lógica de cálculo de delta de estoque na consolidação.

Por que esses testes existem:
- Em 2026-07-01 foi corrigido um bug crítico: QTDANTERIOR incluía qtdeentrega,
  fazendo o trigger do Automec ajustar MOVIMENTO para o total físico em vez
  de manter o disponível. Esses testes garantem que o bug não volte.
"""

import pytest
from app.routers.inventario import _calcular_delta_estoque


# ─── Cenários SEM entrega pendente ───────────────────────────────────────────

class TestSemEntrega:

    def test_contagem_exata_nenhum_movimento(self):
        """Contou exatamente o que o sistema tem — nenhum ajuste."""
        qtdanterior, qtentrada, qtsaida, vl, baseline = _calcular_delta_estoque(
            qtde_contada=6.0, qtde_atual=6.0, qtdeentrega=0.0, vlcusto=10.0
        )
        assert qtdanterior == 6.0
        assert qtentrada   == 0.0
        assert qtsaida     == 0.0
        assert vl          == 0.0
        assert baseline    == 6.0

    def test_ganho_de_estoque(self):
        """Contou mais do que o sistema — entrada de 3 unidades."""
        qtdanterior, qtentrada, qtsaida, vl, baseline = _calcular_delta_estoque(
            qtde_contada=9.0, qtde_atual=6.0, qtdeentrega=0.0, vlcusto=10.0
        )
        assert qtdanterior == 6.0
        assert qtentrada   == 3.0
        assert qtsaida     == 0.0
        assert vl          == 30.0   # +3 × R$10
        assert baseline    == 6.0

    def test_perda_de_estoque(self):
        """Contou menos do que o sistema — saída de 3 unidades."""
        qtdanterior, qtentrada, qtsaida, vl, baseline = _calcular_delta_estoque(
            qtde_contada=3.0, qtde_atual=6.0, qtdeentrega=0.0, vlcusto=10.0
        )
        assert qtdanterior == 6.0
        assert qtentrada   == 0.0
        assert qtsaida     == 3.0
        assert vl          == -30.0  # -3 × R$10
        assert baseline    == 6.0


# ─── Cenários COM entrega pendente ───────────────────────────────────────────

class TestComEntrega:

    def test_bug_corrigido_contagem_bate_sistema(self):
        """
        Cenário exato do bug de 2026-07-01:
        MOVIMENTO=6, entrega=4, usuário contou 10 (físico completo).
        Não deve gerar nenhum ajuste em MOVIMENTO.
        QTDANTERIOR deve ser 6 (não 10).
        """
        qtdanterior, qtentrada, qtsaida, vl, baseline = _calcular_delta_estoque(
            qtde_contada=10.0, qtde_atual=6.0, qtdeentrega=4.0, vlcusto=50.0
        )
        assert qtdanterior == 6.0   # nunca inclui entrega
        assert qtentrada   == 0.0   # effective=10-4=6 == qtde_atual → sem movimento
        assert qtsaida     == 0.0
        assert vl          == 0.0
        assert baseline    == 10.0  # relatório mostra total físico

    def test_ganho_de_estoque_disponivel(self):
        """Contou 11 físico com 4 em entrega → disponível efetivo=7 > 6 → ganhou 1."""
        qtdanterior, qtentrada, qtsaida, vl, baseline = _calcular_delta_estoque(
            qtde_contada=11.0, qtde_atual=6.0, qtdeentrega=4.0, vlcusto=50.0
        )
        assert qtdanterior == 6.0
        assert qtentrada   == 1.0   # effective=7 - qtde_atual=6
        assert qtsaida     == 0.0
        assert vl          == 50.0  # +1 × R$50
        assert baseline    == 10.0

    def test_perda_de_estoque_disponivel(self):
        """Contou 9 físico com 4 em entrega → disponível efetivo=5 < 6 → perdeu 1."""
        qtdanterior, qtentrada, qtsaida, vl, baseline = _calcular_delta_estoque(
            qtde_contada=9.0, qtde_atual=6.0, qtdeentrega=4.0, vlcusto=50.0
        )
        assert qtdanterior == 6.0
        assert qtentrada   == 0.0
        assert qtsaida     == 1.0   # qtde_atual=6 - effective=5
        assert vl          == -50.0  # -1 × R$50
        assert baseline    == 10.0

    def test_qtdanterior_nunca_inclui_entrega(self):
        """Propriedade fundamental: QTDANTERIOR = MOVIMENTO.QTDEATUAL sempre."""
        for qtdeentrega in [1.0, 4.0, 10.0, 100.0]:
            qtdanterior, *_ = _calcular_delta_estoque(
                qtde_contada=6.0 + qtdeentrega,
                qtde_atual=6.0,
                qtdeentrega=qtdeentrega,
                vlcusto=0.0,
            )
            assert qtdanterior == 6.0, (
                f"QTDANTERIOR deveria ser 6.0 com qtdeentrega={qtdeentrega}, "
                f"mas foi {qtdanterior}"
            )

    def test_baseline_report_inclui_entrega(self):
        """baseline_report = qtde_atual + qtdeentrega (total físico para o relatório)."""
        _, _, _, _, baseline = _calcular_delta_estoque(
            qtde_contada=10.0, qtde_atual=6.0, qtdeentrega=4.0, vlcusto=0.0
        )
        assert baseline == 10.0

    def test_vl_perda_ganho_sobre_disponivel(self):
        """O valor financeiro é calculado sobre o disponível (effective), não o físico."""
        _, _, _, vl, _ = _calcular_delta_estoque(
            qtde_contada=11.0, qtde_atual=6.0, qtdeentrega=4.0, vlcusto=100.0
        )
        # effective=7, ganho=1 unidade × R$100
        assert vl == 100.0


# ─── Casos de borda ───────────────────────────────────────────────────────────

class TestCasosDeBorda:

    def test_estoque_zero_sem_entrega(self):
        """Produto com estoque zero — contou 5 → entrada de 5."""
        qtdanterior, qtentrada, qtsaida, vl, baseline = _calcular_delta_estoque(
            qtde_contada=5.0, qtde_atual=0.0, qtdeentrega=0.0, vlcusto=20.0
        )
        assert qtdanterior == 0.0
        assert qtentrada   == 5.0
        assert qtsaida     == 0.0
        assert vl          == 100.0

    def test_estoque_zero_com_entrega(self):
        """Produto com MOVIMENTO=0 mas 3 em entrega — contou 3 → sem ajuste."""
        qtdanterior, qtentrada, qtsaida, vl, baseline = _calcular_delta_estoque(
            qtde_contada=3.0, qtde_atual=0.0, qtdeentrega=3.0, vlcusto=20.0
        )
        assert qtdanterior == 0.0
        assert qtentrada   == 0.0
        assert qtsaida     == 0.0
        assert vl          == 0.0
        assert baseline    == 3.0

    def test_vlcusto_zero_vl_perda_ganho_zero(self):
        """Produto sem preço de custo — vl_perda_ganho deve ser 0, não None."""
        _, _, _, vl, _ = _calcular_delta_estoque(
            qtde_contada=10.0, qtde_atual=6.0, qtdeentrega=0.0, vlcusto=0.0
        )
        assert vl == 0.0

    def test_arredondamento_vl_perda_ganho(self):
        """vl_perda_ganho é arredondado para 2 casas decimais."""
        _, _, _, vl, _ = _calcular_delta_estoque(
            qtde_contada=7.0, qtde_atual=6.0, qtdeentrega=0.0, vlcusto=1.005
        )
        assert vl == round(1.0 * 1.005, 2)
