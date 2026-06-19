package br.com.inventario.ui.scanner

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.KeyEvent
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
import br.com.inventario.ui.base.TimeoutActivity
import br.com.inventario.data.model.BipagemRequest
import br.com.inventario.data.model.EditarBipagemRequest
import br.com.inventario.data.model.Produto
import br.com.inventario.databinding.ActivityScannerBinding
import br.com.inventario.util.SessionManager
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class ScannerActivity : TimeoutActivity() {

    private enum class ScanMode { CAMERA, BLUETOOTH }

    private lateinit var binding: ActivityScannerBinding
    private lateinit var session: SessionManager
    private lateinit var cameraExecutor: ExecutorService
    private var cameraProvider: ProcessCameraProvider? = null

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
        cameraExecutor = Executors.newSingleThreadExecutor()

        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = session.getNomeDeposito() ?: "Scanner"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        ViewCompat.setOnApplyWindowInsetsListener(binding.toolbar) { v, insets ->
            val top = insets.getInsets(WindowInsetsCompat.Type.statusBars()).top
            v.setPadding(v.paddingLeft, top, v.paddingRight, v.paddingBottom)
            insets
        }

        // Painel inferior acima da barra de navegação do sistema
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
        binding.tvOperador.setOnClickListener { selecionarOperador() }
        binding.switchMultiplo.setOnCheckedChangeListener { _, checked ->
            if (checked && !aguardandoScan && !processando && scanMode == ScanMode.CAMERA) {
                iniciarScan()
            }
        }

        val modoSalvo = session.getScanMode()
        aplicarModo(if (modoSalvo == "BLUETOOTH") ScanMode.BLUETOOTH else ScanMode.CAMERA)

        atualizarTextoOperador()
    }

    private fun atualizarTextoOperador() {
        val op = session.getOperador()
        val travado = totalBipagens > 0
        binding.tvOperador.text = when {
            op == null && !travado -> "Operador: nenhum  (toque para definir)"
            op == null && travado  -> "Operador: nenhum  (saia para trocar)"
            travado               -> "Operador: $op  [travado - saia para trocar]"
            else                  -> "Operador: $op  (toque para trocar)"
        }
    }

    private fun selecionarOperador() {
        if (totalBipagens > 0) {
            Toast.makeText(this, "Operador travado após início da coleta. Saia e entre novamente para trocar.", Toast.LENGTH_LONG).show()
            return
        }
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val resp = api.listarOperadores()
                if (resp.isSuccessful) {
                    val lista = (resp.body() ?: emptyList()).filter { it.ativo == 1 }
                    val nomes = (listOf("(Sem operador)") + lista.map { it.nome }).toTypedArray()
                    AlertDialog.Builder(this@ScannerActivity)
                        .setTitle("Quem está fazendo a contagem?")
                        .setCancelable(true)
                        .setItems(nomes) { _, idx ->
                            val operador = if (idx == 0) null else lista[idx - 1].nome
                            session.saveOperador(operador)
                            atualizarTextoOperador()
                        }
                        .show()
                }
            } catch (_: Exception) {
                Toast.makeText(this@ScannerActivity, "Não foi possível carregar operadores", Toast.LENGTH_SHORT).show()
            }
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

        // Timeout de 6 segundos se não ler nada
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
            cameraProvider?.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis)
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

    private fun buscarProduto(codigo: String) {
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val response = api.buscarPorBarcode(codigo, session.getCdDeposito())
                if (response.isSuccessful) {
                    registrarBipagem(response.body()!!)
                } else if (response.code() == 404) {
                    mostrarErro("Produto não encontrado: $codigo")
                    resetarEstado()
                } else {
                    mostrarErro("Erro ao buscar produto")
                    resetarEstado()
                }
            } catch (e: Exception) {
                mostrarErro("Sem conexão com o servidor")
                resetarEstado()
            }
        }
    }

    private fun registrarBipagem(produto: Produto) {
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val resp = api.registrarBipagem(
                    BipagemRequest(
                        cdproduto = produto.cdproduto,
                        cddeposito = session.getCdDeposito(),
                        qtde = 1.0,
                        operador = session.getOperador(),
                        deviceId = session.getDeviceId(),
                    )
                )
                if (resp.isSuccessful) {
                    val body = resp.body()!!
                    totalBipagens++
                    atualizarMiniLista(produto.cdproduto, produto.produto, body.novaQtde)
                    mostrarUltimoBipado(produto.produto, body.novaQtde)
                    if (!body.alerta.isNullOrBlank()) {
                        mostrarAlertaQuantidade(produto.produto, body.alerta)
                    }
                } else {
                    mostrarErro("Erro ao registrar bipagem")
                }
            } catch (e: Exception) {
                mostrarErro("Erro: ${e.message}")
            } finally {
                resetarEstado()
            }
        }
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
        binding.tvScanCounter.text = "$totalBipagens bipagens"
        binding.tvStatus.visibility = View.GONE
        atualizarTextoOperador() // trava o campo após o 1º scan
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
                lifecycleScope.launch {
                    try {
                        val api = RetrofitClient.build(session)
                        val resp = api.editarBipagem(item.cdproduto, EditarBipagemRequest(
                            qtde = novaQtde,
                            cddeposito = session.getCdDeposito(),
                            motivo = "Edição manual no scanner",
                            deviceId = session.getDeviceId(),
                        ))
                        if (resp.isSuccessful) {
                            item.qtde = novaQtde
                            scannedAdapter.notifyDataSetChanged()
                            mostrarUltimoBipado(item.nome, novaQtde)
                        } else {
                            mostrarErro("Erro ao atualizar quantidade")
                        }
                    } catch (e: Exception) {
                        mostrarErro("Erro: ${e.message}")
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
