package br.com.inventario.ui.usuarios

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import br.com.inventario.data.model.DispositivoInfo
import br.com.inventario.databinding.ItemDeviceBinding

class DeviceAdapter(
    private val items: List<DispositivoInfo>,
    private val onRemove: (DispositivoInfo) -> Unit,
) : RecyclerView.Adapter<DeviceAdapter.VH>() {

    inner class VH(val b: ItemDeviceBinding) : RecyclerView.ViewHolder(b.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        VH(ItemDeviceBinding.inflate(LayoutInflater.from(parent.context), parent, false))

    override fun getItemCount() = items.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val d = items[position]
        with(holder.b) {
            tvNomeDispositivo.text = d.nomeDispositivo?.takeIf { it.isNotBlank() }
                ?: "Dispositivo desconhecido"
            tvDeviceId.text = if (d.deviceId.length > 12) d.deviceId.take(12) + "…" else d.deviceId
            tvUltimoAcesso.text = "Último acesso: ${formatarData(d.ultimoAcesso)}"
            tvPrimeiroAcesso.text = "Cadastrado: ${formatarData(d.primeiroAcesso)}"
            btnRemover.setOnClickListener { onRemove(d) }
        }
    }

    private fun formatarData(iso: String?): String {
        if (iso.isNullOrBlank()) return "—"
        return iso.replace("T", " ").take(16)
    }
}
