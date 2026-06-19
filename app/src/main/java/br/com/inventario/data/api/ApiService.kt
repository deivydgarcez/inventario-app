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

    @GET("inventario/resumo/{cddeposito}")
    suspend fun resumoContagem(@Path("cddeposito") cddeposito: Int): Response<ResumoContagem>

    @POST("inventario/consolidar")
    suspend fun consolidar(@Body body: ConsolidarRequest): Response<ConsolidarResponse>

    @DELETE("inventario/bipagem/{cdproduto}")
    suspend fun removerBipagem(
        @Path("cdproduto") cdproduto: Int,
        @Query("cddeposito") cddeposito: Int,
        @Query("motivo") motivo: String? = null,
        @Query("device_id") deviceId: String? = null,
    ): Response<Map<String, String>>

    @PUT("inventario/bipagem/{cdproduto}")
    suspend fun editarBipagem(
        @Path("cdproduto") cdproduto: Int,
        @Body body: EditarBipagemRequest,
    ): Response<Map<String, String>>

    @GET("inventario/historico/{cddeposito}")
    suspend fun historico(@Path("cddeposito") cddeposito: Int): Response<List<ItemHistorico>>

    @GET("inventario/log/{cddeposito}")
    suspend fun logAuditoria(@Path("cddeposito") cddeposito: Int): Response<List<LogAuditoria>>

    @GET("operadores")
    suspend fun listarOperadores(): Response<List<Operador>>

    @POST("operadores")
    suspend fun criarOperador(@Body body: OperadorRequest): Response<Operador>

    @PUT("operadores/{id}/toggle")
    suspend fun toggleOperador(@Path("id") id: Int): Response<Operador>

    @GET("auth/usuarios")
    suspend fun listarUsuariosMobile(): Response<List<UsuarioMobile>>

    @PUT("auth/usuarios/{id}/senha-mobile")
    suspend fun definirSenhaMobile(
        @Path("id") id: Int,
        @Body body: SenhaMobileRequest,
    ): Response<Map<String, String>>

    @PUT("auth/usuarios/{id}/toggle-admin")
    suspend fun toggleAdminMobile(@Path("id") id: Int): Response<Map<String, Any>>
}
