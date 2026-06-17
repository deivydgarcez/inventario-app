package br.com.inventario.util

import android.content.Context
import br.com.inventario.BuildConfig
import androidx.core.content.edit

class SessionManager(context: Context) {

    private val prefs = context.getSharedPreferences("inventario_prefs", Context.MODE_PRIVATE)

    fun saveLogin(token: String, usuario: String, nome: String) {
        prefs.edit {
            putString("token", token)
                .putString("usuario", usuario)
                .putString("nome", nome)
        }
    }

    fun getToken(): String? = prefs.getString("token", null)
    fun getUsuario(): String? = prefs.getString("usuario", null)
    fun getNome(): String? = prefs.getString("nome", null)
    fun isLoggedIn(): Boolean = getToken() != null

    fun saveDeposito(cddeposito: Int, nomeDeposito: String) {
        prefs.edit {
            putInt("cddeposito", cddeposito)
                .putString("nome_deposito", nomeDeposito)
        }
    }

    fun getCdDeposito(): Int = prefs.getInt("cddeposito", -1)
    fun getNomeDeposito(): String? = prefs.getString("nome_deposito", null)

    fun saveServerUrl(url: String) {
        prefs.edit { putString("server_url", url) }
    }

    fun getServerUrl(): String =
        prefs.getString("server_url", BuildConfig.API_BASE_URL) ?: BuildConfig.API_BASE_URL

    fun logout() {
        prefs.edit { clear() }
    }
}
