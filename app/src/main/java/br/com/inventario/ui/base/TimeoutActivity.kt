package br.com.inventario.ui.base

import android.content.Intent
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import br.com.inventario.data.api.RetrofitClient
import br.com.inventario.ui.login.LoginActivity
import br.com.inventario.util.SessionManager
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

private const val TIMEOUT_MS = 15 * 60 * 1000L  // 15 minutos

abstract class TimeoutActivity : AppCompatActivity() {

    private var timeoutJob: Job? = null

    override fun onResume() {
        super.onResume()
        resetTimeout()
    }

    override fun onPause() {
        super.onPause()
        timeoutJob?.cancel()
    }

    override fun onUserInteraction() {
        super.onUserInteraction()
        resetTimeout()
    }

    private fun resetTimeout() {
        timeoutJob?.cancel()
        timeoutJob = lifecycleScope.launch {
            delay(TIMEOUT_MS)
            onSessionTimeout()
        }
    }

    open fun onSessionTimeout() {
        val session = SessionManager(this)
        session.logout()
        RetrofitClient.reset()
        startActivity(Intent(this, LoginActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            putExtra("timeout", true)
        })
        finish()
    }
}
