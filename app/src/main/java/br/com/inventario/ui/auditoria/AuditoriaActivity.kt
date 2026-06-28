package br.com.inventario.ui.auditoria

import android.graphics.Color
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import br.com.inventario.data.api.RetrofitClient
import br.com.inventario.data.model.LogAuditoria
import br.com.inventario.databinding.ActivityAuditoriaBinding
import br.com.inventario.databinding.ItemAuditoriaBinding
import br.com.inventario.ui.base.TimeoutActivity
import br.com.inventario.util.SessionManager
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

class AuditoriaActivity : TimeoutActivity() {

    private lateinit var binding: ActivityAuditoriaBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAuditoriaBinding.inflate(layoutInflater)
        setContentView(binding.root)

        session = SessionManager(this)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "Auditoria: ${session.getNomeDeposito()}"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        binding.recycler.layoutManager = LinearLayoutManager(this)
        carregarLog()
    }

    private fun carregarLog() {
        binding.progressBar.visibility = View.VISIBLE
        binding.tvVazio.visibility = View.GONE
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val resp = api.logAuditoria(session.getCdDeposito())
                if (resp.isSuccessful) {
                    val lista = resp.body() ?: emptyList()
                    if (lista.isEmpty()) {
                        binding.tvVazio.visibility = View.VISIBLE
                        binding.recycler.visibility = View.GONE
                    } else {
                        binding.recycler.adapter = AuditoriaAdapter(lista)
                        binding.recycler.visibility = View.VISIBLE
                    }
                } else if (resp.code() == 403) {
                    binding.tvVazio.text = "Acesso restrito a gerentes e administradores."
                    binding.tvVazio.visibility = View.VISIBLE
                    binding.recycler.visibility = View.GONE
                } else {
                    Toast.makeText(this@AuditoriaActivity, "Erro ao carregar log", Toast.LENGTH_SHORT).show()
                }
            } catch (_: CancellationException) {
            } catch (e: Exception) {
                Toast.makeText(this@AuditoriaActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.visibility = View.GONE
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }

    inner class AuditoriaAdapter(private val lista: List<LogAuditoria>) :
        RecyclerView.Adapter<AuditoriaAdapter.VH>() {

        inner class VH(val b: ItemAuditoriaBinding) : RecyclerView.ViewHolder(b.root)

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
            VH(ItemAuditoriaBinding.inflate(LayoutInflater.from(parent.context), parent, false))

        override fun getItemCount() = lista.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val log = lista[position]
            with(holder.b) {
                // Tipo com cor
                tvTipo.text = when (log.tipo) {
                    "CONSOLID_SEM_RECONTAGEM" -> "SEM RECONTAGEM"
                    else -> log.tipo
                }
                val cor = when (log.tipo) {
                    "EDICAO"                   -> Color.parseColor("#E65100")  // laranja
                    "EDICAO_SUSPEITA"          -> Color.parseColor("#B71C1C")  // vermelho escuro
                    "EXCLUSAO"                 -> Color.parseColor("#C62828")  // vermelho
                    "CONSOLIDACAO"             -> Color.parseColor("#1B5E20")  // verde
                    "CONSOLID_SEM_RECONTAGEM"  -> Color.parseColor("#4A148C")  // roxo — requer atenção
                    "ALERTA"                   -> Color.parseColor("#F57F17")  // amarelo
                    "ALERTA_REESCAN"           -> Color.parseColor("#880E4F")  // roxo escuro
                    else                       -> Color.parseColor("#37474F")
                }
                tvTipo.background.mutate().setTint(cor)

                // Data/hora
                tvDataHora.text = log.dataHora
                    ?.replace("T", " ")
                    ?.substringBefore(".")
                    ?: ""

                // Produto
                tvProduto.text = log.produto ?: when (log.tipo) {
                    "CONSOLIDACAO"            -> "Consolidação de inventário"
                    "CONSOLID_SEM_RECONTAGEM" -> "Justificativa: ${log.motivo ?: "(sem texto)"}"
                    else                      -> "Produto #${log.cdproduto}"
                }

                // Quantidades
                val antes = log.qtdeAntes
                val depois = log.qtdeDepois
                tvQuantidades.text = when {
                    antes != null && depois != null -> "Antes: ${"%.2f".format(antes)}  →  Depois: ${"%.2f".format(depois)}"
                    depois != null -> "Total: ${"%.2f".format(depois)}"
                    antes != null -> "Removido: ${"%.2f".format(antes)}"
                    else -> ""
                }
                tvQuantidades.visibility = if (tvQuantidades.text.isEmpty()) View.GONE else View.VISIBLE

                // Operador e usuário
                val partes = listOfNotNull(
                    log.operador?.let { "Operador: $it" },
                    log.loginUsuario?.let { "Usuário: $it" },
                )
                tvOperador.text = partes.joinToString("  ·  ")
                tvOperador.visibility = if (partes.isEmpty()) View.GONE else View.VISIBLE

                // Motivo
                if (!log.motivo.isNullOrBlank()) {
                    tvMotivo.text = "Motivo: ${log.motivo}"
                    tvMotivo.visibility = View.VISIBLE
                } else {
                    tvMotivo.visibility = View.GONE
                }

                // Device
                if (!log.deviceId.isNullOrBlank()) {
                    tvDevice.text = "Dispositivo: ${log.deviceId}"
                    tvDevice.visibility = View.VISIBLE
                } else {
                    tvDevice.visibility = View.GONE
                }
            }
        }
    }
}
