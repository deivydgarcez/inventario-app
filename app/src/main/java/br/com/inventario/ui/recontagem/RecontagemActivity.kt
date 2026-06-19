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
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import br.com.inventario.R
import br.com.inventario.data.api.RetrofitClient
import br.com.inventario.data.model.EditarBipagemRequest
import br.com.inventario.data.model.ItemRelatorio
import br.com.inventario.databinding.ActivityRecontagemBinding
import br.com.inventario.databinding.ItemRecontagemBinding
import br.com.inventario.util.SessionManager
import com.google.android.material.button.MaterialButton
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import kotlin.math.abs

class RecontagemActivity : TimeoutActivity() {

    private enum class ScanMode { CAMERA, BLUETOOTH }

    private lateinit var binding: ActivityRecontagemBinding
    private lateinit var session: SessionManager
    private var scanMode = ScanMode.BLUETOOTH

    private lateinit var cameraExecutor: ExecutorService
    private var cameraProvider: ProcessCameraProvider? = null

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
        cameraExecutor = Executors.newSingleThreadExecutor()

        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "Recontagem: ${session.getNomeDeposito()}"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        adapter = RecontagemAdapter(itens)
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
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED
            ) {
                iniciarCamera()
            } else {
                ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CAMERA), 101)
            }
        } else {
            aguardandoScan = false
            cameraProvider?.unbindAll()
            binding.cameraContainer.visibility = View.GONE
            binding.btnEscanear.visibility = View.GONE
            binding.switchRow.visibility = View.GONE
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
                val api = RetrofitClient.build(session)
                val resp = api.relatorio(session.getCdDeposito())
                if (resp.isSuccessful) {
                    val lista = resp.body() ?: emptyList()
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
                } else {
                    Toast.makeText(this@RecontagemActivity, "Erro ao carregar itens", Toast.LENGTH_SHORT).show()
                }
            } catch (_: CancellationException) {
            } catch (e: Exception) {
                Toast.makeText(this@RecontagemActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.visibility = View.GONE
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
                    val api = RetrofitClient.build(session)
                    val resp = api.buscarPorBarcode(codigo, session.getCdDeposito())
                    if (resp.isSuccessful) {
                        val produto = resp.body()!!
                        val idx2 = cdprodutoMap[produto.cdproduto]
                        if (idx2 != null) {
                            incrementarItem(idx2)
                        } else {
                            Toast.makeText(this@RecontagemActivity, "Produto não está na contagem: ${produto.produto}", Toast.LENGTH_SHORT).show()
                        }
                    } else {
                        Toast.makeText(this@RecontagemActivity, "Produto não encontrado: $codigo", Toast.LENGTH_SHORT).show()
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
        val difStr = if (abs(dif) > 0.001) "  ⚠ Dif: ${"%.0f".format(dif)}" else "  ✓ Confere"
        binding.lastScanPanel.visibility = View.VISIBLE
        binding.tvLastScanNome.text = item.item.produto
        binding.tvLastScanInfo.text = "2ª contagem: ${"%.0f".format(item.qtde2)} un.$difStr"
        binding.recycler.scrollToPosition(idx)
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
                    val dif = it.qtde2 - (it.item.qtde_contada ?: 0.0)
                    append("  ${it.item.produto}: 1a=${"%.0f".format(it.item.qtde_contada)}, 2a=${"%.0f".format(it.qtde2)} (${if (dif > 0) "+" else ""}${"%.0f".format(dif)})\n")
                }
                if (divergencias.size > 5) append("  ...e mais ${divergencias.size - 5} itens\n")
            } else {
                append("\nTodas as contagens conferem!")
            }
        }

        val view = LayoutInflater.from(this).inflate(R.layout.dialog_resultado_recontagem, null)
        view.findViewById<android.widget.TextView>(R.id.tvMensagemResultado).text = msg

        var dialog: AlertDialog? = null

        if (divergencias.isNotEmpty()) {
            // Aplicar 2ª contagem e já consolidar — ação principal
            view.findViewById<MaterialButton>(R.id.btnConsolidarAgora).apply {
                visibility = View.VISIBLE
                setOnClickListener {
                    dialog?.dismiss()
                    aplicarRecontagemEConsolidar(divergencias)
                }
            }
            // Aplicar 2ª contagem e voltar ao relatório
            view.findViewById<MaterialButton>(R.id.btnAplicar2a).apply {
                visibility = View.VISIBLE
                setOnClickListener { aplicarRecontagem(divergencias); dialog?.dismiss() }
            }
            view.findViewById<MaterialButton>(R.id.btnManter1a).apply {
                visibility = View.VISIBLE
                setOnClickListener {
                    session.setConsolidarBloqueado(session.getCdDeposito(), true)
                    dialog?.dismiss()
                    finish()
                }
            }
        } else {
            session.setConsolidarBloqueado(session.getCdDeposito(), false)
            // Sem divergências: consolidar direto é a ação principal
            view.findViewById<MaterialButton>(R.id.btnConsolidarAgora).apply {
                visibility = View.VISIBLE
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
                        EditarBipagemRequest(item.qtde2, session.getCdDeposito(), motivo = "Recontagem aplicada"),
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
                        EditarBipagemRequest(item.qtde2, session.getCdDeposito(), motivo = "Recontagem aplicada"),
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

    inner class RecontagemAdapter(private val lista: List<ItemRecontagem>) :
        RecyclerView.Adapter<RecontagemAdapter.VH>() {

        inner class VH(val b: ItemRecontagemBinding) : RecyclerView.ViewHolder(b.root)

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
            VH(ItemRecontagemBinding.inflate(LayoutInflater.from(parent.context), parent, false))

        override fun getItemCount() = lista.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val rec = lista[position]
            with(holder.b) {
                tvProduto.text = rec.item.produto
                tvContagem1.text = "1ª: ${"%.2f".format(rec.item.qtde_contada ?: 0.0)}"
                if (rec.qtde2 > 0) {
                    tvContagem2.text = "2ª: ${"%.2f".format(rec.qtde2)}"
                    val dif = rec.qtde2 - (rec.item.qtde_contada ?: 0.0)
                    tvDiferenca.text = if (abs(dif) > 0.001) "${"%.2f".format(dif)}" else "="
                    val ok = abs(dif) <= 0.001
                    tvStatus.text = if (ok) "✓" else "✗"
                    tvStatus.setTextColor(if (ok) 0xFF2E7D32.toInt() else 0xFFC62828.toInt())
                    tvDiferenca.setTextColor(if (ok) 0xFF2E7D32.toInt() else 0xFFC62828.toInt())
                } else {
                    tvContagem2.text = "2ª: ..."
                    tvDiferenca.text = "..."
                    tvStatus.text = "·"
                    tvStatus.setTextColor(0xFF9E9E9E.toInt())
                    tvDiferenca.setTextColor(0xFF9E9E9E.toInt())
                }
            }
        }
    }
}
