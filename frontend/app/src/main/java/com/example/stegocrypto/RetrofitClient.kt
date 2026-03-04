package com.example.stegocrypto

import okhttp3.MultipartBody
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

// --- DATA CLASSES (Maps exactly to Python's JSON response) ---
data class VerificationResponse(
    val status: String,
    val message: String,
    val metadata: MetadataMap?,
    val checks: ChecksMap,
    val details: String
)

data class MetadataMap(
    val authority: String,
    val timestamp: String,
    val message: String
)

data class ChecksMap(
    val signature: Boolean,
    val integrity: Boolean
)

// --- API INTERFACE ---
interface ApiService {
    @GET("/")
    suspend fun checkHealth(): HealthResponse

    // NEW: The Multipart upload endpoint
    @Multipart
    @POST("/verify/")
    suspend fun verifyDocument(
        @Part file: MultipartBody.Part
    ): VerificationResponse
}

data class HealthResponse(val status: String, val system: String, val version: String)

// --- CLIENT BUILDER ---
object RetrofitClient {
    private const val BASE_URL = "https://your-custom-domain.ngrok-free.app"

    val instance: ApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}
