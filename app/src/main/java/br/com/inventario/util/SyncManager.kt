package br.com.inventario.util

import br.com.inventario.data.api.ApiService
import br.com.inventario.data.api.RetrofitClient
import br.com.inventario.data.db.InvecDatabase
import br.com.inventario.data.model.BipagemLoteItem
import br.com.inventario.data.model.LoteBipagemRequest
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.filter
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.util.UUID

object SyncManager {

    // Exposto para ScannerActivity serializar edições com a sincronização (bug race condition)
    val mutex = Mutex()

    fun observarESync(db: InvecDatabase, session: SessionManager, scope: CoroutineScope) {
        // Dispara na transição offline→online
        scope.launch {
            ServerMonitor.isOnline
                .filter { it }
                .collect { sincronizarPendentes(db, session) }
        }
        // Retry periódico enquanto online (cobre falhas de POST que não causaram transição)
        scope.launch {
            while (true) {
                kotlinx.coroutines.delay(60_000)
                if (ServerMonitor.isOnline.value) sincronizarPendentes(db, session)
            }
        }
    }

    suspend fun sincronizarPendentes(db: InvecDatabase, session: SessionManager) {
        // withLock: se já há um sync em andamento (ex: observarESync), aguarda ao invés de pular.
        // Isso evita a race condition onde carregarRelatorio busca o relatório antes do sync terminar.
        mutex.withLock {
            val cddeposito = session.getCdDeposito()
            if (cddeposito == -1) return@withLock

            val pendentes = db.bipag.getNaoSincronizados(cddeposito)
            if (pendentes.isEmpty()) return@withLock

            val bySession = pendentes.groupBy { it.sessionId }
            val api: ApiService = try { RetrofitClient.build(session) } catch (_: Exception) { return@withLock }

            for ((sid, items) in bySession) {
                val lote = items
                    .groupBy { it.cdproduto }
                    .map { (cdproduto, scans) ->
                        val qtdeSistema = db.bipag.getQtdeSistema(cdproduto, sid)
                            ?: scans.first().qtdeSistema
                        BipagemLoteItem(
                            cdproduto    = cdproduto,
                            produto      = scans.first().produto,
                            qtde         = scans.sumOf { it.qtde },
                            qtde_sistema = qtdeSistema,
                            operador     = scans.first().operador,
                            device_id    = scans.first().deviceId,
                            timestamp    = scans.minOf { it.timestamp },
                        )
                    }

                try {
                    val loteId = UUID.randomUUID().toString()
                    api.sincronizarLote(LoteBipagemRequest(sid, cddeposito, lote, loteId))
                    db.bipag.marcarSincronizados(items.map { it.id })
                } catch (_: Exception) {
                    // deixa pendente para o próximo ciclo
                }
            }
        }
    }
}
