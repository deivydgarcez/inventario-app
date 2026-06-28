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
import br.com.inventario.data.db.InvecDatabase
import br.com.inventario.data.db.ItemRelatorioLocal
import br.com.inventario.data.model.ConsolidarRequest
import br.com.inventario.data.model.EditarBipagemRequest
import br.com.inventario.data.model.ItemRelatorio
import br.com.inventario.databinding.ActivityRelatorioBinding
import br.com.inventario.ui.historico.HistoricoActivity
import br.com.inventario.ui.recontagem.RecontagemActivity
import br.com.inventario.util.ServerMonitor
import br.com.inventario.util.SessionManager
import br.com.inventario.util.SyncManager
import com.google.android.material.button.MaterialButton
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlin.math.abs

class RelatorioActivity : TimeoutActivity() {

    private lateinit var binding: ActivityRelatorioBinding
    private lateinit var session: SessionManager
    private lateinit var db: InvecDatabase
    private var adapter: RelatorioAdapter? = null
    private var recontagemConfirmada = false
    private var consolidarAposCarregar = false
    private var skipNextResume = false

    private val recontarLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        recontagemConfirmada = true
        consolidarAposCarregar = result.data?.getBooleanExtra("consolidar_direto", false) == true
        skipNextResume = true
        carregarRelatorio()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityRelatorioBinding.inflate(layoutInflater)
        setContentView(binding.root)

        WindowCompat.setDecorFitsSystemWindows(window, false)

