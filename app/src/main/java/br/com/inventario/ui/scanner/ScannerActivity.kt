package br.com.inventario.ui.scanner

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.KeyEvent
import android.view.View
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
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
import br.com.inventario.data.model.BipagemRequest
import br.com.inventario.data.model.EditarBipagemRequest
import br.com.inventario.data.model.Produto
import br.com.inventario.databinding.ActivityScannerBinding
import br.com.inventario.util.SessionManager
import com.google.android.material.snackbar.Snackbar
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import kotlinx.coroutines.launch
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class ScannerActivity : AppCompatActivity() {

    private enum class ScanMode { CAMERA, BLUETOOTH }

    private lateinit var binding: ActivityScannerBinding
    private lateinit var session: SessionManager
    private lateinit var cameraExecutor: ExecutorService
    private var cameraProvider: ProcessCameraProvider? = null
    private var processando = false
    private var scanMode = ScanMode.CAMERA

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

        scannedAdapter = ScannedItemsAdapter(scannedItems) { item -> editarQuantidade(item) }
        binding.rvScanned.apply {
            layoutManager = LinearLayoutManager(this@ScannerActivity)
            adapter = scannedAdapter
        }

        binding.btnTrocarModo.setOnClickListener { mostrarSeletorModo() }
        mostrarSeletorModo()
    }

    private fun mostrarSeletorModo() {
        AlertDialog.Builder(this)
            .setTitle("Modo de leitura")
            .setItems(arrayOf("📷  Câmera do celular", "📡  Leitor Bluetooth")) { _, which ->
                if (which == 0) aplicarModo(ScanMode.CAMERA)
                else aplicarModo(ScanMode.BLUETOOTH)
            }
            .setCancelable(scanMode != ScanMode.CAMERA || cameraProvider != null)
            .show()
    }

    private fun aplicarModo(modo: ScanMode) {
        scanMode = modo
        if (modo == ScanMode.CAMERA) {
            binding.btModeLayout.visibility = View.GONE
            binding.previewView.visibility = View.VISIBLE
            binding.cameraOverlayTop.visibility = View.VISIBLE
            binding.cameraOverlayBottom.visibility = View.VISIBLE
            binding.scanFrame.visibility = View.VISIBLE
            binding.scanLine.visibility = View.VISIBLE
            binding.tvCameraInstruction.visibility = View.VISIBLE
            binding.btnTrocarModo.text = "Bluetooth"

            if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED
            ) {
                iniciarCamera()
            } else {
                ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CAMERA), 100)
            }
        } else {
            cameraProvider?.unbindAll()
            binding.btModeLayout.visibility = View.VISIBLE
            binding.previewView.visibility = View.GONE
            binding.cameraOverlayTop.visibility = View.GONE
            binding.cameraOverlayBottom.visibility = View.GONE
            binding.scanFrame.visibility = View.GONE
            binding.scanLine.visibility = View.GONE
            binding.tvCameraInstruction.visibility = View.GONE
            binding.btnTrocarModo.text = "Câmera"
            btBuffer.clear()
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
        if (processando || scanMode != ScanMode.CAMERA) { imageProxy.close(); return }

        val mediaImage = imageProxy.image ?: run { imageProxy.close(); return }
        val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)

        BarcodeScanning.getClient()
            .process(image)
            .addOnSuccessListener { barcodes ->
                val codigo = barcodes.firstOrNull { it.rawValue != null }?.rawValue
                if (codigo != null) {
                    processando = true
                    runOnUiThread { buscarProduto(codigo) }
                }
            }
            .addOnCompleteListener { imageProxy.close() }
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
                        binding.tvStatus.text = "Buscando: $codigo…"
                        binding.tvStatus.visibility = View.VISIBLE
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
        if (scanMode == ScanMode.CAMERA) {
            binding.tvStatus.text = "Buscando…"
            binding.tvStatus.visibility = View.VISIBLE
        }
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val response = api.buscarPorBarcode(codigo, session.getCdDeposito())
                if (response.isSuccessful) {
                    registrarBipagem(response.body()!!)
                } else if (response.code() == 404) {
                    Snackbar.make(binding.root, "Produto não encontrado: $codigo", Snackbar.LENGTH_SHORT).show()
                    resetarEstado()
                } else {
                    Snackbar.make(binding.root, "Erro ao buscar produto", Snackbar.LENGTH_SHORT).show()
                    resetarEstado()
                }
            } catch (e: Exception) {
                Snackbar.make(binding.root, "Erro: ${e.message}", Snackbar.LENGTH_SHORT).show()
                resetarEstado()
            }
        }
    }

    private fun registrarBipagem(produto: Produto) {
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val resp = api.registrarBipagem(BipagemRequest(produto.cdproduto, session.getCdDeposito(), 1.0))
                if (resp.isSuccessful) {
                    val total = resp.body()!!.novaQtde
                    atualizarMiniLista(produto.cdproduto, produto.produto, total)
                    Snackbar.make(binding.root, "${produto.produto} → Total: ${"%.0f".format(total)} un.", Snackbar.LENGTH_SHORT)
                        .setAction("EDITAR") {
                            scannedItems.firstOrNull { it.cdproduto == produto.cdproduto }?.let { editarQuantidade(it) }
                        }
                        .show()
                } else {
                    Snackbar.make(binding.root, "Erro ao registrar bipagem", Snackbar.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Snackbar.make(binding.root, "Erro: ${e.message}", Snackbar.LENGTH_SHORT).show()
            } finally {
                resetarEstado()
            }
        }
    }

    private fun atualizarMiniLista(cdproduto: Int, nome: String, qtde: Double) {
        val idx = scannedItems.indexOfFirst { it.cdproduto == cdproduto }
        if (idx >= 0) {
            val item = scannedItems.removeAt(idx)
            item.qtde = qtde
            scannedItems.add(0, item)
        } else {
            scannedItems.add(0, ScannedItem(cdproduto, nome, qtde))
            if (scannedItems.size > 8) scannedItems.removeAt(scannedItems.size - 1)
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
                        api.editarBipagem(item.cdproduto, EditarBipagemRequest(novaQtde, session.getCdDeposito()))
                        item.qtde = novaQtde
                        scannedAdapter.notifyDataSetChanged()
                        Snackbar.make(binding.root, "Quantidade ajustada: ${"%.2f".format(novaQtde)}", Snackbar.LENGTH_SHORT).show()
                    } catch (e: Exception) {
                        Snackbar.make(binding.root, "Erro: ${e.message}", Snackbar.LENGTH_SHORT).show()
                    }
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun resetarEstado() {
        processando = false
        binding.tvStatus.visibility = View.GONE
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
