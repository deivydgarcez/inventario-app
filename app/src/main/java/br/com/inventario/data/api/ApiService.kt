package br.com.inventario.data.api

import br.com.inventario.data.model.*
import retrofit2.Response
import retrofit2.http.*

interface ApiService {

    @POST("auth/login")
    suspend fun login(@Body body: LoginRequest): Response<TokenResponse>

    @GET("depositos")
    suspend fun listarDepositos(): Response<List<Deposito>>

    @GET("produtos/barcode/{codigo}")
    suspend fun buscarPorBarcode(
        @Path("codigo") codigo: String,
        @Query("cddeposito") cddeposito: Int,
    ): Response<Produto>

    @GET("produtos/busca")
    suspend fun buscarPorDescricao(
        @Query("q") q: String,
        @Query("cddeposito") cddeposito: Int,
    ): Response<List<Produto>>

    @POST("inventario/bipagem")
    suspend fun registrarBipagem(@Body body: BipagemRequest): Response<BipagemResponse>

    @GET("inventario/relatorio/{cddeposito}")
    suspend fun relatorio(@Path("cddeposito") cddeposito: Int): Response<List<ItemRelatorio>>

    @POST("inventario/consolidar")
    suspend fun consolidar(@Body body: Map<String, Int>): Response<Map<String, String>>

    @DELETE("inventario/bipagem/{cdproduto}")
    suspend fun removerBipagem(
        @Path("cdproduto") cdproduto: Int,
        @Query("cddeposito") cddeposito: Int,
    ): Response<Map<String, String>>

    @PUT("inventario/bipagem/{cdproduto}")
    suspend fun editarBipagem(
        @Path("cdproduto") cdproduto: Int,
        @Body body: EditarBipagemRequest,
    ): Response<Map<String, String>>
}
