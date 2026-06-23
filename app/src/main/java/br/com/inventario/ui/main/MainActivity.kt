package br.com.inventario.ui.main

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
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
import br.com.inventario.util.ServerMonitor
import br.com.inventario.util.SessionManager
import kotlinx.coroutines.launch

class MainActivity : TimeoutActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var session: SessionManager
    private lateinit var db: InvecDatabase
    private var depositos: List<Deposito> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        session = SessionManager(this)
        db = InvecDatabase.getInstance(this)

        ServerMonitor.startOrKeep(session, lifecycleScope)

        atualizarHeader()

        binding.btnSelecionarDeposito.setOnClickListener { carregarDepositos() }
        binding.btnBipar.setOnClickListener { abrirScanner() }
        binding.btnRelatorio.setOnClickListener { abrirRelatorio() }
        binding.btnUsuarios.setOnClickListener {
            startActivity(Intent(this, UsuariosActivity::class.java))
        }
        binding.btnSair.setOnClickListener { sair() }
        binding.btnConfigurarServidor.setOnClickListener { configurarServidor() }
    }

    override fun onResume() {
        super.onResume()
        atualizarHeader()
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
        } else {
            binding.tvDeposito.text = "Nenhum depósito selecionado"
        }
        binding.btnBipar.isEnabled = dep != null
        binding.btnRelatorio.isEnabled = dep != null
        binding.btnUsuarios.visibility = if (session.canManageUsers()) View.VISIBLE else View.GONE
    }

    private fun configurarServidor() {
        val urlAtual = session.getServerUrl()
        val input = EditText(this).apply {
            hint = "http://192.168.0.1:8000/"
            setText(urlAtual)
            setPadding(48, 32, 48, 32)
        }
        AlertDialog.Builder(this)
            .setTitle("Endereço do servidor")
            .setMessage("Digite o IP e porta do servidor.\nExemplo: http://192.168.0.31:8000/")
            .setView(input)
            .setPositiveButton("Salvar") { _, _ ->
                var url = input.text.toString().trim()
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
            .setNegativeButton("Cancelar", null)
            .show()
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
                    Toast.makeText(
                        this@MainActivity,
                        "Sem conexão. Conecte-se ao servidor ao menos uma vez para usar offline.",
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
        }
    }

    private fun mostrarDialogDeposito(fromCache: Boolean = false) {
        val nomes = depositos.map { it.deposito }.toTypedArray()
        val titulo = if (fromCache) "Selecionar Depósito (cache)" else "Selecionar Depósito"
        AlertDialog.Builder(this)
            .setTitle(titulo)
            .setItems(nomes) { _, index ->
                val dep = depositos[index]

                // BUG-2: guarda depósito/sessão antigos antes de trocar
                val oldDepositoId = session.getCdDeposito()
                val oldSessionId  = if (oldDepositoId != -1 && oldDepositoId != dep.cddeposito)
                    session.getSessionId() else null

                session.saveDeposito(dep.cddeposito, dep.deposito)

                // Garante sessão ativa para este depósito
                val sessionId = session.getOuCriarSession()

                atualizarHeader()
                binding.btnSelecionarDeposito.isEnabled = false
                binding.btnBipar.isEnabled = false

                lifecycleScope.launch {
                    try {
                        val api = RetrofitClient.build(session)

                        // BUG-2: encerra sessão do depósito anterior no servidor (não bloqueia UI em caso de falha)
                        if (oldSessionId != null && ServerMonitor.isOnline.value) {
                            try { api.encerrarSessao(oldSessionId) } catch (_: Exception) {}
                        }

                        if (ServerMonitor.isOnline.value) {
                            try {
                                api.iniciarSessao(IniciarSessaoRequest(
                                    sessionId  = sessionId,
                                    cddeposito = dep.cddeposito,
                                    operador   = session.getOperador(),
                                ))
                            } catch (_: Exception) { }
                        }

                        val repo = CatalogoRepository(db, api, session)
                        repo.sincronizarCatalogo(dep.cddeposito) { baixados, total ->
                            runOnUiThread {
                                binding.tvDeposito.text =
                                    "Depósito: ${dep.deposito} · baixando $baixados/$total..."
                            }
                        }
                    } catch (_: Exception) {
                        val cached = db.catalogo.count(dep.cddeposito)
                        runOnUiThread {
                            if (cached == 0) {
                                Toast.makeText(this@MainActivity, "Sem conexão — catálogo não baixado", Toast.LENGTH_LONG).show()
                            }
                        }
                    } finally {
                        runOnUiThread {
                            binding.btnSelecionarDeposito.isEnabled = true
                            atualizarHeader()
                        }
                    }
                }
            }
            .show()
    }

    private fun abrirScanner() {
        if (session.getCdDeposito() == -1) {
            Toast.makeText(this, "Selecione um depósito primeiro", Toast.LENGTH_SHORT).show()
            return
        }
        startActivity(Intent(this, ScannerActivity::class.java))
    }

    private fun abrirRelatorio() {
        if (session.getCdDeposito() == -1) {
            Toast.makeText(this, "Selecione um depósito primeiro", Toast.LENGTH_SHORT).show()
            return
        }
        startActivity(Intent(this, RelatorioActivity::class.java))
    }

    private fun sair() {
        val online = ServerMonitor.isOnline.value
        val mensagem = if (online) {
            "Deseja sair da conta?"
        } else {
            "Você está sem conexão com o servidor.\n\nSe sair, só conseguirá fazer login novamente quando estiver conectado ao servidor."
        }
        AlertDialog.Builder(this)
            .setTitle("Sair da conta")
            .setMessage(mensagem)
            .setPositiveButton("Sair") { _, _ -> fazerLogout() }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun fazerLogout() {
        val sessionId = session.getSessionId()
        if (sessionId != null && ServerMonitor.isOnline.value) {
            val api = try { RetrofitClient.build(session) } catch (_: Exception) { null }
            if (api != null) {
                lifecycleScope.launch {
                    try { kotlinx.coroutines.withTimeoutOrNull(3_000) { api.encerrarSessao(sessionId) } } catch (_: Exception) {}
                    session.logout()
                    RetrofitClient.reset()
                    startActivity(Intent(this@MainActivity, LoginActivity::class.java))
                    finish()
                }
                return
            }
        }
        session.logout()
        RetrofitClient.reset()
        startActivity(Intent(this, LoginActivity::class.java))
        finish()
    }
}
