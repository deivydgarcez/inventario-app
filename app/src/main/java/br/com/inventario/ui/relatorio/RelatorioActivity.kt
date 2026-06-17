package br.com.inventario.ui.relatorio

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.ItemTouchHelper
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import br.com.inventario.data.api.RetrofitClient
import br.com.inventario.data.model.EditarBipagemRequest
import br.com.inventario.data.model.ItemRelatorio
import br.com.inventario.databinding.ActivityRelatorioBinding
import br.com.inventario.ui.recontagem.RecontagemActivity
import br.com.inventario.util.SessionManager
import kotlinx.coroutines.launch
import kotlin.math.abs

class RelatorioActivity : AppCompatActivity() {

    private lateinit var binding: ActivityRelatorioBinding
    private lateinit var session: SessionManager
    private var adapter: RelatorioAdapter? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityRelatorioBinding.inflate(layoutInflater)
        setContentView(binding.root)

        WindowCompat.setDecorFitsSystemWindows(window, false)

        session = SessionManager(this)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "Relatório — ${session.getNomeDeposito()}"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        ViewCompat.setOnApplyWindowInsetsListener(binding.toolbar) { v, insets ->
            val top = insets.getInsets(WindowInsetsCompat.Type.statusBars()).top
            v.setPadding(v.paddingLeft, top, v.paddingRight, v.paddingBottom)
            insets
        }

        binding.recycler.layoutManager = LinearLayoutManager(this)
        binding.btnConsolidar.setOnClickListener { confirmarConsolidar() }
        binding.btnRecontagem.setOnClickListener {
            startActivity(Intent(this, RecontagemActivity::class.java))
        }

        val swipeHelper = object : ItemTouchHelper.SimpleCallback(0, ItemTouchHelper.LEFT or ItemTouchHelper.RIGHT) {
            override fun onMove(rv: RecyclerView, vh: RecyclerView.ViewHolder, t: RecyclerView.ViewHolder) = false
            override fun onSwiped(viewHolder: RecyclerView.ViewHolder, direction: Int) {
                val pos = viewHolder.adapterPosition
                val item = adapter?.getItem(pos) ?: return
                confirmarRemocao(item, pos)
            }
        }
        ItemTouchHelper(swipeHelper).attachToRecyclerView(binding.recycler)

        carregarRelatorio()
    }

    override fun onResume() {
        super.onResume()
        carregarRelatorio()
    }

    private fun carregarRelatorio() {
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val response = api.relatorio(session.getCdDeposito())
                if (response.isSuccessful) {
                    val items = response.body()?.toMutableList() ?: mutableListOf()
                    adapter = RelatorioAdapter(items) { item, pos -> editarItem(item, pos) }
                    binding.recycler.adapter = adapter
                    atualizarResumo(items)
                } else {
                    Toast.makeText(this@RelatorioActivity, "Erro ao carregar relatório", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@RelatorioActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.visibility = View.GONE
            }
        }
    }

    private fun atualizarResumo(items: List<ItemRelatorio>) {
        val divergencias = items.count { abs(it.diferenca ?: 0.0) > 0.001 }
        binding.tvTotal.text = if (divergencias > 0)
            "${items.size} itens · $divergencias com divergência"
        else
            "${items.size} itens · tudo OK"
        binding.btnConsolidar.isEnabled = items.isNotEmpty()
        binding.btnRecontagem.isEnabled = items.isNotEmpty()
    }

    private fun editarItem(item: ItemRelatorio, position: Int) {
        val input = EditText(this).apply {
            hint = "Quantidade contada"
            inputType = android.text.InputType.TYPE_CLASS_NUMBER or android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL
            setText("%.2f".format(item.qtde_contada ?: 0.0))
        }
        AlertDialog.Builder(this)
            .setTitle(item.produto)
            .setMessage("Editar quantidade contada")
            .setView(input)
            .setPositiveButton("Salvar") { _, _ ->
                val novaQtde = input.text.toString().toDoubleOrNull() ?: return@setPositiveButton
                lifecycleScope.launch {
                    try {
                        val api = RetrofitClient.build(session)
                        api.editarBipagem(item.cdproduto, EditarBipagemRequest(novaQtde, session.getCdDeposito()))
                        adapter?.updateItem(position, novaQtde)
                        Toast.makeText(this@RelatorioActivity, "Quantidade atualizada", Toast.LENGTH_SHORT).show()
                    } catch (e: Exception) {
                        Toast.makeText(this@RelatorioActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
                    }
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun confirmarRemocao(item: ItemRelatorio, position: Int) {
        AlertDialog.Builder(this)
            .setTitle("Remover item")
            .setMessage("Remover '${item.produto}' da contagem?")
            .setPositiveButton("Remover") { _, _ ->
                lifecycleScope.launch {
                    try {
                        val api = RetrofitClient.build(session)
                        api.removerBipagem(item.cdproduto, session.getCdDeposito())
                        adapter?.removeItem(position)
                        val count = adapter?.itemCount ?: 0
                        binding.tvTotal.text = "$count itens"
                        binding.btnConsolidar.isEnabled = count > 0
                        binding.btnRecontagem.isEnabled = count > 0
                    } catch (e: Exception) {
                        Toast.makeText(this@RelatorioActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
                        carregarRelatorio()
                    }
                }
            }
            .setNegativeButton("Cancelar") { _, _ -> carregarRelatorio() }
            .setOnCancelListener { carregarRelatorio() }
            .show()
    }

    private fun confirmarConsolidar() {
        val adp = adapter ?: return
        val total = adp.itemCount
        val divergencias = (0 until total).count { pos ->
            abs(adp.getItem(pos).diferenca ?: 0.0) > 0.001
        }

        val msg = buildString {
            append("Depósito: ${session.getNomeDeposito()}\n\n")
            append("• $total itens para consolidar\n")
            if (divergencias > 0) {
                append("• $divergencias itens com diferença de estoque\n\n")
                append("Recomendado: faça a recontagem antes de consolidar.")
            } else {
                append("• Sem divergências encontradas.\n\nPode consolidar com segurança!")
            }
        }

        AlertDialog.Builder(this)
            .setTitle("Consolidar Inventário")
            .setMessage(msg)
            .setPositiveButton("Consolidar agora") { _, _ -> consolidar() }
            .apply {
                if (divergencias > 0) {
                    setNeutralButton("Fazer recontagem") { _, _ ->
                        startActivity(Intent(this@RelatorioActivity, RecontagemActivity::class.java))
                    }
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }

    private fun consolidar() {
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val response = api.consolidar(mapOf("cddeposito" to session.getCdDeposito()))
                if (response.isSuccessful) {
                    val msg = response.body()?.get("mensagem") ?: "Consolidado com sucesso"
                    Toast.makeText(this@RelatorioActivity, msg, Toast.LENGTH_LONG).show()
                    carregarRelatorio()
                } else {
                    Toast.makeText(this@RelatorioActivity, "Erro ao consolidar", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@RelatorioActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.visibility = View.GONE
            }
        }
    }
}
