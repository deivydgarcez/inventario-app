package br.com.inventario.ui.relatorio

import android.graphics.Color
import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import br.com.inventario.data.model.ItemRelatorio
import br.com.inventario.databinding.ItemRelatorioBinding

class RelatorioAdapter(
    private val items: MutableList<ItemRelatorio>,
    private val onEdit: (ItemRelatorio, Int) -> Unit,
) : RecyclerView.Adapter<RelatorioAdapter.VH>() {

    inner class VH(val binding: ItemRelatorioBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        VH(ItemRelatorioBinding.inflate(LayoutInflater.from(parent.context), parent, false))

    override fun getItemCount() = items.size

    fun getItem(position: Int): ItemRelatorio = items[position]

    fun removeItem(position: Int) {
        items.removeAt(position)
        notifyItemRemoved(position)
    }

    fun updateItem(position: Int, novaQtde: Double) {
        val item = items[position]
        val novaDif = novaQtde - (item.qtde_sistema ?: 0.0)
        items[position] = item.copy(qtde_contada = novaQtde, diferenca = novaDif)
        notifyItemChanged(position)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val item = items[position]
        with(holder.binding) {
            tvProduto.text = item.produto
            tvCodigo.text = buildString {
                append("Cód. Int.: ${item.cdproduto}")
                if (!item.codigobarra.isNullOrBlank()) append("  •  ${item.codigobarra}")
            }
            tvSistema.text = buildString {
                append("Sistema: ${item.qtde_sistema?.let { "%.2f".format(it) } ?: "N/D"}")
                val entrega = item.qtde_entrega ?: 0.0
                if (entrega > 0.001) append("  (+%.2f entrega)".format(entrega))
            }
            tvContada.text = "Contada: ${item.qtde_contada?.let { "%.2f".format(it) } ?: "0"}"
            val dif = item.diferenca ?: 0.0
            tvDiferenca.text = "Dif: ${"%.2f".format(dif)}"
            tvDiferenca.setTextColor(when {
                dif > 0 -> Color.parseColor("#2E7D32")
                dif < 0 -> Color.parseColor("#C62828")
                else    -> Color.parseColor("#555555")
            })
            root.setOnClickListener {
                val pos = holder.adapterPosition
                if (pos != RecyclerView.NO_POSITION) onEdit(item, pos)
            }
        }
    }
}
