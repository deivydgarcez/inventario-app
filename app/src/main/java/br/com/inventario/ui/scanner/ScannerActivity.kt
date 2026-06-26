package br.com.inventario.ui.scanner

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import android.view.KeyEvent
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import br.com.inventario.data.api.RetrofitClient
import br.com.inventario.data.db.BipagPendente
import br.com.inventario.data.db.InvecDatabase
import br.com.inventario.data.db.ProdutoCache

import br.com.inventario.data.model.BipagemRequest
import br.com.inventario.data.model.EditarBipagemRequest
import br.com.inventario.data.model.Produto
import br.com.inventario.databinding.ActivityScannerBinding
import br.com.inventario.ui.base.TimeoutActivity
import br.com.inventario.util.ServerMonitor
import br.com.inventario.util.SessionManager
import br.com.inventario.util.SyncManager
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class ScannerActivity : TimeoutActivity() {

    private enum class ScanMode { CAMERA, BLUETOOTH }

    private lateinit var binding: ActivityScannerBinding
    private lateinit var session: SessionManager
    private lateinit var db: InvecDatabase
    private lateinit var cameraExecutor: ExecutorService
    private var cameraProvider: ProcessCameraProvider? = null
    private var camera: Camera? = null
    private var flashLigado = false

    @Volatile private var processando = false
    @Volatile private var aguardandoScan = false

    private var scanMode = ScanMode.CAMERA
    private var totalBipagens = 0

    private val btBuffer = StringBuilder()
    private var btLastKeyTime = 0L
    private val BT_TIMEOUT_MS = 150L

    private val scannedItems = mutableListOf<ScannedItem>()
    private lateinit var scannedAdapter: ScannedItemsAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityScannerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        WindowCompat.setDecorFitsSystemWindows(window, false)

        session = SessionManager(this)
        db = InvecDatabase.getInstance(this)
        cameraExecutor = Executors.newSingleThreadExecutor()

        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = session.getNomeDeposito() ?: "Scanner"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        ViewCompat.setOnApplyWindowInsetsListener(binding.toolbar) { v, insets ->
            val top = insets.getInsets(WindowInsetsCompat.Type.statusBars()).top
            v.setPadding(v.paddingLeft, top, v.paddingRight, v.paddingBottom)
            insets
        }

        ViewCompat.setOnApplyWindowInsetsListener(binding.bottomPanel) { v, insets ->
            val nav = insets.getInsets(WindowInsetsCompat.Type.navigationBars()).bottom
            v.setPadding(v.paddingLeft, v.paddingTop, v.paddingRight, nav)
            insets
        }

        scannedAdapter = ScannedItemsAdapter(scannedItems) { item -> editarQuantidade(item) }
        binding.rvScanned.apply {
            layoutManager = LinearLayoutManager(this@ScannerActivity)
            adapter = scannedAdapter
        }

        binding.btnTrocarModo.setOnClickListener { mostrarSeletorModo() }
        binding.btnDigitarCodigo.setOnClickListener { digitarManualmente() }
        binding.btnEscanear.setOnClickListener { iniciarScan() }
        binding.switchMultiplo.setOnCheckedChangeListener { _, checked ->
            if (checked && !aguardandoScan && !processando && scanMode == ScanMode.CAMERA) {
                iniciarScan()
            }
        }

        val modoSalvo = session.getScanMode()
        aplicarModo(if (modoSalvo == "BLUETOOTH") ScanMode.BLUETOOTH else ScanMode.CAMERA)

        // Restaura mini-lista da sessão atual ao reabrir o scanner
        lifecycleScope.launch {
            val sid = session.getSessionId() ?: return@launch
            val cddeposito = session.getCdDeposito()
            val itens = withContext(Dispatchers.IO) { db.bipag.getRelatorioOffline(sid, cddeposito) }
            if (itens.isNotEmpty()) {
                // take(5) mostra os mais recentes; none-check evita duplicatas se um scan chegou antes desta coroutine
                itens.take(5).reversed().forEach { item ->
                    if (scannedItems.none { it.cdproduto == item.cdproduto }) {
                        scannedItems.add(ScannedItem(item.cdproduto, item.produto, item.qtdeContada))
                    }
                }
                if (scannedItems.isNotEmpty()) {
                    scannedAdapter.notifyDataSetChanged()
                    binding.rvScanned.visibility = View.VISIBLE
                }
            }
        }

        lifecycleScope.launch { verificarCatalogo() }

        // Monitor de conectividade
        ServerMonitor.startOrKeep(session, lifecycleScope)
        SyncManager.observarESync(db, session, lifecycleScope)

        lifecycleScope.launch {
            ServerMonitor.isOnline.collect { online ->
                try {
                    atualizarIndicadorConexao(online)
                    verificarCatalogo()
                } catch (_: Exception) { }
            }
        }
    }

    private suspend fun atualizarIndicadorConexao(online: Boolean) {
        val sid = session.getSessionId()
        val pendentes = if (sid != null) withContext(Dispatchers.IO) { db.bipag.countPendentes(sid) } else 0
        supportActionBar?.subtitle = if (online) {
            if (pendentes > 0) "Sincronizando $pendentes itens..." else "Online"
        } else {
            if (pendentes > 0) "Offline — $pendentes pendentes" else "Offline"
        }
    }

    private fun mostrarSeletorModo() {
        AlertDialog.Builder(this)
            .setTitle("Modo de leitura")
            .setItems(arrayOf("Câmera do celular", "Leitor Bluetooth")) { _, which ->
                if (which == 0) aplicarModo(ScanMode.CAMERA)
                else aplicarModo(ScanMode.BLUETOOTH)
            }
            .setCancelable(true)
            .show()
    }

    private fun iniciarScan() {
        if (processando) return
        aguardandoScan = true
        binding.btnEscanear.isEnabled = false
        binding.btnEscanear.text = "Aguardando..."
        binding.tvStatus.text = "Aponte a câmera para o código de barras"
        binding.tvStatus.visibility = View.VISIBLE

        lifecycleScope.launch {
            delay(6000)
            if (aguardandoScan) {
                aguardandoScan = false
                runOnUiThread { resetarBotaoEscanear() }
            }
        }
    }

    private fun resetarBotaoEscanear() {
        binding.btnEscanear.isEnabled = true
        binding.btnEscanear.text = "Escanear"
        if (!processando) binding.tvStatus.visibility = View.GONE
    }

    private fun digitarManualmente() {
        val input = EditText(this).apply {
            hint = "Digite o código de barras"
            inputType = android.text.InputType.TYPE_CLASS_TEXT
            setPadding(48, 32, 48, 32)
        }
        AlertDialog.Builder(this)
            .setTitle("Código manual")
            .setView(input)
            .setPositiveButton("Buscar") { _, _ ->
                val codigo = input.text.toString().trim()
                if (codigo.length >= 3 && !processando) {
                    processando = true
                    mostrarBuscando(codigo)
                    buscarProduto(codigo)
                } else if (codigo.isNotEmpty() && codigo.length < 3) {
                    Toast.makeText(this, "Código muito curto", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun aplicarModo(modo: ScanMode) {
        scanMode = modo
        session.saveScanMode(modo.name)
        if (modo == ScanMode.CAMERA) {
            binding.btModeLayout.visibility = View.GONE
            binding.previewView.visibility = View.VISIBLE
            binding.cameraOverlayTop.visibility = View.VISIBLE
            binding.cameraOverlayBottom.visibility = View.VISIBLE
            binding.scanFrame.visibility = View.VISIBLE
            binding.scanLine.visibility = View.VISIBLE
            binding.tvCameraInstruction.visibility = View.VISIBLE
            binding.btnEscanear.visibility = View.VISIBLE
            binding.switchRow.visibility = View.VISIBLE
            binding.btnTrocarModo.text = "Bluetooth"

            if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED
            ) {
                iniciarCamera()
            } else {
                ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CAMERA), 100)
            }
        } else {
            aguardandoScan = false
            if (flashLigado) {
                flashLigado = false
                camera?.cameraControl?.enableTorch(false)
            }
            cameraProvider?.unbindAll()
            binding.btModeLayout.visibility = View.VISIBLE
            binding.previewView.visibility = View.GONE
            binding.cameraOverlayTop.visibility = View.GONE
            binding.cameraOverlayBottom.visibility = View.GONE
            binding.scanFrame.visibility = View.GONE
            binding.scanLine.visibility = View.GONE
            binding.tvCameraInstruction.visibility = View.GONE
            binding.btnEscanear.visibility = View.GONE
            binding.switchRow.visibility = View.GONE
            binding.btnTrocarModo.text = "Câmera"
            btBuffer.clear()
            resetarBotaoEscanear()
        }
    }

    private fun iniciarCamera() {
        val future = ProcessCameraProvider.getInstance(this)
        future.addListener({
            cameraProvider = future.get()
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.previewView.surfaceProvider)
            }
            val analysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also { it.setAnalyzer(cameraExecutor) { img -> processarImagem(img) } }

            cameraProvider?.unbindAll()
            camera = cameraProvider?.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis)
            if (flashLigado) camera?.cameraControl?.enableTorch(true)
        }, ContextCompat.getMainExecutor(this))
    }

    @androidx.annotation.OptIn(ExperimentalGetImage::class)
    private fun processarImagem(imageProxy: ImageProxy) {
        if (!aguardandoScan || processando || scanMode != ScanMode.CAMERA) {
            imageProxy.close()
            return
        }

        val mediaImage = imageProxy.image ?: run { imageProxy.close(); return }
        val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)

        BarcodeScanning.getClient()
            .process(image)
            .addOnSuccessListener { barcodes ->
                val codigo = barcodes.firstOrNull { it.rawValue != null }?.rawValue
                if (codigo != null && aguardandoScan && !processando) {
                    aguardandoScan = false
                    processando = true
                    runOnUiThread {
                        mostrarBuscando(codigo)
                        buscarProduto(codigo)
                    }
                }
            }
            .addOnCompleteListener { imageProxy.close() }
    }

    private fun mostrarBuscando(codigo: String) {
        binding.tvStatus.text = "Buscando: $codigo..."
        binding.tvStatus.visibility = View.VISIBLE
    }

    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        if (scanMode == ScanMode.BLUETOOTH && event.action == KeyEvent.ACTION_DOWN) {
            val now = System.currentTimeMillis()
            if (now - btLastKeyTime > BT_TIMEOUT_MS) btBuffer.clear()
            btLastKeyTime = now

            when (event.keyCode) {
                KeyEvent.KEYCODE_ENTER, KeyEvent.KEYCODE_NUMPAD_ENTER -> {
                    val codigo = btBuffer.toString().trim()
                    btBuffer.clear()
                    if (codigo.length >= 3 && !processando) {
                        processando = true
                        mostrarBuscando(codigo)
                        buscarProduto(codigo)
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

    private suspend fun verificarCatalogo(): Boolean {
        val cddeposito = session.getCdDeposito()
        val total = withContext(Dispatchers.IO) { db.catalogo.count(cddeposito) }
        val offline = !ServerMonitor.isOnline.value

        val bloqueado = offline && total == 0
        if (bloqueado) {
            binding.layoutAvisoCatalogo.visibility = View.VISIBLE
            binding.btnEscanear.isEnabled = false
            binding.btnDigitarCodigo.isEnabled = false
            binding.tvAvisoTitulo.text = "Catálogo não baixado!"
            binding.tvAvisoMensagem.text =
                "Volte para a tela anterior, conecte ao servidor e selecione o depósito novamente para baixar o catálogo."
        } else {
            binding.layoutAvisoCatalogo.visibility = View.GONE
            binding.btnEscanear.isEnabled = true
            binding.btnDigitarCodigo.isEnabled = true
        }
        return bloqueado
    }

    private fun buscarProduto(codigo: String) {
        val cddeposito = session.getCdDeposito()
        val sessionId = session.getOuCriarSession()

        lifecycleScope.launch {
            var produto: Produto? = null
            var erroRede: Boolean = false

            if (ServerMonitor.isOnline.value) {
                // Online: tenta servidor (conectTimeout agora 5s)
                try {
                    val api = RetrofitClient.build(session)
                    val response = api.buscarPorBarcode(codigo, cddeposito)
                    when {
                        response.isSuccessful -> {
                            produto = response.body()!!
                            val barcode = produto.codigobarra
                            if (!barcode.isNullOrBlank()) {
                                db.catalogo.upsertBatch(listOf(ProdutoCache(
                                    codigobarra = barcode,
                                    cddeposito  = cddeposito,
                                    cdproduto   = produto.cdproduto,
                                    produto     = produto.produto,
                                    qtdeatual   = produto.qtdeatual ?: 0.0,
                                )))
                            }
                        }
                        response.code() == 404 -> {
                            mostrarErro("Produto não encontrado: $codigo")
                            resetarEstado()
                            return@launch
                        }
                        else -> { erroRede = true; throw Exception("HTTP ${response.code()}") }
                    }
                } catch (_: Exception) {
                    erroRede = true
                    val cached = withContext(Dispatchers.IO) { db.catalogo.getByBarcode(codigo, cddeposito) }
                    if (cached != null) {
                        produto = Produto(cached.cdproduto, cached.produto, cached.codigobarra, cached.qtdeatual)
                    }
                }
            } else {
                // Offline: vai direto ao cache local (sem esperar timeout de rede)
                erroRede = true
                val cached = withContext(Dispatchers.IO) { db.catalogo.getByBarcode(codigo, cddeposito) }
                if (cached != null) {
                    produto = Produto(cached.cdproduto, cached.produto, cached.codigobarra, cached.qtdeatual)
                }
            }

            if (produto != null) {
                registrarBipagem(produto, sessionId)
            } else {
                val totalCache = db.catalogo.count(cddeposito)
                if (erroRede && totalCache == 0) {
                    lifecycleScope.launch { verificarCatalogo() }
                } else {
                    mostrarErro("Produto não cadastrado no sistema")
                }
                resetarEstado()
            }
        }
    }

    private fun registrarBipagem(produto: Produto, sessionId: String) {
        val cddeposito = session.getCdDeposito()

        lifecycleScope.launch {
            try { _registrarBipagemInterno(produto, sessionId, cddeposito) }
            catch (e: Exception) {
                mostrarErro("Erro ao salvar scan: ${e.message}")
                resetarEstado()
            }
        }
    }

    private suspend fun _registrarBipagemInterno(produto: Produto, sessionId: String, cddeposito: Int) {
        // Snapshot de estoque: igual ao 1º scan deste produto na sessão
        val qtdeSistema = db.bipag.getQtdeSistema(produto.cdproduto, sessionId)
            ?: (produto.qtdeatual ?: 0.0)

        // UUID único por scan — permite idempotência no servidor caso timeout de rede gere retry via lote
        val scanId = java.util.UUID.randomUUID().toString()

        // 1. Salvar em Room imediatamente (funciona offline)
        val rowId = db.bipag.insert(BipagPendente(
            sessionId   = sessionId,
            cdproduto   = produto.cdproduto,
            produto     = produto.produto,
            codigobarra = produto.codigobarra,
            qtde        = 1.0,
            cddeposito  = cddeposito,
            operador    = session.getOperador(),
            deviceId    = session.getDeviceId(),
            qtdeSistema = qtdeSistema,
            scanId      = scanId,
        ))

        // 2. Quantidade acumulada calculada localmente
        val novaQtde = db.bipag.getQtdeAcumulada(produto.cdproduto, sessionId)

        totalBipagens++
        atualizarMiniLista(produto.cdproduto, produto.produto, novaQtde)
        mostrarUltimoBipado(produto.produto, novaQtde)

        // 3. Sincronização imediata se online
        if (ServerMonitor.isOnline.value) {
            try {
                val api = RetrofitClient.build(session)
                val resp = api.registrarBipagem(BipagemRequest(
                    cdproduto  = produto.cdproduto,
                    cddeposito = cddeposito,
                    qtde       = 1.0,
                    operador   = session.getOperador(),
                    deviceId   = session.getDeviceId(),
                    sessionId  = sessionId,
                    scanId     = scanId,
                ))
                if (resp.isSuccessful) {
                    db.bipag.marcarSincronizado(rowId)
                    val alerta = resp.body()?.alerta
                    if (!alerta.isNullOrBlank()) mostrarAlertaQuantidade(produto.produto, alerta)
                } else {
                    val detail = try {
                        org.json.JSONObject(resp.errorBody()?.string() ?: "").getString("detail")
                    } catch (_: Exception) { "HTTP ${resp.code()}" }
                    mostrarErro("Bipagem não salva no servidor: $detail")
                }
            } catch (_: Exception) {
                // UX-2: atualiza status de conexão imediatamente sem aguardar o ciclo de 30s
                ServerMonitor.forcePing(session, lifecycleScope)
            }
        }

        atualizarIndicadorConexao(ServerMonitor.isOnline.value)
        resetarEstado()
    }

    private fun mostrarAlertaQuantidade(nomeProduto: String, alerta: String) {
        AlertDialog.Builder(this)
            .setTitle("Quantidade suspeita")
            .setMessage("$nomeProduto\n\n$alerta")
            .setPositiveButton("Entendi", null)
            .show()
    }

    private fun mostrarUltimoBipado(nome: String, qtd: Double) {
        binding.lastScanPanel.visibility = View.VISIBLE
        binding.tvLastScanNome.text = "✓ $nome"
        binding.tvLastScanQtd.text = "Total neste produto: ${"%.0f".format(qtd)} un."
        binding.tvScanCounter.text = "$totalBipagens un. contadas"
        binding.tvStatus.visibility = View.GONE
        if (binding.switchMultiplo.isChecked && scanMode == ScanMode.CAMERA) {
            lifecycleScope.launch {
                delay(800)
                if (!processando) runOnUiThread { iniciarScan() }
            }
        }
    }

    private fun mostrarErro(msg: String) {
        binding.tvStatus.text = "⚠ $msg"
        binding.tvStatus.visibility = View.VISIBLE
    }

    private fun atualizarMiniLista(cdproduto: Int, nome: String, qtde: Double) {
        val idx = scannedItems.indexOfFirst { it.cdproduto == cdproduto }
        if (idx >= 0) {
            val item = scannedItems.removeAt(idx)
            item.qtde = qtde
            scannedItems.add(0, item)
        } else {
            scannedItems.add(0, ScannedItem(cdproduto, nome, qtde))
            if (scannedItems.size > 5) scannedItems.removeAt(scannedItems.size - 1)
        }
        scannedAdapter.notifyDataSetChanged()
        binding.rvScanned.visibility = View.VISIBLE
    }

    private fun editarQuantidade(item: ScannedItem) {
        val input = EditText(this).apply {
            hint = "Nova quantidade"
            inputType = android.text.InputType.TYPE_CLASS_NUMBER or android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL
            setText("%.2f".format(item.qtde))
        }
        AlertDialog.Builder(this)
            .setTitle(item.nome)
            .setMessage("Quantidade atual: ${"%.2f".format(item.qtde)}")
            .setView(input)
            .setPositiveButton("Salvar") { _, _ ->
                val novaQtde = input.text.toString().toDoubleOrNull() ?: return@setPositiveButton
                val sid = session.getSessionId() ?: return@setPositiveButton
                lifecycleScope.launch {
                    if (ServerMonitor.isOnline.value) {
                        try {
                            val api = RetrofitClient.build(session)
                            val resp = api.editarBipagem(item.cdproduto, EditarBipagemRequest(
                                qtde       = novaQtde,
                                cddeposito = session.getCdDeposito(),
                                motivo     = "Edição manual no scanner",
                                deviceId   = session.getDeviceId(),
                                sessionId  = sid,
                            ))
                            if (resp.isSuccessful) {
                                item.qtde = novaQtde
                                scannedAdapter.notifyDataSetChanged()
                                mostrarUltimoBipado(item.nome, novaQtde)
                                SyncManager.mutex.withLock {
                                    withContext(Dispatchers.IO) {
                                        db.bipag.atualizarQtdeProduto(item.cdproduto, sid, novaQtde)
                                    }
                                }
                            } else {
                                val detail = try {
                                    org.json.JSONObject(resp.errorBody()?.string() ?: "").getString("detail")
                                } catch (_: Exception) { "HTTP ${resp.code()}" }
                                if (resp.code() == 404) {
                                    val pendentes = withContext(Dispatchers.IO) { db.bipag.countPendentes(sid) }
                                    if (pendentes > 0)
                                        mostrarErro("Itens pendentes de sync. Aguarde e tente novamente.")
                                    else
                                        mostrarErro("Erro ao atualizar: $detail")
                                } else {
                                    mostrarErro("Erro ao atualizar: $detail")
                                }
                            }
                        } catch (e: Exception) {
                            mostrarErro("Erro: ${e.message}")
                        }
                    } else {
                        // Offline: salva delta no Room; o lote vai corrigir o servidor ao reconectar
                        SyncManager.mutex.withLock {
                            withContext(Dispatchers.IO) {
                                db.bipag.atualizarQtdeProduto(item.cdproduto, sid, novaQtde, offline = true)
                            }
                        }
                        item.qtde = novaQtde
                        scannedAdapter.notifyDataSetChanged()
                        mostrarUltimoBipado(item.nome, novaQtde)
                        Toast.makeText(this@ScannerActivity, "Salvo offline — será sincronizado ao reconectar", Toast.LENGTH_SHORT).show()
                    }
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun resetarEstado() {
        lifecycleScope.launch {
            if (scanMode == ScanMode.CAMERA) delay(200)
            processando = false
            runOnUiThread { resetarBotaoEscanear() }
        }
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(br.com.inventario.R.menu.menu_scanner, menu)
        return true
    }

    override fun onPrepareOptionsMenu(menu: Menu): Boolean {
        val flashItem = menu.findItem(br.com.inventario.R.id.action_flash)
        val flashVisivel = scanMode == ScanMode.CAMERA
        flashItem?.isVisible = flashVisivel
        flashItem?.icon?.setTint(if (flashLigado) Color.parseColor("#FFD700") else Color.WHITE)
        // Ajusta margem do botão: 2 ícones no modo câmera (~104dp), 1 no modo BT (~52dp)
        val endDp = if (flashVisivel) 104 else 52
        val endPx = (endDp * resources.displayMetrics.density).toInt()
        (binding.btnTrocarModo.layoutParams as? androidx.appcompat.widget.Toolbar.LayoutParams)
            ?.marginEnd = endPx
        binding.btnTrocarModo.requestLayout()
        return super.onPrepareOptionsMenu(menu)
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            br.com.inventario.R.id.action_sincronizar -> { sincronizarManual(); true }
            br.com.inventario.R.id.action_flash -> {
                flashLigado = !flashLigado
                camera?.cameraControl?.enableTorch(flashLigado)
                invalidateOptionsMenu()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    private fun sincronizarManual() {
        val sid = session.getSessionId() ?: return
        lifecycleScope.launch {
            Toast.makeText(this@ScannerActivity, "Sincronizando...", Toast.LENGTH_SHORT).show()
            try {
                SyncManager.sincronizarPendentes(db, session)
                val pendentes = db.bipag.countPendentes(sid)
                val msg = if (pendentes == 0) "Tudo sincronizado!" else "$pendentes scan(s) ainda pendentes"
                Toast.makeText(this@ScannerActivity, msg, Toast.LENGTH_SHORT).show()
            } catch (_: Exception) {
                Toast.makeText(this@ScannerActivity, "Sem conexão com o servidor", Toast.LENGTH_SHORT).show()
            }
            atualizarIndicadorConexao(ServerMonitor.isOnline.value)
        }
    }

    override fun onPause() {
        super.onPause()
        if (flashLigado) {
            flashLigado = false
            camera?.cameraControl?.enableTorch(false)
        }
    }

    override fun onResume() {
        super.onResume()
        val sid = session.getSessionId() ?: return

        // UX-1: recalcula totalBipagens a partir do banco ao voltar de outra tela
        lifecycleScope.launch {
            val total = withContext(Dispatchers.IO) {
                db.bipag.getRelatorioOffline(sid, session.getCdDeposito()).sumOf { it.qtdeContada }.toInt()
            }
            totalBipagens = total
            if (total > 0) binding.tvScanCounter.text = "$total un. contadas"
        }

        // UX-3: recarrega mini-lista ao retornar (pode ter sido alterada em RelatorioActivity)
        lifecycleScope.launch {
            val itens = withContext(Dispatchers.IO) {
                db.bipag.getRelatorioOffline(sid, session.getCdDeposito())
            }
            scannedItems.clear()
            itens.take(5).reversed().forEach { item ->
                scannedItems.add(ScannedItem(item.cdproduto, item.produto, item.qtdeContada))
            }
            if (scannedItems.isNotEmpty()) {
                scannedAdapter.notifyDataSetChanged()
                binding.rvScanned.visibility = View.VISIBLE
            } else {
                binding.rvScanned.visibility = View.GONE
            }
        }
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 100 && grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
            iniciarCamera()
        } else {
            Toast.makeText(this, "Permissão de câmera necessária", Toast.LENGTH_LONG).show()
            aplicarModo(ScanMode.BLUETOOTH)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
    }
}
