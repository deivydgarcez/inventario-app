package br.com.inventario.ui.main

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import br.com.inventario.data.api.RetrofitClient
import br.com.inventario.data.model.Deposito
import br.com.inventario.databinding.ActivityMainBinding
import br.com.inventario.ui.login.LoginActivity
import br.com.inventario.ui.relatorio.RelatorioActivity
import br.com.inventario.ui.scanner.ScannerActivity
import br.com.inventario.util.SessionManager
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

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
        binding.btnSair.setOnClickListener { sair() }
    }

    override fun onResume() {
        super.onResume()
        atualizarHeader()
    }

    private fun atualizarHeader() {
        binding.tvNome.text = "Olá, ${session.getNome() ?: "usuário"}"
        val dep = session.getNomeDeposito()
        binding.tvDeposito.text = if (dep != null) "Depósito: $dep" else "Nenhum depósito selecionado"
        binding.btnBipar.isEnabled = dep != null
        binding.btnRelatorio.isEnabled = dep != null
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
