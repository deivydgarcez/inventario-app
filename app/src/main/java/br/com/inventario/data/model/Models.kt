package br.com.inventario.data.model

import com.google.gson.annotations.SerializedName

data class LoginRequest(val login: String, val senha: String)

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    val usuario: String,
    val nome: String,
)

data class Deposito(val cddeposito: Int, val deposito: String)

data class Produto(
    val cdproduto: Int,
    val produto: String,
    val codigobarra: String?,
    val qtdeatual: Double?,
)

data class BipagemRequest(val cdproduto: Int, val cddeposito: Int, val qtde: Double)

data class BipagemResponse(
    val cdproduto: Int,
    val cddeposito: Int,
    val qtde: Double,
    @SerializedName("nova_qtde") val novaQtde: Double,
    val mensagem: String,
)

data class EditarBipagemRequest(val qtde: Double, val cddeposito: Int)

data class ItemRelatorio(
    val cdproduto: Int,
    val produto: String,
    val codigobarra: String?,
    val qtde_sistema: Double?,
    val qtde_contada: Double?,
    val diferenca: Double?,
)
