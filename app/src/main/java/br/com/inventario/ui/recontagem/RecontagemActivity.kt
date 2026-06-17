package br.com.inventario.ui.recontagem

import android.os.Bundle
import android.view.KeyEvent
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import br.com.inventario.data.api.RetrofitClient
import br.com.inventario.data.model.EditarBipagemRequest
import br.com.inventario.data.model.ItemRelatorio
import br.com.inventario.databinding.ActivityRecontagemBinding
import br.com.inventario.databinding.ItemRecontagemBinding
import br.com.inventario.util.SessionManager
import kotlinx.coroutines.launch
import kotlin.math.abs

class RecontagemActivity : AppCompatActivity() {

    private enum class ScanMode { CAMERA, BLUETOOTH }

    private lateinit var binding: ActivityRecontagemBinding
    private lateinit var session: SessionManager
    private var scanMode = ScanMode.BLUETOOTH

    private val btBuffer = StringBuilder()
    private var btLastKeyTime = 0L
    private val BT_TIMEOUT_MS = 150L
    private var processando = false

    data class ItemRecontagem(
        val item: ItemRelatorio,
        var qtde2: Double = 0.0,
    )

    private val itens = mutableListOf<ItemRecontagem>()
    private val barcodeMap = mutableMapOf<String, Int>()
    private val cdprodutoMap = mutableMapOf<Int, Int>()
    private lateinit var adapter: RecontagemAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityRecontagemBinding.inflate(layoutInflater)
        setContentView(binding.root)

        WindowCompat.setDecorFitsSystemWindows(window, false)

        session = SessionManager(this)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "Recontagem — ${session.getNomeDeposito()}"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        ViewCompat.setOnApplyWindowInsetsListener(binding.toolbar) { v, insets ->
            val top = insets.getInsets(WindowInsetsCompat.Type.statusBars()).top
            v.setPadding(v.paddingLeft, top, v.paddingRight, v.paddingBottom)
            insets
        }

        adapter = RecontagemAdapter(itens)
        binding.recycler.layoutManager = LinearLayoutManager(this)
        binding.recycler.adapter = adapter

        binding.btnModo.setOnClickListener { alternarModo() }
        binding.btnFinalizar.setOnClickListener { finalizarRecontagem() }

