package br.com.inventario.ui.main

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.lifecycle.lifecycleScope
import br.com.inventario.data.api.RetrofitClient
import br.com.inventario.data.model.Deposito
import br.com.inventario.data.model.Operador
import br.com.inventario.databinding.ActivityMainBinding
import br.com.inventario.ui.login.LoginActivity
import br.com.inventario.ui.base.TimeoutActivity
import br.com.inventario.ui.operadores.OperadoresActivity
import br.com.inventario.ui.relatorio.RelatorioActivity
import br.com.inventario.ui.scanner.ScannerActivity
import br.com.inventario.ui.usuarios.UsuariosActivity
import br.com.inventario.util.SessionManager
import kotlinx.coroutines.launch

class MainActivity : TimeoutActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var session: SessionManager
    private var depositos: List<Deposito> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        session = SessionManager(this)
        atualizarHeader()

        binding.btnSelecionarDeposito.setOnClickListener { carregarDepositos() }
        binding.btnBipar.setOnClickListener { abrirScanner() }
        binding.btnRelatorio.setOnClickListener { abrirRelatorio() }
        binding.btnOperadores.setOnClickListener {
            startActivity(Intent(this, OperadoresActivity::class.java))
        }
        binding.btnUsuarios.setOnClickListener {
            startActivity(Intent(this, UsuariosActivity::class.java))
        }
        binding.btnSair.setOnClickListener { sair() }
        binding.btnConfigurarServidor.setOnClickListener { configurarServidor() }
        binding.tvOperadorAtual.setOnClickListener { carregarEMostrarOperadores() }
    }

    override fun onResume() {
        super.onResume()
        atualizarHeader()
    }

    private fun atualizarHeader() {
        val nome = session.getNome() ?: session.getUsuario() ?: "usuário"
        binding.tvNome.text = "Olá, $nome"
        val dep = session.getNomeDeposito()
        binding.tvDeposito.text = if (dep != null) "Depósito: $dep" else "Nenhum depósito selecionado"
        binding.btnBipar.isEnabled = dep != null
        binding.btnRelatorio.isEnabled = dep != null
        val op = session.getOperador()
        binding.tvOperadorAtual.text = if (op != null)
            "Operador: $op  (toque para trocar)"
        else
            "Operador: nenhum selecionado  (toque para definir)"
        binding.btnUsuarios.visibility = if (session.canManageUsers()) View.VISIBLE else View.GONE
    }

    private fun carregarEMostrarOperadores() {
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val resp = api.listarOperadores()
                if (resp.isSuccessful) {
                    val lista: List<Operador> = (resp.body() ?: emptyList()).filter { it.ativo == 1 }
                    val nomes = (listOf("(Sem operador)") + lista.map { it.nome }).toTypedArray()
                    AlertDialog.Builder(this@MainActivity)
                        .setTitle("Quem vai fazer a contagem?")
                        .setCancelable(true)
                        .setItems(nomes) { _, idx ->
                            val operador = if (idx == 0) null else lista[idx - 1].nome
                            session.saveOperador(operador)
                            atualizarHeader()
                        }
                        .show()
                } else {
                    Toast.makeText(this@MainActivity, "Erro ao carregar operadores", Toast.LENGTH_SHORT).show()
                }
            } catch (_: Exception) {
                Toast.makeText(this@MainActivity, "Sem conexão para carregar operadores", Toast.LENGTH_SHORT).show()
            }
        }
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
                    mostrarDialogDeposito()
                } else {
                    Toast.makeText(this@MainActivity, "Erro ao carregar depósitos", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@MainActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun mostrarDialogDeposito() {
        val nomes = depositos.map { it.deposito }.toTypedArray()
        AlertDialog.Builder(this)
            .setTitle("Selecionar Depósito")
            .setItems(nomes) { _, index ->
                val dep = depositos[index]
                session.saveDeposito(dep.cddeposito, dep.deposito)
                atualizarHeader()
                Toast.makeText(this, "Depósito: ${dep.deposito}", Toast.LENGTH_SHORT).show()
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
        session.logout()
        RetrofitClient.reset()
        startActivity(Intent(this, LoginActivity::class.java))
        finish()
    }
}
