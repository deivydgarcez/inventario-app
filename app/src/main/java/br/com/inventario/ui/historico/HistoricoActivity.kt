package br.com.inventario.ui.historico

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import br.com.inventario.data.api.RetrofitClient
import br.com.inventario.data.model.ItemHistorico
import br.com.inventario.databinding.ActivityHistoricoBinding
import br.com.inventario.databinding.ItemHistoricoBinding
import br.com.inventario.ui.base.TimeoutActivity
import br.com.inventario.util.SessionManager
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

class HistoricoActivity : TimeoutActivity() {

    private lateinit var binding: ActivityHistoricoBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityHistoricoBinding.inflate(layoutInflater)
        setContentView(binding.root)

        WindowCompat.setDecorFitsSystemWindows(window, false)
        session = SessionManager(this)

        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "Histórico: ${session.getNomeDeposito()}"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        ViewCompat.setOnApplyWindowInsetsListener(binding.toolbar) { v, insets ->
            val top = insets.getInsets(WindowInsetsCompat.Type.statusBars()).top
            v.setPadding(v.paddingLeft, top, v.paddingRight, v.paddingBottom)
            insets
        }

        binding.recycler.layoutManager = LinearLayoutManager(this)
        carregarHistorico()
    }

    private fun carregarHistorico() {
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val response = api.historico(session.getCdDeposito())
                if (response.isSuccessful) {
                    val lista = response.body() ?: emptyList()
                    binding.tvTotalHistorico.text = "${lista.size} registros de consolidação"
                    if (lista.isEmpty()) {
                        binding.recycler.visibility = View.GONE
                        binding.tvVazio.visibility = View.VISIBLE
                    } else {
                        binding.recycler.adapter = HistoricoAdapter(lista)
                        binding.recycler.visibility = View.VISIBLE
                        binding.tvVazio.visibility = View.GONE
                    }
                } else {
                    Toast.makeText(this@HistoricoActivity, "Erro ao carregar histórico", Toast.LENGTH_SHORT).show()
                }
            } catch (_: CancellationException) {
                // Ignorado: usuário voltou enquanto carregava
            } catch (e: Exception) {
                Toast.makeText(this@HistoricoActivity, "Erro ao carregar histórico", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.visibility = View.GONE
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }

    inner class HistoricoAdapter(private val lista: List<ItemHistorico>) :
        RecyclerView.Adapter<HistoricoAdapter.VH>() {

        inner class VH(val b: ItemHistoricoBinding) : RecyclerView.ViewHolder(b.root)

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
            VH(ItemHistoricoBinding.inflate(LayoutInflater.from(parent.context), parent, false))

        override fun getItemCount() = lista.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val item = lista[position]
            with(holder.b) {
                tvProduto.text = item.produto
                tvContada.text = "Contada: ${"%.2f".format(item.qtde_contada ?: 0.0)}"
                tvSistema.text = "Sistema: ${"%.2f".format(item.qtde_sistema ?: 0.0)}"
                val dataStr = item.data?.take(16)?.replace("T", " ") ?: "sem data"
                val opStr = item.operador?.let { " · $it" } ?: ""
                tvData.text = "$dataStr$opStr"
            }
        }
    }
}