        session = SessionManager(this)
        db = InvecDatabase.getInstance(this)
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
        binding.btnSincronizar.setOnClickListener { sincronizarManual() }
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
                if (!ServerMonitor.isOnline.value) {
                    Toast.makeText(this@RelatorioActivity, "Remoção requer conexão com o servidor", Toast.LENGTH_SHORT).show()
                    carregarRelatorio()
                    return
                }
                val item = adapter?.getItem(pos) ?: return
                confirmarRemocao(item, pos)
            }
        }
        ItemTouchHelper(swipeHelper).attachToRecyclerView(binding.recycler)

        ServerMonitor.startOrKeep(session, lifecycleScope)

        // Ao voltar online: sincroniza e recarrega do servidor antes de habilitar Consolidar.
        // Ao ficar offline: atualiza chip/botões sem recarregar (dados do adapter ainda válidos).
        lifecycleScope.launch {
            ServerMonitor.isOnline.collect { online ->
                if (online && adapter != null) {
                    carregarRelatorio()
                } else {
                    val currentAdapter = adapter ?: return@collect
                    val items = (0 until currentAdapter.itemCount).map { currentAdapter.getItem(it) }
                    atualizarResumo(items, online = false)
                }
            }
        }

        carregarRelatorio()
    }

    override fun onResume() {
        super.onResume()
        if (skipNextResume) { skipNextResume = false; return }
        carregarRelatorio()
    }

    private fun carregarRelatorio() {
        binding.progressBar.visibility = View.VISIBLE
        val sessionId = session.getSessionId()
        val dep = session.getCdDeposito()

        lifecycleScope.launch {
            val online = ServerMonitor.isOnline.value

            if (online) {
                // Sincroniza pendentes antes de exibir relatório completo
                SyncManager.sincronizarPendentes(db, session)

                // Após sync, nenhum pendente → esconde botão
                binding.btnSincronizar.visibility = View.GONE

                try {
                    val api = RetrofitClient.build(session)
                    val deferRelatorio = async { api.relatorio(dep, sessionId) }
                    val deferResumo   = async { api.resumoContagem(dep, sessionId) }

                    val respRelatorio = deferRelatorio.await()
                    val respResumo    = deferResumo.await()

                    if (respRelatorio.isSuccessful) {
                        val items = respRelatorio.body()?.toMutableList() ?: mutableListOf()
                        adapter = RelatorioAdapter(items) { item, pos -> editarItem(item, pos) }
                        binding.recycler.adapter = adapter
                        binding.tvAvisoNaoContados.visibility = View.GONE
                        atualizarResumo(items, online = true)
                        if (consolidarAposCarregar) {
                            consolidarAposCarregar = false
                            confirmarConsolidar()
                        }
                    } else {
                        val errBody = try { respRelatorio.errorBody()?.string() ?: "" } catch (_: Exception) { "" }
                        val detail = try {
                            org.json.JSONObject(errBody).getString("detail")
                        } catch (_: Exception) { "HTTP ${respRelatorio.code()}" }
                        Toast.makeText(this@RelatorioActivity, "Erro ao carregar relatório: $detail", Toast.LENGTH_LONG).show()
                    }

                    val resumo = respResumo.body()
                    if (resumo != null && resumo.naoContados > 0) {
                        val exemplos = if (resumo.produtosNaoContados.isNotEmpty())
                            "\nEx: " + resumo.produtosNaoContados.take(3).joinToString(", ")
                        else ""
                        binding.tvAvisoNaoContados.text =
                            "⚠ ${resumo.naoContados} produto(s) com estoque não foram contados.$exemplos"
                        binding.tvAvisoNaoContados.visibility = View.VISIBLE
                    }
                } catch (e: kotlinx.coroutines.CancellationException) {
                    throw e
                } catch (e: Exception) {
                    Toast.makeText(this@RelatorioActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
                    // Mesmo com falha de rede, habilita Consolidar se já há itens no adapter
                    val currentAdapter = adapter
                    if (currentAdapter != null) {
                        val items = (0 until currentAdapter.itemCount).map { currentAdapter.getItem(it) }
                        atualizarResumo(items, online = true)
                    }
                }
            } else {
                // Modo offline: constrói relatório a partir do Room
                if (sessionId != null) {
                    val locais = withContext(Dispatchers.IO) {
                        db.bipag.getRelatorioOffline(sessionId, dep)
                    }
                    val items = locais.map { it.toItemRelatorio() }.toMutableList()
                    adapter = RelatorioAdapter(items) { item, pos -> editarItem(item, pos) }
                    binding.recycler.adapter = adapter
                    atualizarResumo(items, online = false)

                    val pendentes = withContext(Dispatchers.IO) { db.bipag.countPendentes(sessionId) }
                    if (pendentes > 0) {
                        binding.tvAvisoNaoContados.text = "$pendentes scan(s) aguardando sincronização com o servidor"
                        binding.tvAvisoNaoContados.setBackgroundColor(0xFFE65100.toInt())
                        binding.tvAvisoNaoContados.visibility = View.VISIBLE
                        binding.btnSincronizar.visibility = View.VISIBLE
                    } else {
                        binding.tvAvisoNaoContados.visibility = View.GONE
                        binding.btnSincronizar.visibility = View.GONE
                    }
                } else {
                    binding.tvAvisoNaoContados.text = "Sem sessão ativa — selecione um depósito"
                    binding.tvAvisoNaoContados.setBackgroundColor(0xFF616161.toInt())
                    binding.tvAvisoNaoContados.visibility = View.VISIBLE
                    binding.btnSincronizar.visibility = View.GONE
                }
            }

            binding.progressBar.visibility = View.GONE
        }
    }

    private fun sincronizarManual() {
        if (!ServerMonitor.isOnline.value) {
            Toast.makeText(this, "Sem conexão com o servidor", Toast.LENGTH_SHORT).show()
            return
        }
        binding.btnSincronizar.isEnabled = false
        binding.btnSincronizar.text = "Sincronizando..."
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            SyncManager.sincronizarPendentes(db, session)
            carregarRelatorio()
            binding.btnSincronizar.isEnabled = true
            binding.btnSincronizar.text = "↑ Sincronizar com servidor agora"
        }
    }

    private fun atualizarResumo(items: List<ItemRelatorio>, online: Boolean = true) {
        val divergencias = items.count { abs(it.diferenca ?: 0.0) > 0.001 }
        val temItens = items.isNotEmpty()

        // Chip online/offline
        val pillColor = if (online) 0xFF388E3C.toInt() else 0xFF757575.toInt()
        binding.tvOnlinePill.text = if (online) "● Online" else "● Offline"
        (binding.tvOnlinePill.background as? android.graphics.drawable.GradientDrawable)
            ?.setColor(pillColor)

        binding.tvTotal.text = when {
            !temItens -> "Nenhum item bipado"
            divergencias > 0 -> "${items.size} itens · $divergencias divergência(s)"
            else -> "${items.size} itens · sem divergências"
        }

        binding.tvDicaSwipe.visibility = if (temItens) View.VISIBLE else View.GONE

        // Botão Recontagem
        if (divergencias > 0) {
            binding.btnRecontagem.text = "✓ Recontagem recomendada"
            binding.btnRecontagem.backgroundTintList =
                android.content.res.ColorStateList.valueOf(0xFF388E3C.toInt())
        } else {
            binding.btnRecontagem.text = "Verificar contagem"
            binding.btnRecontagem.backgroundTintList =
                android.content.res.ColorStateList.valueOf(0xFF757575.toInt())
        }
        binding.btnRecontagem.isEnabled = temItens

        // Aviso + botão Consolidar
        when {
            !online -> {
                binding.tvAvisoBloqueio.text = "⚠ Sem conexão — consolidação indisponível"
                binding.tvAvisoBloqueio.setBackgroundColor(0xFF616161.toInt())
                binding.tvAvisoBloqueio.visibility = View.VISIBLE
                binding.btnConsolidar.isEnabled = false
            }
            divergencias > 0 && !recontagemConfirmada -> {
                binding.tvAvisoBloqueio.text = "⚠ $divergencias divergência(s) — recontagem opcional, supervisor obrigatório"
                binding.tvAvisoBloqueio.setBackgroundColor(0xFFFF8F00.toInt())
                binding.tvAvisoBloqueio.visibility = View.VISIBLE
                binding.btnConsolidar.isEnabled = temItens
            }
            else -> {
                binding.tvAvisoBloqueio.visibility = View.GONE
                binding.btnConsolidar.isEnabled = temItens
            }
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

        val dialog = AlertDialog.Builder(this)
            .setTitle("Editar: ${item.produto}")
            .setMessage("Quantidade atual: ${item.qtde_contada?.toInt() ?: 0}")
            .setView(layout)
            .setPositiveButton("Salvar", null)
            .setNegativeButton("Cancelar", null)
            .show()
        dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
            val novaQtde = etQtde.text.toString().toDoubleOrNull()
            if (novaQtde == null) { etQtde.error = "Quantidade inválida"; return@setOnClickListener }
            val motivo = etMotivo.text.toString().trim()
            if (motivo.isEmpty()) { etMotivo.error = "Obrigatório"; return@setOnClickListener }
            editarItemComAuditoria(item, position, novaQtde, motivo)
            dialog.dismiss()
        }
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
                            motivo    = motivo,
                            deviceId  = session.getDeviceId(),
                            sessionId = session.getSessionId(),
                        )
                        if (resp.isSuccessful) {
                            adapter?.removeItem(position)
                            val currentItems = (0 until (adapter?.itemCount ?: 0)).map { adapter!!.getItem(it) }
                            atualizarResumo(currentItems, online = ServerMonitor.isOnline.value)
                        } else {
                            val errBody = try { resp.errorBody()?.string() ?: "" } catch (_: Exception) { "" }
                            val detail = try {
                                org.json.JSONObject(errBody).getString("detail")
                            } catch (_: Exception) { "HTTP ${resp.code()}" }
                            Toast.makeText(this@RelatorioActivity, "Erro ao remover: $detail", Toast.LENGTH_LONG).show()
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
                append("$divergencias itens com diferença de estoque.")
                if (recontagemConfirmada) append("\n\nRecontagem já realizada.")
            } else {
                append("Sem divergências. Pode consolidar com segurança.")
            }
        }

        val view = LayoutInflater.from(this).inflate(R.layout.dialog_consolidar, null)
        view.findViewById<android.widget.TextView>(R.id.tvMensagemConsolidar).text = msg

        var dialog: AlertDialog? = null

        // Recontagem sempre opcional — mostrar apenas se há divergências e ainda não foi feita
        if (divergencias > 0 && !recontagemConfirmada) {
            view.findViewById<MaterialButton>(R.id.btnFazerRecontagem).apply {
                visibility = View.VISIBLE
                text = "Fazer Recontagem (opcional)"
                setOnClickListener {
                    dialog?.dismiss()
                    recontarLauncher.launch(Intent(this@RelatorioActivity, RecontagemActivity::class.java))
                }
            }
        }

        val btnConsolidarNow = view.findViewById<MaterialButton>(R.id.btnConsolidarNow)
        btnConsolidarNow.text = when {
            divergencias == 0 -> "Consolidar"
            recontagemConfirmada -> "Consolidar (recontagem feita)"
            else -> "Consolidar sem recontagem"
        }

        btnConsolidarNow.setOnClickListener {
            dialog?.dismiss()
            when {
                divergencias == 0 -> consolidar(null, null)
                recontagemConfirmada && session.isSupervisor() -> consolidar(null, null)
                recontagemConfirmada -> pedirSupervisor()
                else -> pedirSupervisorComJustificativa()
            }
        }
        view.findViewById<MaterialButton>(R.id.btnCancelarConsolidar).setOnClickListener { dialog?.dismiss() }

        dialog = MaterialAlertDialogBuilder(this).setView(view).setCancelable(true).create()
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

        val d = AlertDialog.Builder(this)
            .setTitle("Autorização do supervisor")
            .setMessage("Recontagem realizada com divergências. Um supervisor deve autorizar.")
            .setView(layout)
            .setPositiveButton("Consolidar", null)
            .setNegativeButton("Cancelar", null)
            .show()
        d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
            val login = etLogin.text.toString().trim()
            val senha = etSenha.text.toString().trim()
            when {
                login.isEmpty() || senha.isEmpty() ->
                    Toast.makeText(this, "Informe login e senha do supervisor", Toast.LENGTH_SHORT).show()
                login.equals(session.getUsuario(), ignoreCase = true) && session.getRole() == "operador" ->
                    Toast.makeText(this, "Operadores não podem autorizar a própria consolidação", Toast.LENGTH_LONG).show()
                else -> { d.dismiss(); consolidar(login, senha) }
            }
        }
    }

    private fun pedirSupervisorComJustificativa() {
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 16, 48, 0)
        }
        val etLogin = EditText(this).apply { hint = "Login do supervisor" }
        val etSenha = EditText(this).apply {
            hint = "Senha do supervisor"
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD
        }
        val etJustificativa = EditText(this).apply {
            hint = "Por que não fará recontagem? (obrigatório)"
            minLines = 2
        }
        layout.addView(etLogin)
        layout.addView(etSenha)
        layout.addView(etJustificativa)

        val d = AlertDialog.Builder(this)
            .setTitle("Consolidar sem recontagem")
            .setMessage("Há ${(0 until (adapter?.itemCount ?: 0)).count { abs(adapter!!.getItem(it).diferenca ?: 0.0) > 0.001 }} divergências.\n\nInforme o motivo pelo qual a recontagem não será feita — ficará registrado na auditoria.")
            .setView(layout)
            .setPositiveButton("Consolidar", null)
            .setNegativeButton("Cancelar", null)
            .show()
        d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
            val login = etLogin.text.toString().trim()
            val senha = etSenha.text.toString().trim()
            val justificativa = etJustificativa.text.toString().trim()
            when {
                login.isEmpty() || senha.isEmpty() ->
                    Toast.makeText(this, "Informe login e senha do supervisor", Toast.LENGTH_SHORT).show()
                login.equals(session.getUsuario(), ignoreCase = true) && session.getRole() == "operador" ->
                    Toast.makeText(this, "Operadores não podem autorizar a própria consolidação", Toast.LENGTH_LONG).show()
                justificativa.length < 10 ->
                    Toast.makeText(this, "Justificativa muito curta — descreva o motivo com pelo menos 10 caracteres", Toast.LENGTH_LONG).show()
                else -> { d.dismiss(); consolidar(login, senha, justificativa) }
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }

    private fun consolidar(supervisorLogin: String?, supervisorSenha: String?, justificativaSemRecontagem: String? = null) {
        binding.progressBar.visibility = View.VISIBLE
        val sessionId = session.getSessionId()
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val response = api.consolidar(ConsolidarRequest(
                    cddeposito                = session.getCdDeposito(),
                    operador                  = session.getOperador(),
                    supervisorLogin           = supervisorLogin,
                    supervisorSenha           = supervisorSenha,
                    recontagemConfirmada      = recontagemConfirmada || session.isSupervisor(),
                    sessionId                 = sessionId,
                    justificativaSemRecontagem = justificativaSemRecontagem,
                ))
                if (response.isSuccessful) {
                    recontagemConfirmada = false
                    session.setConsolidarBloqueado(session.getCdDeposito(), false)

                    // Limpa dados locais desta sessão e inicia uma nova
                    if (sessionId != null) {
                        withContext(Dispatchers.IO) { db.bipag.deleteAllDaSessao(sessionId) }
                    }
                    session.encerrarSession()

                    val body = response.body()
                    val inv = body?.idinventario?.let { " (Inv. nº $it)" } ?: ""
                    val msg = (body?.mensagem ?: "Consolidado com sucesso") + inv
                    Toast.makeText(this@RelatorioActivity, msg, Toast.LENGTH_LONG).show()
                    carregarRelatorio()
                } else {
                    val errorBody = response.errorBody()?.string() ?: ""
                    val detail = try {
                        org.json.JSONObject(errorBody).getString("detail")
                    } catch (_: Exception) { "Erro ao consolidar" }
                    // Servidor exige supervisor (edições desta sessão) — abre dialog automaticamente
                    // Admin/gerente não precisam de outro supervisor, mostra erro genérico se 403
                    if (response.code() == 403 && detail.contains("Supervisor", ignoreCase = true) && !session.isSupervisor()) {
                        pedirSupervisor()
                    } else {
                        Toast.makeText(this@RelatorioActivity, detail, Toast.LENGTH_LONG).show()
                    }
                }
            } catch (e: kotlinx.coroutines.CancellationException) {
                throw e
            } catch (e: Exception) {
                // BUG-1: verifica se a consolidação ocorreu apesar do timeout de rede
                var consolidouSilenciosamente = false
                if (e is java.io.IOException || e is java.net.SocketTimeoutException) {
                    try {
                        val histResp = RetrofitClient.build(session).historico(session.getCdDeposito())
                        if (histResp.isSuccessful) {
                            val hoje = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.getDefault())
                                .format(java.util.Date())
                            consolidouSilenciosamente = histResp.body()?.firstOrNull()?.data?.startsWith(hoje) == true
                        }
                    } catch (_: Exception) {}
                }
                if (consolidouSilenciosamente) {
                    recontagemConfirmada = false
                    session.setConsolidarBloqueado(session.getCdDeposito(), false)
                    if (sessionId != null) {
                        withContext(Dispatchers.IO) { db.bipag.deleteAllDaSessao(sessionId) }
                    }
                    session.encerrarSession()
                    Toast.makeText(this@RelatorioActivity, "Consolidação verificada no histórico. Dados atualizados.", Toast.LENGTH_LONG).show()
                    carregarRelatorio()
                } else {
                    Toast.makeText(this@RelatorioActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            } finally {
                binding.progressBar.visibility = View.GONE
            }
        }
    }

    private fun editarItemComAuditoria(item: ItemRelatorio, position: Int, novaQtde: Double, motivo: String) {
        val sid = session.getSessionId() ?: return
        lifecycleScope.launch {
            if (ServerMonitor.isOnline.value) {
                try {
                    val api = RetrofitClient.build(session)
                    val resp = api.editarBipagem(item.cdproduto, EditarBipagemRequest(
                        qtde       = novaQtde,
                        cddeposito = session.getCdDeposito(),
                        motivo     = motivo,
                        deviceId   = session.getDeviceId(),
                        sessionId  = sid,
                    ))
                    if (resp.isSuccessful) {
                        adapter?.updateItem(position, novaQtde)
                        Toast.makeText(this@RelatorioActivity, "Quantidade atualizada", Toast.LENGTH_SHORT).show()
                        val currentItems = (0 until (adapter?.itemCount ?: 0)).map { adapter!!.getItem(it) }
                        atualizarResumo(currentItems, online = true)
                    } else {
                        val detail = try {
                            org.json.JSONObject(resp.errorBody()?.string() ?: "").getString("detail")
                        } catch (_: Exception) { "Erro ao atualizar quantidade" }
                        Toast.makeText(this@RelatorioActivity, detail, Toast.LENGTH_LONG).show()
                    }
                } catch (e: kotlinx.coroutines.CancellationException) {
                    throw e
                } catch (e: Exception) {
                    Toast.makeText(this@RelatorioActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            } else {
                // Offline: salva delta no Room; sincronizado ao reconectar via lote
                withContext(Dispatchers.IO) {
                    db.bipag.atualizarQtdeProduto(item.cdproduto, sid, novaQtde, offline = true)
                }
                adapter?.updateItem(position, novaQtde)
                val currentItems = (0 until (adapter?.itemCount ?: 0)).map { adapter!!.getItem(it) }
                atualizarResumo(currentItems, online = false)
                Toast.makeText(this@RelatorioActivity, "Salvo offline — será sincronizado ao reconectar", Toast.LENGTH_SHORT).show()
            }
        }
    }
}

private fun ItemRelatorioLocal.toItemRelatorio() = ItemRelatorio(
    cdproduto   = cdproduto,
    produto     = produto,
    codigobarra = codigobarra,
    qtde_sistema = qtdeSistema,
    qtde_contada = qtdeContada,
    diferenca   = diferenca,
    operador    = operador,
)