        carregarItens()
    }

    private fun alternarModo() {
        scanMode = if (scanMode == ScanMode.BLUETOOTH) ScanMode.CAMERA else ScanMode.BLUETOOTH
        binding.btnModo.text = if (scanMode == ScanMode.BLUETOOTH) "BT" else "Câmera"
        val modoStr = if (scanMode == ScanMode.BLUETOOTH) "Bluetooth" else "Câmera"
        Toast.makeText(this, "Modo: $modoStr", Toast.LENGTH_SHORT).show()
    }

    private fun carregarItens() {
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val resp = api.relatorio(session.getCdDeposito())
                if (resp.isSuccessful) {
                    val lista = resp.body() ?: emptyList()
                    itens.clear()
                    barcodeMap.clear()
                    cdprodutoMap.clear()
                    lista.forEachIndexed { idx, item ->
                        itens.add(ItemRecontagem(item))
                        item.codigobarra?.let { barcodeMap[it] = idx }
                        cdprodutoMap[item.cdproduto] = idx
                    }
                    adapter.notifyDataSetChanged()
                    atualizarStatus()
                } else {
                    Toast.makeText(this@RecontagemActivity, "Erro ao carregar itens", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@RecontagemActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.visibility = View.GONE
            }
        }
    }

    private fun atualizarStatus() {
        val escaneados = itens.count { it.qtde2 > 0 }
        val divergencias = itens.count { it.qtde2 > 0 && abs(it.qtde2 - (it.item.qtde_contada ?: 0.0)) > 0.001 }
        binding.tvStatus.text = "$escaneados de ${itens.size} itens · $divergencias divergências"
    }

    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        if (event.action == KeyEvent.ACTION_DOWN) {
            val now = System.currentTimeMillis()
            if (now - btLastKeyTime > BT_TIMEOUT_MS) btBuffer.clear()
            btLastKeyTime = now

            when (event.keyCode) {
                KeyEvent.KEYCODE_ENTER, KeyEvent.KEYCODE_NUMPAD_ENTER -> {
                    val codigo = btBuffer.toString().trim()
                    btBuffer.clear()
                    if (codigo.length >= 3 && !processando) {
                        processando = true
                        buscarERegistrar(codigo)
                    }
                    return true
                }
                else -> {
                    val c = event.unicodeChar.toChar()
                    if (c.code in 32..126) btBuffer.append(c)
                }
            }
        }
        return super.dispatchKeyEvent(event)
    }

    private fun buscarERegistrar(codigo: String) {
        binding.tvStatus.text = "Buscando: $codigo…"
        lifecycleScope.launch {
            try {
                val idx = barcodeMap[codigo]
                if (idx != null) {
                    incrementarItem(idx)
                } else {
                    val api = RetrofitClient.build(session)
                    val resp = api.buscarPorBarcode(codigo, session.getCdDeposito())
                    if (resp.isSuccessful) {
                        val produto = resp.body()!!
                        val idx2 = cdprodutoMap[produto.cdproduto]
                        if (idx2 != null) {
                            incrementarItem(idx2)
                        } else {
                            Toast.makeText(this@RecontagemActivity, "Produto não está na contagem: ${produto.produto}", Toast.LENGTH_SHORT).show()
                        }
                    } else {
                        Toast.makeText(this@RecontagemActivity, "Produto não encontrado: $codigo", Toast.LENGTH_SHORT).show()
                    }
                }
            } catch (e: Exception) {
                Toast.makeText(this@RecontagemActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                processando = false
                atualizarStatus()
            }
        }
    }

    private fun incrementarItem(idx: Int) {
        itens[idx].qtde2 += 1.0
        adapter.notifyItemChanged(idx)
        val item = itens[idx]
        val dif = item.qtde2 - (item.item.qtde_contada ?: 0.0)
        val msg = "${item.item.produto} → 2ª: ${"%.0f".format(item.qtde2)}" +
                if (abs(dif) > 0.001) " ⚠ Dif: ${"%.2f".format(dif)}" else " ✓"
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
    }

    private fun finalizarRecontagem() {
        val escaneados = itens.count { it.qtde2 > 0 }
        if (escaneados == 0) {
            Toast.makeText(this, "Nenhum item foi recontado ainda", Toast.LENGTH_SHORT).show()
            return
        }

        val divergencias = itens.filter {
            it.qtde2 > 0 && abs(it.qtde2 - (it.item.qtde_contada ?: 0.0)) > 0.001
        }
        val matches = itens.count { it.qtde2 > 0 && abs(it.qtde2 - (it.item.qtde_contada ?: 0.0)) <= 0.001 }

        val msg = buildString {
            append("Resultado da recontagem:\n\n")
            append("• $matches itens conferidos (✓ sem divergência)\n")
            if (divergencias.isNotEmpty()) {
                append("• ${divergencias.size} itens com divergência:\n")
                divergencias.take(5).forEach {
                    val dif = it.qtde2 - (it.item.qtde_contada ?: 0.0)
                    append("  - ${it.item.produto}: 1ª=${"%.0f".format(it.item.qtde_contada)}, 2ª=${"%.0f".format(it.qtde2)} (${if (dif > 0) "+" else ""}${"%.0f".format(dif)})\n")
                }
                if (divergencias.size > 5) append("  ... e mais ${divergencias.size - 5} itens\n")
                append("\nDeseja aplicar os valores da 2ª contagem para os itens divergentes?")
            } else {
                append("\nTodos os itens conferem. Pode consolidar com segurança!")
            }
        }

        AlertDialog.Builder(this)
            .setTitle("Resultado da Recontagem")
            .setMessage(msg)
            .apply {
                if (divergencias.isNotEmpty()) {
                    setPositiveButton("Aplicar 2ª contagem") { _, _ -> aplicarRecontagem(divergencias) }
                    setNeutralButton("Manter 1ª contagem") { _, _ -> finish() }
                } else {
                    setPositiveButton("Voltar ao relatório") { _, _ -> finish() }
                }
            }
            .setNegativeButton("Continuar recontando", null)
            .show()
    }

    private fun aplicarRecontagem(divergencias: List<ItemRecontagem>) {
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                var atualizados = 0
                divergencias.forEach { item ->
                    val resp = api.editarBipagem(
                        item.item.cdproduto,
                        EditarBipagemRequest(item.qtde2, session.getCdDeposito()),
                    )
                    if (resp.isSuccessful) atualizados++
                }
                Toast.makeText(
                    this@RecontagemActivity,
                    "$atualizados itens atualizados com valores da recontagem",
                    Toast.LENGTH_LONG,
                ).show()
                finish()
            } catch (e: Exception) {
                Toast.makeText(this@RecontagemActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.visibility = View.GONE
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }

    inner class RecontagemAdapter(private val lista: List<ItemRecontagem>) :
        RecyclerView.Adapter<RecontagemAdapter.VH>() {

        inner class VH(val b: ItemRecontagemBinding) : RecyclerView.ViewHolder(b.root)

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
            VH(ItemRecontagemBinding.inflate(LayoutInflater.from(parent.context), parent, false))

        override fun getItemCount() = lista.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val rec = lista[position]
            with(holder.b) {
                tvProduto.text = rec.item.produto
                tvContagem1.text = "1ª: ${"%.2f".format(rec.item.qtde_contada ?: 0.0)}"
                if (rec.qtde2 > 0) {
                    tvContagem2.text = "2ª: ${"%.2f".format(rec.qtde2)}"
                    val dif = rec.qtde2 - (rec.item.qtde_contada ?: 0.0)
                    tvDiferenca.text = if (abs(dif) > 0.001) "${"%.2f".format(dif)}" else "="
                    val ok = abs(dif) <= 0.001
                    tvStatus.text = if (ok) "✓" else "✗"
                    tvStatus.setTextColor(if (ok) 0xFF2E7D32.toInt() else 0xFFC62828.toInt())
                    tvDiferenca.setTextColor(if (ok) 0xFF2E7D32.toInt() else 0xFFC62828.toInt())
                } else {
                    tvContagem2.text = "2ª: —"
                    tvDiferenca.text = "—"
                    tvStatus.text = "·"
                    tvStatus.setTextColor(0xFF9E9E9E.toInt())
                    tvDiferenca.setTextColor(0xFF9E9E9E.toInt())
                }
            }
        }
    }
}
