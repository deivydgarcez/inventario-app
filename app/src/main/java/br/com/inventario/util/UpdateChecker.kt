package br.com.inventario.util

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import androidx.core.content.FileProvider
import br.com.inventario.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.File
import java.util.concurrent.TimeUnit

data class UpdateInfo(
    val versao: String,
    val changelog: String,
    val apkApiUrl: String
)

object UpdateChecker {

    private const val REPO = "deivydgarcez/inventario-app"

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(180, TimeUnit.SECONDS)
        .build()

    suspend fun verificar(): UpdateInfo? = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("https://api.github.com/repos/$REPO/releases/latest")
                .header("Authorization", "Bearer ${BuildConfig.GITHUB_TOKEN}")
                .header("Accept", "application/vnd.github+json")
                .header("X-GitHub-Api-Version", "2022-11-28")
                .build()

            val response = client.newCall(request).execute()
            if (!response.isSuccessful) return@withContext null

            val json = JSONObject(response.body!!.string())
            val tagName = json.optString("tag_name", "")
            val versaoRemota = tagName.removePrefix("v")

            if (versaoRemota.isBlank()) return@withContext null
            if (!isMaisRecente(versaoRemota, BuildConfig.VERSION_NAME)) return@withContext null

            val changelog = json.optString("body", "Melhorias e correções gerais.")

            val assets = json.optJSONArray("assets") ?: return@withContext null
            var apkUrl: String? = null
            for (i in 0 until assets.length()) {
                val asset = assets.getJSONObject(i)
                if (asset.getString("name").endsWith(".apk")) {
                    apkUrl = asset.getString("url")
                    break
                }
            }
            if (apkUrl == null) return@withContext null

            UpdateInfo(versaoRemota, changelog, apkUrl)
        } catch (_: Exception) {
            null
        }
    }

    suspend fun baixar(
        context: Context,
        apkApiUrl: String,
        onProgresso: (Int) -> Unit
    ): File? = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url(apkApiUrl)
                .header("Authorization", "Bearer ${BuildConfig.GITHUB_TOKEN}")
                .header("Accept", "application/octet-stream")
                .build()

            val response = client.newCall(request).execute()
            if (!response.isSuccessful) return@withContext null

            val body = response.body ?: return@withContext null
            val tamanhoTotal = body.contentLength()
            val apkFile = File(context.cacheDir, "invec_update.apk")

            var baixado = 0L
            body.byteStream().use { input ->
                apkFile.outputStream().use { output ->
                    val buffer = ByteArray(8 * 1024)
                    var lidos: Int
                    while (input.read(buffer).also { lidos = it } != -1) {
                        output.write(buffer, 0, lidos)
                        baixado += lidos
                        if (tamanhoTotal > 0) {
                            onProgresso((baixado * 100 / tamanhoTotal).toInt())
                        }
                    }
                }
            }
            apkFile
        } catch (_: Exception) {
            null
        }
    }

    fun instalar(context: Context, apkFile: File) {
        val uri = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            FileProvider.getUriForFile(context, "${context.packageName}.provider", apkFile)
        } else {
            @Suppress("DEPRECATION")
            Uri.fromFile(apkFile)
        }
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
    }

    private fun isMaisRecente(remota: String, atual: String): Boolean {
        val r = remota.split(".").map { it.toIntOrNull() ?: 0 }
        val a = atual.split(".").map { it.toIntOrNull() ?: 0 }
        val len = maxOf(r.size, a.size)
        for (i in 0 until len) {
            val rv = r.getOrElse(i) { 0 }
            val av = a.getOrElse(i) { 0 }
            if (rv > av) return true
            if (rv < av) return false
        }
        return false
    }
}
