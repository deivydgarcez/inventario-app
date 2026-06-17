package br.com.inventario.ui.scanner

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import br.com.inventario.databinding.ItemScannedBinding

data class ScannedItem(val cdproduto: Int, val nome: String, var qtde: Double)

class ScannedItemsAdapter(
    private val items: List<ScannedItem>,
    private val onEdit: (ScannedItem) -> Unit,
) : RecyclerView.Adapter<ScannedItemsAdapter.VH>() {

    inner class VH(val b: ItemScannedBinding) : RecyclerView.ViewHolder(b.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        VH(ItemScannedBinding.inflate(LayoutInflater.from(parent.context), parent, false))

    override fun getItemCount() = items.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val item = items[position]
        holder.b.tvNomeProduto.text = item.nome
        holder.b.tvQtde.text = "%.0f un.".format(item.qtde)
        holder.b.root.setOnClickListener { onEdit(item) }
    }
}
