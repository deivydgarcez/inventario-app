package br.com.inventario.ui.login

import android.animation.Animator
import android.animation.AnimatorListenerAdapter
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.provider.Settings
import android.view.View
import android.view.ViewAnimationUtils
import android.view.ViewGroup
import android.view.animation.AccelerateDecelerateInterpolator
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.lifecycleScope
import br.com.inventario.R
import br.com.inventario.data.api.ApiService
import br.com.inventario.data.api.RetrofitClient
import br.com.inventario.data.model.LoginRequest
import br.com.inventario.databinding.ActivityLoginBinding
import br.com.inventario.ui.main.MainActivity
import br.com.inventario.util.SessionManager
import kotlinx.coroutines.launch
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        session = SessionManager(this)

        atualizarIconeDarkMode()
        binding.btnDarkMode.setOnCheckedChangeListener { _, isChecked ->
            if (isChecked != session.isDarkMode()) toggleDarkModeWithReveal(isChecked)
        }

        // Teclado: root com fitsSystemWindows já trata status/nav; aqui só o IME
        ViewCompat.setOnApplyWindowInsetsListener(binding.scrollView) { view, insets ->
            val imeBottom = insets.getInsets(WindowInsetsCompat.Type.ime()).bottom
            view.setPadding(0, 0, 0, imeBottom)
            insets
        }

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

        binding.btnEntrarNm.setOnClickListener { doLogin() }
        binding.btnEntrar.setOnClickListener { doLogin() }

        binding.btnConfigurarServidor.setOnClickListener {
            val url = binding.etServerUrl.text.toString().trim()
            if (url.isNotEmpty()) {
                val finalUrl = if (url.endsWith("/")) url else "$url/"
                session.saveServerUrl(finalUrl)
                RetrofitClient.reset()
                Toast.makeText(this, "Servidor salvo: $finalUrl", Toast.LENGTH_SHORT).show()
                binding.tvTesteResult.visibility = View.GONE
            }
        }

        binding.btnTestarConexao.setOnClickListener { testarConexao() }

        binding.etServerUrl.setText(session.getServerUrl())
    }

    private fun testarConexao() {
        val rawUrl = binding.etServerUrl.text.toString().trim()
        if (rawUrl.isEmpty()) {
            mostrarResultadoTeste(ok = false, msg = "Digite uma URL primeiro")
            return
        }

        // Normaliza URL (igual ao MainActivity): garante http:// e barra final
        var baseUrl = if (rawUrl.endsWith("/")) rawUrl else "$rawUrl/"
        if (!baseUrl.startsWith("http")) baseUrl = "http://$baseUrl"

        binding.btnTestarConexao.isEnabled = false
        binding.tvTesteResult.visibility = View.GONE

        lifecycleScope.launch {
            val inicio = System.currentTimeMillis()
            try {
                // Usa o mesmo Retrofit/OkHttp do login, só troca a baseUrl
                val api = Retrofit.Builder()
                    .baseUrl(baseUrl)
                    .addConverterFactory(GsonConverterFactory.create())
                    .build()
                    .create(ApiService::class.java)

                val response = api.ping()
                val ms = System.currentTimeMillis() - inicio

                if (response.isSuccessful) {
                    mostrarResultadoTeste(ok = true, msg = "✓  Servidor respondeu em ${ms} ms")
                } else {
                    mostrarResultadoTeste(ok = false, msg = "✗  Servidor retornou erro ${response.code()}")
                }
            } catch (_: Exception) {
                mostrarResultadoTeste(ok = false, msg = "✗  Sem resposta — verifique o IP e a porta")
            } finally {
                binding.btnTestarConexao.isEnabled = true
            }
        }
    }

    private fun mostrarResultadoTeste(ok: Boolean, msg: String) {
        binding.tvTesteResult.text = msg
        binding.tvTesteResult.setTextColor(
            if (ok) Color.parseColor("#2E7D32") else Color.parseColor("#C62828")
        )
        binding.tvTesteResult.setBackgroundColor(
            if (ok) Color.parseColor("#E8F5E9") else Color.parseColor("#FFEBEE")
        )
        binding.tvTesteResult.visibility = View.VISIBLE
    }

    private fun doLogin() {
        val login = binding.etLogin.text.toString().trim()
        val senha = binding.etSenha.text.toString().trim()

        if (login.isEmpty() || senha.isEmpty()) {
            Toast.makeText(this, "Preencha login e senha", Toast.LENGTH_SHORT).show()
            return
        }

        setLoading(true)
        val deviceId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID)
            ?: "unknown-device"
        val deviceName = android.os.Build.MODEL
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val response = api.login(LoginRequest(login, senha, deviceId, deviceName))
                if (response.isSuccessful) {
                    val body = response.body()!!
                    session.saveLogin(body.accessToken, body.usuario, body.nome, body.role, body.mobileAdmin)
                    goToMain()
                } else if (response.code() == 403) {
                    val detail = try {
                        org.json.JSONObject(response.errorBody()?.string() ?: "").getString("detail")
                    } catch (_: Exception) {
                        "Acesso negado. Contate o administrador."
                    }
                    androidx.appcompat.app.AlertDialog.Builder(this@LoginActivity)
                        .setTitle("Limite de Dispositivos")
                        .setMessage(detail)
                        .setPositiveButton("OK", null)
                        .show()
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
            } catch (_: Exception) {
                Toast.makeText(
                    this@LoginActivity,
                    "Sem conexão com o servidor.\nConecte-se ao WiFi do servidor para fazer login.",
                    Toast.LENGTH_LONG
                ).show()
            } finally {
                setLoading(false)
            }
        }
    }

    private fun setLoading(loading: Boolean) {
        binding.btnEntrarNm.isEnabled = !loading
        binding.btnEntrar.isEnabled = !loading
        binding.progressBar.visibility = if (loading) View.VISIBLE else View.GONE
    }

    private fun toggleDarkModeWithReveal(novo: Boolean) {
        val newBgColor = if (novo) Color.parseColor("#1C2128") else Color.parseColor("#E8ECEF")

        val rootView = binding.root
        val overlayView = android.view.View(this).apply { setBackgroundColor(newBgColor) }
        (rootView as ViewGroup).overlay.add(overlayView)
        overlayView.layout(0, 0, rootView.width, rootView.height)

        val loc = IntArray(2)
        binding.btnDarkMode.getLocationInWindow(loc)
        val cx = loc[0] + binding.btnDarkMode.width / 2
        val cy = loc[1] + binding.btnDarkMode.height / 2
        val maxRadius = Math.hypot(rootView.width.toDouble(), rootView.height.toDouble()).toFloat()

        val reveal = ViewAnimationUtils.createCircularReveal(overlayView, cx, cy, 0f, maxRadius)
        reveal.duration = 420
        reveal.interpolator = AccelerateDecelerateInterpolator()
        reveal.addListener(object : AnimatorListenerAdapter() {
            override fun onAnimationEnd(animation: Animator) {
                session.saveDarkMode(novo)
                binding.ivDarkModeIcon.setImageResource(
                    if (novo) R.drawable.ic_light_mode else R.drawable.ic_dark_mode
                )
                AppCompatDelegate.setDefaultNightMode(
                    if (novo) AppCompatDelegate.MODE_NIGHT_YES else AppCompatDelegate.MODE_NIGHT_NO
                )
                (rootView as ViewGroup).overlay.remove(overlayView)
            }
        })
        reveal.start()
    }

    private fun atualizarIconeDarkMode() {
        val isDark = session.isDarkMode()
        binding.btnDarkMode.isChecked = isDark
        binding.ivDarkModeIcon.setImageResource(
            if (isDark) R.drawable.ic_light_mode else R.drawable.ic_dark_mode
        )
    }

    private fun goToMain() {
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }
}
