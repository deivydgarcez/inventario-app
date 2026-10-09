package br.com.inventario.ui.usuarios

import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import br.com.inventario.data.api.RetrofitClient
import br.com.inventario.data.model.DispositivoInfo
import br.com.inventario.databinding.ActivityDevicesBinding
import br.com.inventario.ui.base.TimeoutActivity
import br.com.inventario.util.GlassDialog
import br.com.inventario.util.SessionManager
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

class DevicesActivity : TimeoutActivity() {

    private lateinit var binding: ActivityDevicesBinding
    private lateinit var session: SessionManager
    private val items = mutableListOf<DispositivoInfo>()
    private lateinit var adapter: DeviceAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDevicesBinding.inflate(layoutInflater)
        setContentView(binding.root)

        session = SessionManager(this)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "Dispositivos Autorizados"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        adapter = DeviceAdapter(items) { confirmarRemocao(it) }
        binding.recycler.layoutManager = LinearLayoutManager(this)
        binding.recycler.adapter = adapter

        carregarDispositivos()
    }

    private fun carregarDispositivos() {
        binding.progressBar.visibility = View.VISIBLE
        binding.tvEmpty.visibility = View.GONE
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val resp = api.listarDispositivos()
                if (resp.isSuccessful) {
                    items.clear()
                    items.addAll(resp.body() ?: emptyList())
                    adapter.notifyDataSetChanged()
                    binding.tvEmpty.visibility =
                        if (items.isEmpty()) View.VISIBLE else View.GONE
                } else {
                    Toast.makeText(this@DevicesActivity, "Erro ao carregar dispositivos", Toast.LENGTH_SHORT).show()
                }
            } catch (_: CancellationException) {
            } catch (_: Exception) {
                Toast.makeText(this@DevicesActivity, "Sem conexão", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.visibility = View.GONE
            }
        }
    }

    private fun confirmarRemocao(dispositivo: DispositivoInfo) {
        GlassDialog.show(
            context = this,
            title = "Remover dispositivo",
            message = "Remover \"${dispositivo.nomeDispositivo ?: dispositivo.deviceId}\"?\n\n" +
                    "Esse aparelho precisará de um slot livre para fazer login novamente.",
            positiveText = "Remover",
            negativeText = "Cancelar",
            onPositive = { removerDispositivo(dispositivo) }
        )
    }

    private fun removerDispositivo(dispositivo: DispositivoInfo) {
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val resp = api.removerDispositivo(dispositivo.id)
                if (resp.isSuccessful) {
                    items.remove(dispositivo)
                    adapter.notifyDataSetChanged()
                    binding.tvEmpty.visibility =
                        if (items.isEmpty()) View.VISIBLE else View.GONE
                    Toast.makeText(this@DevicesActivity, "Dispositivo removido", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this@DevicesActivity, "Erro ao remover", Toast.LENGTH_SHORT).show()
                }
            } catch (_: CancellationException) {
            } catch (_: Exception) {
                Toast.makeText(this@DevicesActivity, "Sem conexão", Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }
}
