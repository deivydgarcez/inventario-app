package br.com.inventario.ui.relatorio

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import br.com.inventario.ui.auditoria.AuditoriaActivity
import br.com.inventario.ui.base.TimeoutActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.ItemTouchHelper
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import br.com.inventario.data.api.RetrofitClient
import br.com.inventario.R
import br.com.inventario.data.model.ConsolidarRequest
import br.com.inventario.data.model.EditarBipagemRequest
import br.com.inventario.data.model.ItemRelatorio
import br.com.inventario.databinding.ActivityRelatorioBinding
import br.com.inventario.ui.historico.HistoricoActivity
import br.com.inventario.ui.recontagem.RecontagemActivity
import br.com.inventario.util.SessionManager
import com.google.android.material.button.MaterialButton
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import kotlinx.coroutines.async
import kotlinx.coroutines.launch
import kotlin.math.abs

class RelatorioActivity : TimeoutActivity() {

    private lateinit var binding: ActivityRelatorioBinding
    private lateinit var session: SessionManager
    private var adapter: RelatorioAdapter? = null
    private var recontagemConfirmada = false
    private var consolidarAposCarregar = false
    private var skipNextResume = false

    private val recontarLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        recontagemConfirmada = true
        consolidarAposCarregar = result.data?.getBooleanExtra("consolidar_direto", false) == true
        skipNextResume = true  // onResume() dispara logo após o launcher — evita duplo carregamento
        carregarRelatorio()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityRelatorioBinding.inflate(layoutInflater)
        setContentView(binding.root)

        WindowCompat.setDecorFitsSystemWindows(window, false)

        session = SessionManager(this)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "Relatório: ${session.getNomeDeposito()}"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        ViewCompat.setOnApplyWindowInsetsListener(binding.toolbar) { v, insets ->
            val top = insets.getInsets(WindowInsetsCompat.Type.statusBars()).top
            v.setPadding(v.paddingLeft, top, v.paddingRight, v.paddingBottom)
            insets
        }

        binding.recycler.layoutManager = LinearLayoutManager(this)
        binding.btnConsolidar.setOnClickListener { confirmarConsolidar() }
        binding.btnRecontagem.setOnClickListener {
            recontarLauncher.launch(Intent(this, RecontagemActivity::class.java))
        }
        binding.btnHistorico.setOnClickListener {
            startActivity(Intent(this, HistoricoActivity::class.java))
        }
        binding.btnAuditoria.setOnClickListener {
            startActivity(Intent(this, AuditoriaActivity::class.java))
        }

        val swipeHelper = object : ItemTouchHelper.SimpleCallback(0, ItemTouchHelper.LEFT or ItemTouchHelper.RIGHT) {
            override fun onMove(rv: RecyclerView, vh: RecyclerView.ViewHolder, t: RecyclerView.ViewHolder) = false
            override fun onSwiped(viewHolder: RecyclerView.ViewHolder, direction: Int) {
                val pos = viewHolder.adapterPosition
                if (pos == RecyclerView.NO_POSITION) { carregarRelatorio(); return }
                val item = adapter?.getItem(pos) ?: return
                confirmarRemocao(item, pos)
            }
        }
        ItemTouchHelper(swipeHelper).attachToRecyclerView(binding.recycler)

