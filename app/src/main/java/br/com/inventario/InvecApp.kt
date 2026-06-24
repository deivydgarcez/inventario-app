package br.com.inventario

import android.app.Application
import androidx.appcompat.app.AppCompatDelegate
import br.com.inventario.util.SessionManager

class InvecApp : Application() {
    override fun onCreate() {
        super.onCreate()
        val session = SessionManager(this)
        AppCompatDelegate.setDefaultNightMode(
            if (session.isDarkMode()) AppCompatDelegate.MODE_NIGHT_YES
            else AppCompatDelegate.MODE_NIGHT_NO
        )
    }
}
