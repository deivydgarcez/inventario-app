package br.com.inventario.data.repository

import br.com.inventario.data.api.ApiService
import br.com.inventario.data.db.InvecDatabase
import br.com.inventario.data.db.ProdutoCache
import br.com.inventario.data.model.ProdutoCatalogoItem
import br.com.inventario.util.SessionManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class CatalogoRepository(
    private val db: InvecDatabase,
    private val api: ApiService,
    private val session: SessionManager? = null,
) {
    suspend fun sincronizarCatalogo(
        cddeposito: Int,
        onProgresso: (baixados: Int, total: Int) -> Unit = { _, _ -> },
    ) {
        session?.saveCatalogoCompleto(cddeposito, false)
        var pagina = 1
        var baixados = 0
        while (true) {
            val resp = api.catalogo(cddeposito, pagina, 500)
            if (!resp.isSuccessful) break
            val body = resp.body() ?: break
            // BUG-3: evita loop infinito se o servidor retornar 0 itens mas paginas > pagina
            if (body.itens.isEmpty()) break
            withContext(Dispatchers.IO) {
                db.catalogo.upsertBatch(body.itens.map { it.toCache(cddeposito) })
            }
            baixados += body.itens.size
            onProgresso(baixados, body.total)
            if (pagina >= body.paginas) {
                session?.saveCatalogoCompleto(cddeposito, true)
                break
            }
            pagina++
        }
    }

    fun countCached(cddeposito: Int): Int = db.catalogo.count(cddeposito)
}

fun ProdutoCatalogoItem.toCache(cddeposito: Int) = ProdutoCache(
    codigobarra = codigobarra ?: "",
    cddeposito  = cddeposito,
    cdproduto   = cdproduto,
    produto     = produto,
    qtdeatual   = qtdeatual,
)
