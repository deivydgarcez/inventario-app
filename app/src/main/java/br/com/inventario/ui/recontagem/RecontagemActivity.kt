package br.com.inventario.ui.recontagem

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.KeyEvent
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import br.com.inventario.ui.base.TimeoutActivity
import androidx.camera.core.*
import androidx.camera.core.Camera
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import br.com.inventario.R
import br.com.inventario.data.api.RetrofitClient
import br.com.inventario.data.db.InvecDatabase
import br.com.inventario.data.model.EditarBipagemRequest
import br.com.inventario.data.model.ItemRelatorio
import br.com.inventario.databinding.ActivityRecontagemBinding
import br.com.inventario.databinding.ItemRecontagemBinding
import br.com.inventario.util.ServerMonitor
import br.com.inventario.util.SessionManager
import com.google.android.material.button.MaterialButton
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import kotlin.math.abs

class RecontagemActivity : TimeoutActivity() {

    private enum class ScanMode { CAMERA, BLUETOOTH }

    private lateinit var binding: ActivityRecontagemBinding
    private lateinit var session: SessionManager
    private lateinit var db: InvecDatabase
    private var scanMode = ScanMode.BLUETOOTH

    private lateinit var cameraExecutor: ExecutorService
    private var cameraProvider: ProcessCameraProvider? = null
    private var camera: Camera? = null
    private var flashLigado = false

    private val btBuffer = StringBuilder()
    private var btLastKeyTime = 0L
    private val BT_TIMEOUT_MS = 150L

    @Volatile private var processando = false
    @Volatile private var aguardandoScan = false

    data class ItemRecontagem(
        val item: ItemRelatorio,
        var qtde2: Double = 0.0,
    )

    private val itens = mutableListOf<ItemRecontagem>()
    private val barcodeMap = mutableMapOf<String, Int>()
    private val cdprodutoMap = mutableMapOf<Int, Int>()
    private lateinit var adapter: RecontagemAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityRecontagemBinding.inflate(layoutInflater)
        setContentView(binding.root)

        session = SessionManager(this)
        db = InvecDatabase.getInstance(this)
        cameraExecutor = Executors.newSingleThreadExecutor()

        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "Recontagem: ${session.getNomeDeposito()}"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        adapter = RecontagemAdapter(itens) { idx -> decrementarItem(idx) }
        binding.recycler.layoutManager = LinearLayoutManager(this)
        binding.recycler.adapter = adapter

        binding.btnModo.setOnClickListener { mostrarSeletorModo() }
        binding.btnFinalizar.setOnClickListener { finalizarRecontagem() }
        binding.btnEscanear.setOnClickListener { iniciarScan() }
        binding.btnDigitarCodigo.setOnClickListener { digitarManualmente() }
        binding.switchMultiplo.setOnCheckedChangeListener { _, checked ->
            if (checked && !aguardandoScan && !processando && scanMode == ScanMode.CAMERA) {
                iniciarScan()
            }
        }

        val modoSalvo = session.getScanMode()
        aplicarModo(if (modoSalvo == "CAMERA") ScanMode.CAMERA else ScanMode.BLUETOOTH)

