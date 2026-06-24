package br.com.inventario.util

import br.com.inventario.data.api.RetrofitClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

object ServerMonitor {

    private val _isOnline = MutableStateFlow(false)
    val isOnline: StateFlow<Boolean> get() = _isOnline

    private var job: Job? = null

    fun startOrKeep(session: SessionManager, scope: CoroutineScope) {
        if (job?.isActive == true) return
        job = scope.launch {
            while (true) {
                val ok = try {
                    val api = RetrofitClient.build(session)
                    api.ping().isSuccessful
                } catch (_: Exception) { false }
                _isOnline.value = ok
                delay(8_000)
            }
        }
    }

    /** UX-2: força ping imediato em vez de aguardar o ciclo de 30s. */
    fun forcePing(session: SessionManager, scope: CoroutineScope) {
        scope.launch {
            val ok = try {
                val api = RetrofitClient.build(session)
                api.ping().isSuccessful
            } catch (_: Exception) { false }
            _isOnline.value = ok
        }
    }

    fun reset() {
        job?.cancel()
        job = null
        _isOnline.value = false
    }
}
