package br.com.inventario.ui.operadores

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
import br.com.inventario.data.model.Operador
import br.com.inventario.data.model.OperadorRequest
import br.com.inventario.databinding.ActivityOperadoresBinding
import br.com.inventario.databinding.ItemOperadorBinding
import br.com.inventario.ui.base.TimeoutActivity
import br.com.inventario.util.GlassDialog
import br.com.inventario.util.SessionManager
import kotlinx.coroutines.launch

class OperadoresActivity : TimeoutActivity() {

    private lateinit var binding: ActivityOperadoresBinding
    private lateinit var session: SessionManager
    private val operadores = mutableListOf<Operador>()
    private lateinit var adapter: OperadoresAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityOperadoresBinding.inflate(layoutInflater)
        setContentView(binding.root)

        WindowCompat.setDecorFitsSystemWindows(window, false)
        session = SessionManager(this)

        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "Operadores"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        ViewCompat.setOnApplyWindowInsetsListener(binding.toolbar) { v, insets ->
            val top = insets.getInsets(WindowInsetsCompat.Type.statusBars()).top
            v.setPadding(v.paddingLeft, top, v.paddingRight, v.paddingBottom)
            insets
        }

        adapter = OperadoresAdapter(operadores) { op -> confirmarToggle(op) }
        binding.recycler.layoutManager = LinearLayoutManager(this)
        binding.recycler.adapter = adapter

        binding.fabAdicionarOperador.setOnClickListener { dialogNovoOperador() }

        carregarOperadores()
    }

    private fun carregarOperadores() {
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val resp = api.listarOperadores()
                if (resp.isSuccessful) {
                    operadores.clear()
                    operadores.addAll(resp.body() ?: emptyList())
                    adapter.notifyDataSetChanged()
                    val ativos = operadores.count { it.ativo == 1 }
                    binding.tvTotal.text = "${operadores.size} operadores · $ativos ativos"
                } else {
                    Toast.makeText(this@OperadoresActivity, "Erro ao carregar", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@OperadoresActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.visibility = View.GONE
            }
        }
    }

    private fun dialogNovoOperador() {
        GlassDialog.input(
            context = this,
            title = "Novo Operador",
            hint = "Nome do operador",
            positiveText = "Adicionar"
        ) { nome ->
            if (nome.isBlank()) return@input
            lifecycleScope.launch {
                try {
                    val api = RetrofitClient.build(session)
                    val resp = api.criarOperador(OperadorRequest(nome))
                    if (resp.isSuccessful) {
                        Toast.makeText(this@OperadoresActivity, "Operador '$nome' adicionado", Toast.LENGTH_SHORT).show()
                        carregarOperadores()
                    } else {
                        Toast.makeText(this@OperadoresActivity, "Erro ao adicionar", Toast.LENGTH_SHORT).show()
                    }
                } catch (e: Exception) {
                    Toast.makeText(this@OperadoresActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun confirmarToggle(op: Operador) {
        val acao = if (op.ativo == 1) "desativar" else "reativar"
        GlassDialog.show(
            context = this,
            title = "${acao.replaceFirstChar { it.uppercase() }} operador",
            message = "Deseja $acao '${op.nome}'?",
            positiveText = acao.replaceFirstChar { it.uppercase() },
            negativeText = "Cancelar",
            onPositive = {
                lifecycleScope.launch {
                    try {
                        val api = RetrofitClient.build(session)
                        val resp = api.toggleOperador(op.id)
                        if (resp.isSuccessful) {
                            carregarOperadores()
                        } else {
                            Toast.makeText(this@OperadoresActivity, "Erro", Toast.LENGTH_SHORT).show()
                        }
                    } catch (e: Exception) {
                        Toast.makeText(this@OperadoresActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        )
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }

    inner class OperadoresAdapter(
        private val lista: List<Operador>,
        private val onToggle: (Operador) -> Unit,
    ) : RecyclerView.Adapter<OperadoresAdapter.VH>() {

        inner class VH(val b: ItemOperadorBinding) : RecyclerView.ViewHolder(b.root)

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
            VH(ItemOperadorBinding.inflate(LayoutInflater.from(parent.context), parent, false))

        override fun getItemCount() = lista.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val op = lista[position]
            with(holder.b) {
                tvNome.text = op.nome
                val ativo = op.ativo == 1
                tvStatus.text = if (ativo) "● Ativo" else "○ Inativo"
                tvStatus.setTextColor(
                    if (ativo) 0xFF2E7D32.toInt() else 0xFF9E9E9E.toInt()
                )
                ivStatus.alpha = if (ativo) 1f else 0.35f
                ivStatus.setColorFilter(
                    if (ativo) 0xFFCC5B2A.toInt() else 0xFF9E9E9E.toInt()
                )
                btnToggle.text = if (ativo) "Desativar" else "Reativar"
                btnToggle.setOnClickListener { onToggle(op) }
            }
        }
    }
}