        carregarRelatorio()
    }

    override fun onResume() {
        super.onResume()
        if (skipNextResume) { skipNextResume = false; return }
        carregarRelatorio()
    }

    private fun carregarRelatorio() {
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val dep = session.getCdDeposito()

                val deferRelatorio = async { api.relatorio(dep) }
                val deferResumo   = async { api.resumoContagem(dep) }

                val respRelatorio = deferRelatorio.await()
                val respResumo    = deferResumo.await()

                if (respRelatorio.isSuccessful) {
                    val items = respRelatorio.body()?.toMutableList() ?: mutableListOf()
                    adapter = RelatorioAdapter(items) { item, pos -> editarItem(item, pos) }
                    binding.recycler.adapter = adapter
                    atualizarResumo(items)
                    if (consolidarAposCarregar) {
                        consolidarAposCarregar = false
                        confirmarConsolidar()
                    }
                } else {
                    Toast.makeText(this@RelatorioActivity, "Erro ao carregar relatório", Toast.LENGTH_SHORT).show()
                }

                val resumo = respResumo.body()
                if (resumo != null && resumo.naoContados > 0) {
                    val exemplos = if (resumo.produtosNaoContados.isNotEmpty())
                        "\nEx: " + resumo.produtosNaoContados.take(3).joinToString(", ")
                    else ""
                    binding.tvAvisoNaoContados.text =
                        "⚠ ${resumo.naoContados} produto(s) com estoque não foram contados nesta sessão.$exemplos"
                    binding.tvAvisoNaoContados.visibility = View.VISIBLE
                } else {
                    binding.tvAvisoNaoContados.visibility = View.GONE
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

        val temItens = items.isNotEmpty()
        binding.tvDicaSwipe.visibility = if (temItens) View.VISIBLE else View.GONE

        if (divergencias > 0) {
            binding.btnRecontagem.text = "✓ Fazer Recontagem (Recomendado)"
            binding.btnRecontagem.backgroundTintList =
                android.content.res.ColorStateList.valueOf(0xFF388E3C.toInt())
        } else {
            binding.btnRecontagem.text = "Verificar contagem"
            binding.btnRecontagem.backgroundTintList =
                android.content.res.ColorStateList.valueOf(0xFF757575.toInt())
        }

        binding.btnRecontagem.isEnabled = temItens
        binding.btnHistorico.isEnabled = true

        val bloqueado = session.isConsolidarBloqueado(session.getCdDeposito())
        if (bloqueado) {
            binding.btnConsolidar.isEnabled = false
            binding.tvAvisoBloqueio.visibility = View.VISIBLE
        } else {
            binding.btnConsolidar.isEnabled = temItens
            binding.tvAvisoBloqueio.visibility = View.GONE
        }
    }

    private fun editarItem(item: ItemRelatorio, position: Int) {
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 16, 48, 0)
        }
        val etQtde = EditText(this).apply {
            hint = "Nova quantidade"
            inputType = android.text.InputType.TYPE_CLASS_NUMBER or android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL
            setText("%.2f".format(item.qtde_contada ?: 0.0))
        }
        val etMotivo = EditText(this).apply {
            hint = "Motivo da alteração (obrigatório)"
        }
        layout.addView(etQtde)
        layout.addView(etMotivo)

        AlertDialog.Builder(this)
            .setTitle("Editar: ${item.produto}")
            .setMessage("Quantidade atual: ${item.qtde_contada?.toInt() ?: 0}")
            .setView(layout)
            .setPositiveButton("Salvar") { _, _ ->
                val novaQtde = etQtde.text.toString().toDoubleOrNull() ?: return@setPositiveButton
                val motivo = etMotivo.text.toString().trim()
                if (motivo.isEmpty()) {
                    Toast.makeText(this, "Informe o motivo da alteração", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                editarItemComAuditoria(item, position, novaQtde, motivo)
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun confirmarRemocao(item: ItemRelatorio, position: Int) {
        val etMotivo = EditText(this).apply {
            hint = "Motivo da exclusão (obrigatório)"
            setPadding(48, 24, 48, 24)
        }
        AlertDialog.Builder(this)
            .setTitle("Remover '${item.produto}'")
            .setMessage("Informe o motivo para registrar na auditoria:")
            .setView(etMotivo)
            .setPositiveButton("Remover") { _, _ ->
                val motivo = etMotivo.text.toString().trim()
                if (motivo.isEmpty()) {
                    Toast.makeText(this, "Informe o motivo para remover o item", Toast.LENGTH_SHORT).show()
                    carregarRelatorio()
                    return@setPositiveButton
                }
                lifecycleScope.launch {
                    try {
                        val api = RetrofitClient.build(session)
                        val resp = api.removerBipagem(
                            item.cdproduto,
                            session.getCdDeposito(),
                            motivo = motivo,
                            deviceId = session.getDeviceId(),
                        )
                        if (resp.isSuccessful) {
                            adapter?.removeItem(position)
                            val currentItems = (0 until (adapter?.itemCount ?: 0)).map { adapter!!.getItem(it) }
                            atualizarResumo(currentItems)
                        } else {
                            Toast.makeText(this@RelatorioActivity, "Erro ao remover item", Toast.LENGTH_SHORT).show()
                            carregarRelatorio()
                        }
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
            append("$total itens para consolidar.\n")
            if (divergencias > 0) {
                append("$divergencias itens com diferença de estoque.\n\nFaça a recontagem antes de consolidar para garantir os valores.")
            } else {
                append("Sem divergências encontradas. Pode consolidar com segurança.")
            }
        }

        val view = LayoutInflater.from(this).inflate(R.layout.dialog_consolidar, null)
        view.findViewById<android.widget.TextView>(R.id.tvMensagemConsolidar).text = msg

        var dialog: AlertDialog? = null

        val btnConsolidarNow = view.findViewById<MaterialButton>(R.id.btnConsolidarNow)
        if (divergencias > 0) {
            view.findViewById<MaterialButton>(R.id.btnFazerRecontagem).apply {
                visibility = View.VISIBLE
                setOnClickListener {
                    dialog?.dismiss()
                    recontarLauncher.launch(Intent(this@RelatorioActivity, RecontagemActivity::class.java))
                }
            }
            btnConsolidarNow.text = "Consolidar mesmo assim"
        } else {
            btnConsolidarNow.text = "Consolidar agora"
        }

        btnConsolidarNow.setOnClickListener {
            dialog?.dismiss()
            if (divergencias > 0) pedirSupervisor() else consolidar(null, null)
        }
        view.findViewById<MaterialButton>(R.id.btnCancelarConsolidar).setOnClickListener { dialog?.dismiss() }

        dialog = MaterialAlertDialogBuilder(this)
            .setView(view)
            .setCancelable(true)
            .create()
        dialog.show()
    }

    private fun pedirSupervisor() {
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 16, 48, 0)
        }
        val etLogin = EditText(this).apply { hint = "Login do supervisor" }
        val etSenha = EditText(this).apply {
            hint = "Senha do supervisor"
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD
        }
        layout.addView(etLogin)
        layout.addView(etSenha)

        AlertDialog.Builder(this)
            .setTitle("Autorização do supervisor")
            .setMessage("Há divergências. Um supervisor diferente de você deve autorizar esta consolidação.")
            .setView(layout)
            .setPositiveButton("Autorizar e Consolidar") { _, _ ->
                val login = etLogin.text.toString().trim()
                val senha = etSenha.text.toString().trim()
                when {
                    login.isEmpty() || senha.isEmpty() ->
                        Toast.makeText(this, "Informe login e senha do supervisor", Toast.LENGTH_SHORT).show()
                    login.equals(session.getUsuario(), ignoreCase = true) && session.getRole() == "operador" ->
                        Toast.makeText(this, "Operadores não podem autorizar a própria consolidação. Chame um gerente.", Toast.LENGTH_LONG).show()
                    else ->
                        consolidar(login, senha)
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }

    private fun consolidar(supervisorLogin: String?, supervisorSenha: String?) {
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val response = api.consolidar(ConsolidarRequest(
                    cddeposito = session.getCdDeposito(),
                    operador = session.getOperador(),
                    supervisorLogin = supervisorLogin,
                    supervisorSenha = supervisorSenha,
                    recontagemConfirmada = recontagemConfirmada,
                ))
                if (response.isSuccessful) {
                    recontagemConfirmada = false
                    session.setConsolidarBloqueado(session.getCdDeposito(), false)
                    val body = response.body()
                    val inv = body?.idinventario?.let { " (Inv. nº $it)" } ?: ""
                    val msg = (body?.mensagem ?: "Consolidado com sucesso") + inv
                    Toast.makeText(this@RelatorioActivity, msg, Toast.LENGTH_LONG).show()
                    carregarRelatorio()
                } else {
                    val detail = try {
                        val body = response.errorBody()?.string() ?: ""
                        org.json.JSONObject(body).getString("detail")
                    } catch (_: Exception) { "Erro ao consolidar" }
                    Toast.makeText(this@RelatorioActivity, detail, Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@RelatorioActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.visibility = View.GONE
            }
        }
    }

    private fun editarItemComAuditoria(item: ItemRelatorio, position: Int, novaQtde: Double, motivo: String) {
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val resp = api.editarBipagem(item.cdproduto, EditarBipagemRequest(
                    qtde = novaQtde,
                    cddeposito = session.getCdDeposito(),
                    motivo = motivo,
                    deviceId = session.getDeviceId(),
                ))
                if (resp.isSuccessful) {
                    adapter?.updateItem(position, novaQtde)
                    Toast.makeText(this@RelatorioActivity, "Quantidade atualizada", Toast.LENGTH_SHORT).show()
                    val currentItems = (0 until (adapter?.itemCount ?: 0)).map { adapter!!.getItem(it) }
                    atualizarResumo(currentItems)
                } else {
                    val detail = try {
                        org.json.JSONObject(resp.errorBody()?.string() ?: "").getString("detail")
                    } catch (_: Exception) { "Erro ao atualizar quantidade" }
                    Toast.makeText(this@RelatorioActivity, detail, Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@RelatorioActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
