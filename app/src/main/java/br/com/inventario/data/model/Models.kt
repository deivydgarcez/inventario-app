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
    @SerializedName("recontagem_confirmada") val recontagemConfirmada: Boolean = false,
    val idempresa: Int = 1,
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
