package br.com.inventario.data.model

import com.google.gson.annotations.SerializedName

data class LoginRequest(val login: String, val senha: String)

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    val usuario: String,
    val nome: String,
    val role: String = "operador",
    @SerializedName("mobile_admin") val mobileAdmin: Int = 0,
)

data class UsuarioMobile(
    val idusuario: Int,
    val login: String,
    val nomecompleto: String?,
    val idgrupo: Int?,
    val inativo: Int?,
    @SerializedName("tem_mobile") val temMobile: Int,
    @SerializedName("mobile_admin") val mobileAdmin: Int = 0,
)

data class SenhaMobileRequest(val senha: String?)

data class Deposito(val cddeposito: Int, val deposito: String)

data class Produto(
    val cdproduto: Int,
    val produto: String,
    val codigobarra: String?,
    val qtdeatual: Double?,
)

data class BipagemRequest(
    val cdproduto: Int,
    val cddeposito: Int,
    val qtde: Double,
    val operador: String? = null,
    @SerializedName("device_id") val deviceId: String? = null,
    @SerializedName("session_id") val sessionId: String? = null,
    @SerializedName("scan_id") val scanId: String? = null,
)

data class BipagemResponse(
    val cdproduto: Int,
    val cddeposito: Int,
    val qtde: Double,
    @SerializedName("nova_qtde") val novaQtde: Double,
    val mensagem: String,
    val alerta: String? = null,
)

data class EditarBipagemRequest(
    val qtde: Double,
    val cddeposito: Int,
    val motivo: String? = null,
    @SerializedName("device_id") val deviceId: String? = null,
    @SerializedName("session_id") val sessionId: String? = null,
)

data class ItemRelatorio(
    val cdproduto: Int,
    val produto: String,
    val codigobarra: String?,
    val qtde_sistema: Double?,
    val qtde_contada: Double?,
    val diferenca: Double?,
    val operador: String?,
)

data class ConsolidarRequest(
    val cddeposito: Int,
    val operador: String? = null,
    @SerializedName("supervisor_login") val supervisorLogin: String? = null,
    @SerializedName("supervisor_senha") val supervisorSenha: String? = null,
    @SerializedName("supervisor_token") val supervisorToken: String? = null,
    @SerializedName("recontagem_confirmada") val recontagemConfirmada: Boolean = false,
    @SerializedName("session_id") val sessionId: String? = null,
    @SerializedName("justificativa_sem_recontagem") val justificativaSemRecontagem: String? = null,
)

data class SupervisorPreAuthRequest(val login: String, val senha: String)

data class SupervisorPreAuthResponse(
    @SerializedName("supervisor_token") val supervisorToken: String,
    @SerializedName("expira_em_segundos") val expiraEmSegundos: Int,
)

data class ConsolidarResponse(
    val mensagem: String,
    val idinventario: Int,
)

data class ResumoContagem(
    @SerializedName("total_deposito") val totalDeposito: Int,
    val contados: Int,
    @SerializedName("nao_contados") val naoContados: Int,
    @SerializedName("produtos_nao_contados") val produtosNaoContados: List<String> = emptyList(),
)

data class ItemHistorico(
    val cdproduto: Int,
    val produto: String,
    val cddeposito: Int,
    val deposito: String,
    val qtde_contada: Double?,
    val qtde_sistema: Double?,
    val data: String?,
    val operador: String?,
)

data class Operador(val id: Int, val nome: String, val ativo: Int)

data class OperadorRequest(val nome: String)

// ── Sessão offline ────────────────────────────────────────────────────────────

data class IniciarSessaoRequest(
    @SerializedName("session_id") val sessionId: String,
    val cddeposito: Int,
    val operador: String? = null,
)

data class SessaoResponse(
    @SerializedName("session_id") val sessionId: String,
    val cddeposito: Int,
    val operador: String?,
    val status: String,
    val inicio: String?,
)

data class BipagemLoteItem(
    val cdproduto: Int,
    val produto: String,
    val qtde: Double,
    val qtde_sistema: Double,
    val operador: String? = null,
    val device_id: String? = null,
    val timestamp: Long = System.currentTimeMillis(),
    val scan_ids: List<String>? = null,
)

data class LoteBipagemRequest(
    @SerializedName("session_id") val sessionId: String,
    val cddeposito: Int,
    val bipagens: List<BipagemLoteItem>,
    @SerializedName("lote_id") val loteId: String? = null,
)

data class LoteSyncResponse(
    val sincronizados: Int,
    val alertas: List<String> = emptyList(),
)

// ── Catálogo offline ──────────────────────────────────────────────────────────

data class ProdutoCatalogoItem(
    val cdproduto: Int,
    val produto: String,
    val codigobarra: String?,
    val qtdeatual: Double,
)

data class CatalogoResponse(
    val itens: List<ProdutoCatalogoItem>,
    val total: Int,
    val pagina: Int,
    val paginas: Int,
)

data class LogAuditoria(
    val id: Int,
    val tipo: String,
    val cddeposito: Int?,
    val cdproduto: Int?,
    val produto: String?,
    val operador: String?,
    @SerializedName("login_usuario") val loginUsuario: String?,
    @SerializedName("qtde_antes") val qtdeAntes: Double?,
    @SerializedName("qtde_depois") val qtdeDepois: Double?,
    val motivo: String?,
    @SerializedName("device_id") val deviceId: String?,
    @SerializedName("data_hora") val dataHora: String?,
)
