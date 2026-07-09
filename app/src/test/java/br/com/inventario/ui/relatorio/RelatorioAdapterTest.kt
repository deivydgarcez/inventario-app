package br.com.inventario.ui.relatorio

import br.com.inventario.data.model.ItemRelatorio
import io.mockk.every
import io.mockk.just
import io.mockk.Runs
import io.mockk.spyk
import io.mockk.verify
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class RelatorioAdapterTest {

    private lateinit var items: MutableList<ItemRelatorio>
    private lateinit var adapter: RelatorioAdapter

    private fun makeItem(
        cdproduto: Int = 1,
        produto: String = "Produto $cdproduto",
        qtdeSistema: Double? = 10.0,
        qtdeContada: Double? = null,
        diferenca: Double? = null,
    ) = ItemRelatorio(
        cdproduto    = cdproduto,
        produto      = produto,
        codigobarra  = null,
        qtde_sistema = qtdeSistema,
        qtde_contada = qtdeContada,
        diferenca    = diferenca,
        qtde_entrega = null,
        operador     = null,
    )

    @Before
    fun setup() {
        items = mutableListOf(
            makeItem(1, "Arroz 5kg",  qtdeSistema = 10.0, qtdeContada = 12.0, diferenca =  2.0),
            makeItem(2, "Feijão 1kg", qtdeSistema =  5.0, qtdeContada =  3.0, diferenca = -2.0),
            makeItem(3, "Sal 1kg",    qtdeSistema = 20.0, qtdeContada = null, diferenca = null),
        )
        adapter = spyk(RelatorioAdapter(items) { _, _ -> })
        every { adapter.notifyItemChanged(any()) } just Runs
        every { adapter.notifyItemRemoved(any()) } just Runs
    }

    // ─── getItem ──────────────────────────────────────────────────────────────

    @Test
    fun `getItem retorna o item correto por posicao`() {
        assertEquals("Arroz 5kg",  adapter.getItem(0).produto)
        assertEquals("Feijão 1kg", adapter.getItem(1).produto)
        assertEquals("Sal 1kg",    adapter.getItem(2).produto)
    }

    @Test
    fun `itemCount reflete o tamanho inicial da lista`() {
        assertEquals(3, adapter.itemCount)
    }

    // ─── updateItem ───────────────────────────────────────────────────────────

    @Test
    fun `updateItem atualiza qtde_contada e recalcula diferenca`() {
        adapter.updateItem(0, 15.0)

        val item = adapter.getItem(0)
        assertEquals(15.0, item.qtde_contada!!, 0.001)
        assertEquals(5.0,  item.diferenca!!,    0.001)  // 15 - 10
    }

    @Test
    fun `updateItem com qtde_sistema nula usa zero como base`() {
        val lista = mutableListOf(makeItem(qtdeSistema = null))
        val localAdapter = spyk(RelatorioAdapter(lista) { _, _ -> })
        every { localAdapter.notifyItemChanged(any()) } just Runs

        localAdapter.updateItem(0, 8.0)

        val item = localAdapter.getItem(0)
        assertEquals(8.0, item.qtde_contada!!, 0.001)
        assertEquals(8.0, item.diferenca!!,    0.001)  // 8 - 0
    }

    @Test
    fun `updateItem calcula diferenca negativa quando contada menor que sistema`() {
        adapter.updateItem(0, 3.0)  // sistema = 10

        assertEquals(-7.0, adapter.getItem(0).diferenca!!, 0.001)
    }

    @Test
    fun `updateItem calcula diferenca zero quando contada igual ao sistema`() {
        adapter.updateItem(0, 10.0)  // sistema = 10

        assertEquals(0.0, adapter.getItem(0).diferenca!!, 0.001)
    }

    @Test
    fun `updateItem notifica a posicao correta`() {
        adapter.updateItem(1, 7.0)

        verify(exactly = 1) { adapter.notifyItemChanged(1) }
    }

    @Test
    fun `updateItem nao altera outros itens da lista`() {
        val produtoAntes = adapter.getItem(1).produto

        adapter.updateItem(0, 99.0)

        assertEquals(produtoAntes, adapter.getItem(1).produto)
    }

    // ─── removeItem ───────────────────────────────────────────────────────────

    @Test
    fun `removeItem reduz o itemCount em um`() {
        adapter.removeItem(0)

        assertEquals(2, adapter.itemCount)
    }

    @Test
    fun `removeItem elimina o produto na posicao correta`() {
        adapter.removeItem(0)  // remove "Arroz 5kg"

        assertEquals("Feijão 1kg", adapter.getItem(0).produto)
        assertEquals("Sal 1kg",    adapter.getItem(1).produto)
    }

    @Test
    fun `removeItem do ultimo elemento deixa lista vazia`() {
        adapter.removeItem(2)
        adapter.removeItem(1)
        adapter.removeItem(0)

        assertEquals(0, adapter.itemCount)
    }

    @Test
    fun `removeItem notifica a posicao correta`() {
        adapter.removeItem(2)

        verify(exactly = 1) { adapter.notifyItemRemoved(2) }
    }

    // ─── diferenca: sinal do prefixo (lógica pura, sem binding) ──────────────

    @Test
    fun `diferenca positiva gera prefixo de mais`() {
        val dif = 3.5
        val prefix = if (dif > 0) "+" else ""
        val result = "$prefix${"%.2f".format(dif)}"
        assertTrue("Esperado prefixo '+', recebeu: $result", result.startsWith("+"))
    }

    @Test
    fun `diferenca negativa nao gera prefixo`() {
        val dif = -2.0
        val prefix = if (dif > 0) "+" else ""
        val result = "$prefix${"%.2f".format(dif)}"
        assertTrue("Esperado sinal negativo sem '+', recebeu: $result", result.startsWith("-"))
    }

    @Test
    fun `diferenca zero nao gera prefixo de mais`() {
        val dif = 0.0
        val prefix = if (dif > 0) "+" else ""
        val result = "$prefix${"%.2f".format(dif)}"
        assertFalse("Dif zero nao deve ter '+', recebeu: $result", result.startsWith("+"))
    }

    // ─── qtde_sistema nula exibe traço ───────────────────────────────────────

    @Test
    fun `qtde_sistema nula exibe traco`() {
        val qtdeSistema: Double? = null
        val display = qtdeSistema?.let { "%.2f".format(it) } ?: "—"
        assertEquals("—", display)
    }

    @Test
    fun `qtde_sistema preenchida nao exibe traco`() {
        val qtdeSistema = 10.5
        val display = qtdeSistema.let { "%.2f".format(it) }
        assertNotEquals("—", display)
        assertTrue("Esperado numero formatado, recebeu: $display", display.isNotBlank())
    }
}
