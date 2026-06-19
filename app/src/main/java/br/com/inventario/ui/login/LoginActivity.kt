package br.com.inventario.ui.login

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import br.com.inventario.data.api.RetrofitClient
import br.com.inventario.data.model.LoginRequest
import br.com.inventario.databinding.ActivityLoginBinding
import br.com.inventario.ui.main.MainActivity
import br.com.inventario.util.SessionManager
import kotlinx.coroutines.launch

class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        session = SessionManager(this)

        if (intent.getBooleanExtra("timeout", false)) {
            Toast.makeText(this, "Sessão encerrada por inatividade", Toast.LENGTH_LONG).show()
        }
        if (intent.getBooleanExtra("session_expired", false)) {
            Toast.makeText(this, "Sessão expirada. Faça login novamente.", Toast.LENGTH_LONG).show()
        }

        if (session.isLoggedIn()) {
            goToMain()
            return
        }

        binding.btnEntrar.setOnClickListener { doLogin() }

        binding.btnConfigurarServidor.setOnClickListener {
            val url = binding.etServerUrl.text.toString().trim()
            if (url.isNotEmpty()) {
                val finalUrl = if (url.endsWith("/")) url else "$url/"
                session.saveServerUrl(finalUrl)
                RetrofitClient.reset()
                Toast.makeText(this, "Servidor salvo: $finalUrl", Toast.LENGTH_SHORT).show()
            }
        }

        binding.etServerUrl.setText(session.getServerUrl())
    }

    private fun doLogin() {
        val login = binding.etLogin.text.toString().trim()
        val senha = binding.etSenha.text.toString().trim()

        if (login.isEmpty() || senha.isEmpty()) {
            Toast.makeText(this, "Preencha login e senha", Toast.LENGTH_SHORT).show()
            return
        }

        setLoading(true)
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val response = api.login(LoginRequest(login, senha))
                if (response.isSuccessful) {
                    val body = response.body()!!
                    session.saveLogin(body.accessToken, body.usuario, body.nome, body.role, body.mobileAdmin)
                    goToMain()
                } else {
                    val msg = if (response.code() == 401) {
                        "Login ou senha inválidos"
                    } else {
                        try {
                            org.json.JSONObject(response.errorBody()?.string() ?: "").getString("detail")
                        } catch (_: Exception) {
                            "Erro ao fazer login (${response.code()})"
                        }
                    }
                    Toast.makeText(this@LoginActivity, msg, Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@LoginActivity, "Erro ao conectar: ${e.message}", Toast.LENGTH_LONG).show()
            } finally {
                setLoading(false)
            }
        }
    }

    private fun setLoading(loading: Boolean) {
        binding.btnEntrar.isEnabled = !loading
        binding.progressBar.visibility = if (loading) View.VISIBLE else View.GONE
    }

    private fun goToMain() {
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }
}
