package br.com.inventario.data.api

import android.content.Intent
import br.com.inventario.ui.login.LoginActivity
import br.com.inventario.util.SessionManager
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {

    private var _api: ApiService? = null
    private var _builtUrl: String? = null

    fun build(session: SessionManager): ApiService {
        val url = session.getServerUrl()
        if (_api != null && _builtUrl == url) return _api!!

        val logging = HttpLoggingInterceptor().apply {
            level = if (br.com.inventario.BuildConfig.DEBUG)
                HttpLoggingInterceptor.Level.BODY
            else
                HttpLoggingInterceptor.Level.NONE
        }

        val client = OkHttpClient.Builder()
            .connectTimeout(3, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(15, TimeUnit.SECONDS)
            .addInterceptor(logging)
            .addInterceptor { chain ->
                val token = session.getToken()
                val request = if (token != null) {
                    chain.request().newBuilder()
                        .addHeader("Authorization", "Bearer $token")
                        .build()
                } else {
                    chain.request()
                }
                val response = chain.proceed(request)
                if (response.code == 401
                    && session.isLoggedIn()
                    && !request.url.encodedPath.contains("login")
                ) {
                    session.logout()
                    reset()
                    val intent = Intent(session.context, LoginActivity::class.java).apply {
                        flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                        putExtra("session_expired", true)
                    }
                    session.context.startActivity(intent)
                }
                response
            }
            .build()

        _api = Retrofit.Builder()
            .baseUrl(url)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)

        _builtUrl = url
        return _api!!
    }

    fun reset() {
        _api = null
        _builtUrl = null
    }
}
