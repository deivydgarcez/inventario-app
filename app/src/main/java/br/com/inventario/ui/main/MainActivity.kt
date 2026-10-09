package br.com.inventario.ui.main

import android.animation.Animator
import android.animation.AnimatorListenerAdapter
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.view.ViewAnimationUtils
import android.view.ViewGroup
import android.view.animation.AccelerateDecelerateInterpolator
import android.widget.Toast
import androidx.appcompat.app.AppCompatDelegate

import br.com.inventario.BuildConfig
import br.com.inventario.R
import androidx.lifecycle.lifecycleScope
import br.com.inventario.data.api.RetrofitClient
import br.com.inventario.data.db.InvecDatabase
import br.com.inventario.data.model.Deposito
import br.com.inventario.data.model.IniciarSessaoRequest
import br.com.inventario.data.repository.CatalogoRepository
import br.com.inventario.databinding.ActivityMainBinding
import br.com.inventario.ui.login.LoginActivity
import br.com.inventario.ui.base.TimeoutActivity
import br.com.inventario.ui.relatorio.RelatorioActivity
import br.com.inventario.ui.scanner.ScannerActivity
import br.com.inventario.ui.usuarios.UsuariosActivity
import br.com.inventario.util.GlassDialog
import br.com.inventario.util.ServerMonitor
import br.com.inventario.util.SessionManager
import br.com.inventario.util.UpdateChecker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : TimeoutActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var session: SessionManager
    private lateinit var db: InvecDatabase
    private var depositos: List<Deposito> = emptyList()

    companion object {
        private var updateCheckDone = false
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        session = SessionManager(this)
        db = InvecDatabase.getInstance(this)

        ServerMonitor.startOrKeep(session, lifecycleScope)

        binding.tvVersion.text = "v${BuildConfig.VERSION_NAME}"
        atualizarHeader()
        atualizarIconeDarkMode()

        binding.btnDarkMode.setOnCheckedChangeListener { _, isChecked ->
            if (isChecked != session.isDarkMode()) toggleDarkModeWithReveal(isChecked)
        }

        binding.btnSelecionarDeposito.setOnClickListener { carregarDepositos() }
        binding.btnBipar.setOnClickListener { abrirScanner() }
        binding.btnRelatorio.setOnClickListener { abrirRelatorio() }
        binding.btnUsuarios.setOnClickListener {
            startActivity(Intent(this, UsuariosActivity::class.java))
        }
        binding.btnSair.setOnClickListener { sair() }
        binding.btnConfigurarServidor.setOnClickListener { configurarServidor() }

        verificarAtualizacao()
    }

    override fun onResume() {
        super.onResume()
        atualizarHeader()
    }

    private fun toggleDarkModeWithReveal(novo: Boolean) {
        val newBgColor = if (novo) Color.parseColor("#1C2128") else Color.parseColor("#E8ECEF")

        val rootView = binding.root
        val overlayView = View(this).apply { setBackgroundColor(newBgColor) }
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

    private fun atualizarHeader() {
        val nome = session.getNome() ?: session.getUsuario() ?: "usuário"
        binding.tvNome.text = "Olá, $nome"
        val dep = session.getNomeDeposito()
        val cdDep = session.getCdDeposito()
        if (dep != null) {
            val qtdeCatalogo = db.catalogo.count(cdDep)
            binding.tvDeposito.text = if (qtdeCatalogo > 0)
                "Depósito: $dep · $qtdeCatalogo produtos em cache"
            else
                "Depósito: $dep · catálogo não baixado"
            binding.tvDeposito.setTextColor(getColor(R.color.textSecondary))
        } else {
            binding.tvDeposito.text = "⚠ Nenhum depósito selecionado"
            binding.tvDeposito.setTextColor(getColor(R.color.atomicOrange))
        }
        binding.btnBipar.isEnabled = true
        binding.btnRelatorio.isEnabled = dep != null
        binding.btnUsuarios.visibility = if (session.canManageUsers()) View.VISIBLE else View.GONE
    }

    private fun verificarAtualizacao() {
        if (updateCheckDone) return
        updateCheckDone = true

        // Limpa APK de update anterior que possa ter ficado no cache
        java.io.File(cacheDir, "invec_update.apk").delete()

        lifecycleScope.launch {
            delay(800)
            val info = withContext(Dispatchers.IO) { UpdateChecker.verificar() } ?: return@launch

            GlassDialog.show(
                context = this@MainActivity,
                title = "Nova versão disponível  v${info.versao}",
                message = info.changelog,
                positiveText = "Atualizar",
                negativeText = "Agora não",
                cancelable = false,
                onPositive = { baixarEInstalar(info.apkApiUrl) }
            )
        }
    }

    private fun baixarEInstalar(apkApiUrl: String) {
        val (loadingDialog, tvMsg) = GlassDialog.showLoading(
            this,
            "Baixando atualização",
            "Iniciando download..."
        )

        lifecycleScope.launch {
            val apkFile = UpdateChecker.baixar(this@MainActivity, apkApiUrl) { progresso ->
                runOnUiThread { tvMsg.text = "Baixando... $progresso%" }
            }

            if (!isFinishing && !isDestroyed) loadingDialog.dismiss()

            if (apkFile != null) {
                UpdateChecker.instalar(this@MainActivity, apkFile)
            } else {
                if (!isFinishing && !isDestroyed) {
                    GlassDialog.show(
                        context = this@MainActivity,
                        title = "Falha no download",
                        message = "Não foi possível baixar a atualização. Tente novamente mais tarde.",
                        positiveText = "OK"
                    )
                }
            }
        }
    }

    private fun configurarServidor() {
        GlassDialog.input(
            context = this,
            title = "Endereço do servidor",
            hint = "http://192.168.0.1:8000/",
            message = "Digite o IP e porta do servidor.\nExemplo: http://192.168.0.31:8000/",
            prefilled = session.getServerUrl() ?: "",
            positiveText = "Salvar"
        ) { raw ->
            var url = raw
            if (url.isNotEmpty()) {
                if (!url.startsWith("http")) url = "http://$url"
                if (!url.endsWith("/")) url = "$url/"
                session.saveServerUrl(url)
                RetrofitClient.reset()
                ServerMonitor.reset()
                ServerMonitor.startOrKeep(session, lifecycleScope)
                Toast.makeText(this, "Servidor configurado: $url", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun carregarDepositos() {
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val response = api.listarDepositos()
                if (response.isSuccessful) {
                    depositos = response.body() ?: emptyList()
                    session.saveDepositos(depositos)
                    mostrarDialogDeposito(fromCache = false)
                } else {
                    Toast.makeText(this@MainActivity, "Erro ao carregar depósitos", Toast.LENGTH_SHORT).show()
                }
            } catch (_: Exception) {
                val cached = session.getCachedDepositos()
                if (!cached.isNullOrEmpty()) {
                    depositos = cached
                    mostrarDialogDeposito(fromCache = true)
                } else {
                    Toast.makeText(this@MainActivity, "Sem conexão. Conecte-se ao servidor ao menos uma vez para usar offline.", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun mostrarDialogDeposito(fromCache: Boolean = false) {
        val nomes = depositos.map { it.deposito }.toTypedArray()
        GlassDialog.list(
            context = this,
            title = if (fromCache) "Selecionar Depósito (cache)" else "Selecionar Depósito",
            items = nomes
        ) { index -> iniciarDeposito(depositos[index]) }
    }

    private fun iniciarDeposito(dep: Deposito) {
        val oldDepositoId = session.getCdDeposito()
        val oldSessionId = if (oldDepositoId != -1 && oldDepositoId != dep.cddeposito) session.getSessionId() else null

        if (oldDepositoId != dep.cddeposito) session.resetEntregaFlag()
        session.saveDeposito(dep.cddeposito, dep.deposito)

        val sessionId = session.getOuCriarSession()

        atualizarHeader()
        binding.btnSelecionarDeposito.isEnabled = false
        binding.btnBipar.isEnabled = false

        lifecycleScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            var qtdCarregada = -1
            try {
                val api = RetrofitClient.build(session)
                if (oldSessionId != null && ServerMonitor.isOnline.value) {
                    try { api.encerrarSessao(oldSessionId) } catch (_: Exception) {}
                }
                if (ServerMonitor.isOnline.value) {
                    try { api.iniciarSessao(IniciarSessaoRequest(sessionId = sessionId, cddeposito = dep.cddeposito, operador = session.getOperador())) } catch (_: Exception) {}
                }
                val repo = CatalogoRepository(db, api, session)
                kotlinx.coroutines.withTimeout(60_000L) {
                    repo.sincronizarCatalogo(dep.cddeposito) { baixados, total ->
                        runOnUiThread { binding.tvDeposito.text = "Depósito: ${dep.deposito} · baixando $baixados/$total..." }
                    }
                }
                qtdCarregada = db.catalogo.count(dep.cddeposito)
            } catch (_: Exception) {
                val temCache = db.catalogo.count(dep.cddeposito) == 0
                if (temCache) {
                    runOnUiThread { Toast.makeText(this@MainActivity, "Sem conexão — catálogo não baixado", Toast.LENGTH_LONG).show() }
                }
            } finally {
                runOnUiThread {
                    binding.btnSelecionarDeposito.isEnabled = true
                    atualizarHeader()
                    if (qtdCarregada > 0) {
                        Toast.makeText(this@MainActivity, "✓ Catálogo carregado — $qtdCarregada produtos", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        }
    }

    private fun abrirScanner() {
        if (session.getCdDeposito() == -1) {
            GlassDialog.show(
                context = this,
                title = "Depósito não selecionado",
                message = "Selecione um depósito antes de iniciar a coleta.",
                positiveText = "Entendido"
            )
            return
        }
        startActivity(Intent(this, ScannerActivity::class.java))
    }

    private fun abrirRelatorio() {
        if (session.getCdDeposito() == -1) { Toast.makeText(this, "Selecione um depósito primeiro", Toast.LENGTH_SHORT).show(); return }
        startActivity(Intent(this, RelatorioActivity::class.java))
    }

    private fun sair() {
        val mensagem = if (ServerMonitor.isOnline.value) "Deseja sair da conta?"
        else "Você está sem conexão com o servidor.\n\nSe sair, só conseguirá fazer login novamente quando estiver conectado ao servidor."
        GlassDialog.show(
            context = this,
            title = "Sair da conta",
            message = mensagem,
            positiveText = "Sair",
            negativeText = "Cancelar",
            onPositive = { fazerLogout() }
        )
    }

    private fun fazerLogout() {
        updateCheckDone = false
        val sessionId = session.getSessionId()
        if (sessionId != null && ServerMonitor.isOnline.value) {
            val api = try { RetrofitClient.build(session) } catch (_: Exception) { null }
            if (api != null) {
                lifecycleScope.launch {
                    try { kotlinx.coroutines.withTimeoutOrNull(3_000) { api.encerrarSessao(sessionId) } } catch (_: Exception) {}
                    kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) { db.bipag.deleteAllDaSessao(sessionId) }
                    session.logout(); RetrofitClient.reset()
                    startActivity(Intent(this@MainActivity, LoginActivity::class.java)); finish()
                }
                return
            }
        }
        if (sessionId != null) {
            lifecycleScope.launch {
                kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) { db.bipag.deleteAllDaSessao(sessionId) }
                session.logout(); RetrofitClient.reset()
                startActivity(Intent(this@MainActivity, LoginActivity::class.java)); finish()
            }
            return
        }
        session.logout(); RetrofitClient.reset()
        startActivity(Intent(this, LoginActivity::class.java)); finish()
    }
}