        carregarItens()
    }

    private fun mostrarSeletorModo() {
        AlertDialog.Builder(this)
            .setTitle("Modo de leitura")
            .setItems(arrayOf("Câmera do celular", "Leitor Bluetooth")) { _, which ->
                aplicarModo(if (which == 0) ScanMode.CAMERA else ScanMode.BLUETOOTH)
            }
            .setCancelable(true)
            .show()
    }

    private fun aplicarModo(modo: ScanMode) {
        scanMode = modo
        session.saveScanMode(modo.name)

        if (modo == ScanMode.CAMERA) {
            binding.btnModo.text = "Câmera"
            binding.cameraContainer.visibility = View.VISIBLE
            binding.btnEscanear.visibility = View.VISIBLE
            binding.switchRow.visibility = View.VISIBLE
            binding.btnFlash.visibility = View.VISIBLE
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED
            ) {
                iniciarCamera()
            } else {
                ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CAMERA), 101)
            }
        } else {
            camera?.cameraControl?.enableTorch(false)
            flashLigado = false
            aguardandoScan = false
            cameraProvider?.unbindAll()
            camera = null
            binding.cameraContainer.visibility = View.GONE
            binding.btnEscanear.visibility = View.GONE
            binding.switchRow.visibility = View.GONE
            binding.btnFlash.visibility = View.GONE
            binding.btnModo.text = "BT"
            btBuffer.clear()
            resetarBotaoEscanear()
        }
    }

    private fun iniciarScan() {
        if (processando) return
        aguardandoScan = true
        binding.btnEscanear.isEnabled = false
        binding.btnEscanear.text = "Aguardando..."
        binding.tvStatus.text = "Aponte a câmera para o código de barras"

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
        if (!processando) atualizarStatus()
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

            binding.btnFlash.setOnClickListener {
                flashLigado = !flashLigado
                camera?.cameraControl?.enableTorch(flashLigado)
                binding.btnFlash.setColorFilter(
                    if (flashLigado) 0xFFFFD700.toInt() else android.graphics.Color.WHITE,
                    android.graphics.PorterDuff.Mode.SRC_IN
                )
            }
        }, ContextCompat.getMainExecutor(this))
    }

    override fun onPause() {
        super.onPause()
        camera?.cameraControl?.enableTorch(false)
        flashLigado = false
        binding.btnFlash.setColorFilter(android.graphics.Color.WHITE, android.graphics.PorterDuff.Mode.SRC_IN)
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
                        binding.tvStatus.text = "Buscando: $codigo..."
                        buscarERegistrar(codigo)
                    }
                }
            }
            .addOnCompleteListener { imageProxy.close() }
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
                    binding.tvStatus.text = "Buscando: $codigo..."
                    buscarERegistrar(codigo)
                } else if (codigo.isNotEmpty() && codigo.length < 3) {
                    Toast.makeText(this, "Código muito curto", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun carregarItens() {
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                var carregouOnline = false
                var erroHttp = false
                try {
                    val api = RetrofitClient.build(session)
                    val resp = api.relatorio(session.getCdDeposito(), session.getSessionId())
                    if (resp.isSuccessful) {
                        popularItens(resp.body() ?: emptyList())
                        carregouOnline = true
                    } else {
                        // Servidor respondeu mas com erro HTTP — não é "offline", é erro de servidor
                        erroHttp = true
                    }
                } catch (_: Exception) {}

                if (!carregouOnline) {
                    if (erroHttp) {
                        Toast.makeText(this@RecontagemActivity, "Erro ao carregar dados do servidor. Verifique e tente novamente.", Toast.LENGTH_LONG).show()
                    } else {
                        val sid = session.getSessionId() ?: ""
                        val lista = withContext(kotlinx.coroutines.Dispatchers.IO) {
                            db.bipag.getRelatorioOffline(sid, session.getCdDeposito())
                        }.map { local ->
                            ItemRelatorio(
                                cdproduto    = local.cdproduto,
                                produto      = local.produto,
                                codigobarra  = local.codigobarra,
                                qtde_sistema = local.qtdeSistema,
                                qtde_contada = local.qtdeContada,
                                diferenca    = local.diferenca,
                                operador     = local.operador,
                            )
                        }
                        popularItens(lista)
                        if (lista.isEmpty()) {
                            Toast.makeText(this@RecontagemActivity, "Sem conexão e sem dados locais", Toast.LENGTH_SHORT).show()
                        } else {
                            Toast.makeText(this@RecontagemActivity, "Offline — ${lista.size} itens do cache local", Toast.LENGTH_SHORT).show()
                        }
                    }
                }
            } catch (_: CancellationException) {
            } catch (e: Exception) {
                Toast.makeText(this@RecontagemActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.visibility = View.GONE
            }
        }
    }

    private fun popularItens(lista: List<ItemRelatorio>) {
        itens.clear()
        barcodeMap.clear()
        cdprodutoMap.clear()
        lista.forEachIndexed { idx, item ->
            itens.add(ItemRecontagem(item))
            item.codigobarra?.let { barcodeMap[it] = idx }
            cdprodutoMap[item.cdproduto] = idx
        }
        adapter.notifyDataSetChanged()
        atualizarStatus()

        // BUG-6: carrega barcodes secundários do catálogo local (um produto pode ter vários)
        val cddeposito = session.getCdDeposito()
        val cdprodutos = lista.map { it.cdproduto }
        lifecycleScope.launch {
            val extras = withContext(kotlinx.coroutines.Dispatchers.IO) {
                db.catalogo.getAllBarcodesForCdprodutos(cdprodutos, cddeposito)
            }
            extras.forEach { (barcode, cdproduto) ->
                if (!barcodeMap.containsKey(barcode)) {
                    val idx = cdprodutoMap[cdproduto]
                    if (idx != null) barcodeMap[barcode] = idx
                }
            }
        }
    }

    private fun atualizarStatus() {
        val escaneados = itens.count { it.qtde2 > 0 }
        val divergencias = itens.count { it.qtde2 > 0 && abs(it.qtde2 - (it.item.qtde_contada ?: 0.0)) > 0.001 }
        binding.tvStatus.text = "$escaneados de ${itens.size} itens · $divergencias divergências"
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
                        binding.tvStatus.text = "Buscando: $codigo..."
                        buscarERegistrar(codigo)
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

    private fun buscarERegistrar(codigo: String) {
        lifecycleScope.launch {
            try {
                val idx = barcodeMap[codigo]
                if (idx != null) {
                    incrementarItem(idx)
                } else {
                    var encontrado = false
                    // Tenta API primeiro
                    try {
                        val api = RetrofitClient.build(session)
                        val resp = api.buscarPorBarcode(codigo, session.getCdDeposito())
                        if (resp.isSuccessful) {
                            val produto = resp.body()
                            if (produto != null) {
                                val idx2 = cdprodutoMap[produto.cdproduto]
                                if (idx2 != null) incrementarItem(idx2)
                                else Toast.makeText(this@RecontagemActivity, "Produto não está na contagem: ${produto.produto}", Toast.LENGTH_SHORT).show()
                                encontrado = true
                            }
                        }
                    } catch (_: Exception) {}

                    // Fallback: catálogo offline
                    if (!encontrado) {
                        val cached = db.catalogo.getByBarcode(codigo, session.getCdDeposito())
                        if (cached != null) {
                            val idx2 = cdprodutoMap[cached.cdproduto]
                            if (idx2 != null) incrementarItem(idx2)
                            else Toast.makeText(this@RecontagemActivity, "Produto não está na contagem: ${cached.produto}", Toast.LENGTH_SHORT).show()
                        } else {
                            val sufixo = if (!ServerMonitor.isOnline.value) " (sem conexão)" else ""
                            Toast.makeText(this@RecontagemActivity, "Produto não encontrado: $codigo$sufixo", Toast.LENGTH_SHORT).show()
                        }
                    }
                }
            } catch (_: CancellationException) {
            } catch (e: Exception) {
                Toast.makeText(this@RecontagemActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                if (scanMode == ScanMode.CAMERA) delay(200)
                processando = false
                runOnUiThread {
                    resetarBotaoEscanear()
                    if (binding.switchMultiplo.isChecked && scanMode == ScanMode.CAMERA) {
                        lifecycleScope.launch {
                            delay(600)
                            if (!processando) runOnUiThread { iniciarScan() }
                        }
                    }
                }
            }
        }
    }

    private fun incrementarItem(idx: Int) {
        itens[idx].qtde2 += 1.0
        adapter.notifyItemChanged(idx)
        val item = itens[idx]
        val dif = item.qtde2 - (item.item.qtde_contada ?: 0.0)
        // Não exibe o valor da 1ª contagem para evitar influência intencional
        val status = if (abs(dif) > 0.001) "  ⚠ Divergência detectada" else "  ✓ Confere"
        binding.lastScanPanel.visibility = View.VISIBLE
        binding.tvLastScanNome.text = item.item.produto
        binding.tvLastScanInfo.text = "2ª contagem: ${"%.0f".format(item.qtde2)} un.$status"
        binding.recycler.scrollToPosition(idx)
    }

    private fun decrementarItem(idx: Int) {
        if (itens[idx].qtde2 > 0) {
            itens[idx].qtde2 -= 1.0
            adapter.notifyItemChanged(idx)
            atualizarStatus()
        }
    }

    private fun finalizarRecontagem() {
        val escaneados = itens.count { it.qtde2 > 0 }
        if (escaneados == 0) {
            Toast.makeText(this, "Nenhum item foi recontado ainda", Toast.LENGTH_SHORT).show()
            return
        }

        val divergencias = itens.filter {
            it.qtde2 > 0 && abs(it.qtde2 - (it.item.qtde_contada ?: 0.0)) > 0.001
        }
        val matches = itens.count { it.qtde2 > 0 && abs(it.qtde2 - (it.item.qtde_contada ?: 0.0)) <= 0.001 }

        val msg = buildString {
            append("$matches itens conferidos sem divergência.\n")
            if (divergencias.isNotEmpty()) {
                append("${divergencias.size} itens com divergência:\n\n")
                divergencias.take(5).forEach {
                    // Não exibe valor da 1ª contagem — apenas informa o que foi contado agora
                    append("  ${it.item.produto}: 2ª contagem = ${"%.0f".format(it.qtde2)} un. ✗\n")
                }
                if (divergencias.size > 5) append("  ...e mais ${divergencias.size - 5} itens\n")
            } else {
                append("\nTodas as contagens conferem! ✓")
            }
        }

        val view = LayoutInflater.from(this).inflate(R.layout.dialog_resultado_recontagem, null)
        view.findViewById<android.widget.TextView>(R.id.tvMensagemResultado).text = msg

        var dialog: AlertDialog? = null
        val online = ServerMonitor.isOnline.value

        if (divergencias.isNotEmpty()) {
            // Aplicar 2ª contagem e já consolidar — ação principal
            view.findViewById<MaterialButton>(R.id.btnConsolidarAgora).apply {
                visibility = View.VISIBLE
                isEnabled = online
                if (!online) text = "Consolidar (requer conexão)"
                setOnClickListener {
                    dialog?.dismiss()
                    aplicarRecontagemEConsolidar(divergencias)
                }
            }
            // Aplicar 2ª contagem e voltar ao relatório
            view.findViewById<MaterialButton>(R.id.btnAplicar2a).apply {
                visibility = View.VISIBLE
                isEnabled = online
                if (!online) text = "Aplicar 2ª contagem (requer conexão)"
                setOnClickListener { aplicarRecontagem(divergencias); dialog?.dismiss() }
            }
            view.findViewById<MaterialButton>(R.id.btnManter1a).apply {
                visibility = View.VISIBLE
                setOnClickListener {
                    // Não bloqueia mais — volta ao relatório onde supervisor pode autorizar
                    dialog?.dismiss()
                    finish()
                }
            }
        } else {
            session.setConsolidarBloqueado(session.getCdDeposito(), false)
            // Sem divergências: consolidar direto é a ação principal
            view.findViewById<MaterialButton>(R.id.btnConsolidarAgora).apply {
                visibility = View.VISIBLE
                isEnabled = online
                if (!online) text = "Consolidar (requer conexão)"
                setOnClickListener {
                    dialog?.dismiss()
                    finalizarComConsolidar()
                }
            }
            view.findViewById<MaterialButton>(R.id.btnVoltarRelatorio).apply {
                visibility = View.VISIBLE
                setOnClickListener { dialog?.dismiss(); finish() }
            }
        }

        view.findViewById<MaterialButton>(R.id.btnContinuarRecontando).setOnClickListener {
            dialog?.dismiss()
        }

        dialog = MaterialAlertDialogBuilder(this)
            .setView(view)
            .setCancelable(true)
            .create()
        dialog.show()
    }

    private fun finalizarComConsolidar() {
        setResult(RESULT_OK, Intent().putExtra("consolidar_direto", true))
        finish()
    }

    private fun aplicarRecontagemEConsolidar(divergencias: List<ItemRecontagem>) {
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                var falhou = false
                divergencias.forEach { item ->
                    val resp = api.editarBipagem(
                        item.item.cdproduto,
                        EditarBipagemRequest(item.qtde2, session.getCdDeposito(), motivo = "Recontagem aplicada", sessionId = session.getSessionId()),
                    )
                    if (!resp.isSuccessful) falhou = true
                }
                if (falhou) {
                    Toast.makeText(this@RecontagemActivity, "Erro ao salvar alguns itens. Verifique e tente novamente.", Toast.LENGTH_LONG).show()
                } else {
                    session.setConsolidarBloqueado(session.getCdDeposito(), false)
                    finalizarComConsolidar()
                }
            } catch (e: Exception) {
                Toast.makeText(this@RecontagemActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.visibility = View.GONE
            }
        }
    }

    private fun aplicarRecontagem(divergencias: List<ItemRecontagem>) {
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                var atualizados = 0
                divergencias.forEach { item ->
                    val resp = api.editarBipagem(
                        item.item.cdproduto,
                        EditarBipagemRequest(item.qtde2, session.getCdDeposito(), motivo = "Recontagem aplicada", sessionId = session.getSessionId()),
                    )
                    if (resp.isSuccessful) atualizados++
                }
                if (atualizados < divergencias.size) {
                    Toast.makeText(
                        this@RecontagemActivity,
                        "Atenção: $atualizados de ${divergencias.size} itens atualizados. Tente novamente.",
                        Toast.LENGTH_LONG
                    ).show()
                } else {
                    session.setConsolidarBloqueado(session.getCdDeposito(), false)
                    Toast.makeText(this@RecontagemActivity, "$atualizados itens atualizados", Toast.LENGTH_LONG).show()
                    finish()
                }
            } catch (e: Exception) {
                Toast.makeText(this@RecontagemActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.visibility = View.GONE
            }
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 101 && grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
            iniciarCamera()
        } else {
            Toast.makeText(this, "Permissão de câmera necessária", Toast.LENGTH_LONG).show()
            aplicarModo(ScanMode.BLUETOOTH)
        }
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
    }

    inner class RecontagemAdapter(
        private val lista: List<ItemRecontagem>,
        private val onDecrement: (Int) -> Unit,
    ) : RecyclerView.Adapter<RecontagemAdapter.VH>() {

        inner class VH(val b: ItemRecontagemBinding) : RecyclerView.ViewHolder(b.root)

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
            VH(ItemRecontagemBinding.inflate(LayoutInflater.from(parent.context), parent, false))

        override fun getItemCount() = lista.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val rec = lista[position]
            with(holder.b) {
                tvProduto.text = rec.item.produto
                // 1ª contagem oculta durante todo o processo de recontagem
                tvContagem1.visibility = View.GONE
                if (rec.qtde2 > 0) {
                    tvContagem2.text = "2ª: ${"%.0f".format(rec.qtde2)}"
                    val dif = rec.qtde2 - (rec.item.qtde_contada ?: 0.0)
                    // Mostra apenas se bate ou não, sem revelar o valor da 1ª contagem
                    tvDiferenca.text = if (abs(dif) > 0.001) "≠" else "="
                    val ok = abs(dif) <= 0.001
                    tvStatus.text = if (ok) "✓" else "✗"
                    tvStatus.setTextColor(if (ok) 0xFF2E7D32.toInt() else 0xFFC62828.toInt())
                    tvDiferenca.setTextColor(if (ok) 0xFF2E7D32.toInt() else 0xFFC62828.toInt())
                    btnMinus.visibility = View.VISIBLE
                    btnMinus.setOnClickListener { onDecrement(holder.adapterPosition) }
                } else {
                    tvContagem2.text = "2ª: ..."
                    tvDiferenca.text = "·"
                    tvStatus.text = "·"
                    tvStatus.setTextColor(0xFF9E9E9E.toInt())
                    tvDiferenca.setTextColor(0xFF9E9E9E.toInt())
                    btnMinus.visibility = View.GONE
                }
            }
        }
    }
}
