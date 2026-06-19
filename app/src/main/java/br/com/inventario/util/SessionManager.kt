package br.com.inventario.util

import android.content.Context
import android.provider.Settings
import br.com.inventario.BuildConfig
import androidx.core.content.edit

class SessionManager(val context: Context) {

    private val prefs = context.getSharedPreferences("inventario_prefs", Context.MODE_PRIVATE)

    fun getDeviceId(): String =
        Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID) ?: "unknown"

    fun saveLogin(token: String, usuario: String, nome: String, role: String = "operador", mobileAdmin: Int = 0) {
        prefs.edit {
            putString("token", token)
                .putString("usuario", usuario)
                .putString("nome", nome)
                .putString("role", role)
                .putInt("mobile_admin", mobileAdmin)
        }
    }

    fun getToken(): String? = prefs.getString("token", null)
    fun getUsuario(): String? = prefs.getString("usuario", null)
    fun getNome(): String? = prefs.getString("nome", null)
    fun getRole(): String = prefs.getString("role", "operador") ?: "operador"
    fun getMobileAdmin(): Int = prefs.getInt("mobile_admin", 0)
    fun canManageUsers(): Boolean = getMobileAdmin() == 1
    fun isMI(): Boolean = getUsuario()?.uppercase() == "MI"
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

    fun saveOperador(nome: String?) {
        prefs.edit { putString("operador", nome) }
    }

    fun getOperador(): String? = prefs.getString("operador", null)

    fun saveScanMode(mode: String) {
        prefs.edit { putString("scan_mode", mode) }
    }

    fun getScanMode(): String = prefs.getString("scan_mode", "CAMERA") ?: "CAMERA"

    fun setConsolidarBloqueado(cddeposito: Int, bloqueado: Boolean) {
        prefs.edit { putBoolean("consolidar_bloqueado_$cddeposito", bloqueado) }
    }

    fun isConsolidarBloqueado(cddeposito: Int): Boolean =
        prefs.getBoolean("consolidar_bloqueado_$cddeposito", false)

    fun logout() {
        val serverUrl = getServerUrl()
        prefs.edit { clear() }
        saveServerUrl(serverUrl)
    }
}
