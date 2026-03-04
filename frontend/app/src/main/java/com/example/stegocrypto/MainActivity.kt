package com.example.stegocrypto

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.webkit.MimeTypeMap
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.stegocrypto.ui.theme.StegoCryptoTheme
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File
import java.io.FileOutputStream

class MainActivity : ComponentActivity() {
    @OptIn(ExperimentalMaterial3Api::class)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 1. Check if we were opened from the Share Menu!
        var sharedUri: Uri? = null
        if (intent?.action == Intent.ACTION_SEND) {
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
                sharedUri = intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
            } else {
                @Suppress("DEPRECATION")
                sharedUri = intent.getParcelableExtra(Intent.EXTRA_STREAM)
            }
        }

        setContent {
            StegoCryptoTheme {
                Scaffold(
                    topBar = {
                        TopAppBar(
                            title = { Text("StegoCrypto", fontWeight = FontWeight.Bold) },
                            colors = TopAppBarDefaults.topAppBarColors(
                                containerColor = MaterialTheme.colorScheme.primary,
                                titleContentColor = MaterialTheme.colorScheme.onPrimary
                            )
                        )
                    }
                ) { padding ->
                    Surface(
                        modifier = Modifier.fillMaxSize().padding(padding),
                        color = MaterialTheme.colorScheme.background
                    ) {
                        MainScreen(initialUri = sharedUri)
                    }
                }
            }
        }
    }
}

@Composable
fun MainScreen(initialUri: Uri?) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    val db = remember { AppDatabase.getDatabase(context) }
    val historyList by db.scanHistoryDao().getAllHistory().collectAsState(initial = emptyList())

    var currentUri by remember { mutableStateOf(initialUri) }
    var isUploading by remember { mutableStateOf(false) }
    var currentResult by remember { mutableStateOf<VerificationResponse?>(null) }
    var currentFileName by remember { mutableStateOf("") }

    val filePickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        if (uri != null) {
            currentUri = uri
            currentResult = null
        }
    }

    LaunchedEffect(currentUri) {
        if (currentUri != null && currentResult == null) {
            isUploading = true
            coroutineScope.launch {
                try {
                    val file = getFileFromUri(context, currentUri!!)
                    currentFileName = file.name
                    val requestFile = file.asRequestBody("multipart/form-data".toMediaTypeOrNull())
                    val body = MultipartBody.Part.createFormData("file", file.name, requestFile)

                    val response = RetrofitClient.instance.verifyDocument(body)
                    currentResult = response

                    withContext(Dispatchers.IO) {
                        db.scanHistoryDao().insertRecord(
                            ScanRecord(
                                filename = file.name,
                                status = response.status,
                                authority = response.metadata?.authority ?: "Unknown",
                                timestamp = response.metadata?.timestamp ?: "Now"
                            )
                        )
                    }
                } catch (e: Exception) {
                    currentResult = VerificationResponse(
                        status = "error", message = e.localizedMessage ?: "Network Error",
                        metadata = null, checks = ChecksMap(signature = false, integrity = false), details = ""
                    )
                } finally {
                    isUploading = false
                }
            }
        }
    }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Button(
            onClick = { filePickerLauncher.launch("*/*") },
            modifier = Modifier.fillMaxWidth().height(56.dp),
            shape = RoundedCornerShape(12.dp)
        ) {
            Icon(Icons.Default.Search, contentDescription = "Scan")
            Spacer(Modifier.width(8.dp))
            Text("Select Document to Verify", style = MaterialTheme.typography.titleMedium)
        }

        Spacer(modifier = Modifier.height(16.dp))

        if (isUploading) {
            CircularProgressIndicator(modifier = Modifier.align(Alignment.CenterHorizontally))
            Spacer(modifier = Modifier.height(8.dp))
            Text("Analyzing Cryptographic Proof...", modifier = Modifier.align(Alignment.CenterHorizontally))
        }

        currentResult?.let { result ->
            ResultCard(result, currentFileName)
        }

        Spacer(modifier = Modifier.height(24.dp))

        Text("Scan History", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

        LazyColumn(modifier = Modifier.fillMaxSize()) {
            items(historyList) { record ->
                HistoryItem(record)
            }
        }
    }
}

// --- SUB-COMPOSABLE: The Dynamic Result Card ---
@Composable
fun ResultCard(result: VerificationResponse, fileName: String) {
    val isDark = isSystemInDarkTheme()

    // 1. Dynamic Backgrounds
    val bgColor = when (result.status.lowercase()) {
        "verified" -> if (isDark) Color(0xFF0C3B14) else Color(0xFFE8F5E9)
        "tampered" -> if (isDark) Color(0xFF4A2A00) else Color(0xFFFFF3E0)
        "fake", "error" -> if (isDark) Color(0xFF4A0B0B) else Color(0xFFFFEBEE)
        else -> if (isDark) Color(0xFF2C2C2C) else Color(0xFFF5F5F5)
    }

    // 2. Dynamic Title Texts & Icons
    val icon = when (result.status.lowercase()) {
        "verified" -> Icons.Default.CheckCircle
        "tampered" -> Icons.Default.Warning
        else -> Icons.Default.Close
    }
    val titleText = when (result.status.lowercase()) {
        "verified" -> "VERIFIED AUTHENTIC"
        "tampered" -> "TAMPERED CONTENT"
        "fake" -> "FAKE SIGNATURE"
        else -> "VERIFICATION ERROR"
    }

    // 3. Dynamic High-Contrast Text Colors
    val titleColor = when (result.status.lowercase()) {
        "verified" -> if (isDark) Color(0xFF81C784) else Color(0xFF2E7D32)
        "tampered" -> if (isDark) Color(0xFFFFB74D) else Color(0xFFEF6C00)
        "fake", "error" -> if (isDark) Color(0xFFE57373) else Color(0xFFC62828)
        else -> if (isDark) Color.White else Color.Black
    }

    // Explicitly define Standard Text colors so they don't get lost on the custom backgrounds
    val standardTextColor = if (isDark) Color(0xFFE0E0E0) else Color.Black
    val detailsTextColor = if (isDark) Color.LightGray else Color.DarkGray

    Card(
        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
        colors = CardDefaults.cardColors(
            containerColor = bgColor,
            contentColor = standardTextColor // Enforces readability!
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(icon, contentDescription = null, tint = titleColor, modifier = Modifier.size(32.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text(titleText, color = titleColor, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
            }
            Spacer(modifier = Modifier.height(12.dp))
            Text("File: $fileName", fontWeight = FontWeight.Medium)
            Text("Authority: ${result.metadata?.authority ?: "N/A"}")
            Text("Status: ${result.message}", style = MaterialTheme.typography.bodyMedium)
            Spacer(modifier = Modifier.height(8.dp))
            Text("Details: ${result.details}", style = MaterialTheme.typography.bodySmall, color = detailsTextColor)
        }
    }
}

// --- SUB-COMPOSABLE: The History List Row ---
@Composable
fun HistoryItem(record: ScanRecord) {
    val isDark = isSystemInDarkTheme()

    // Adjust dot colors to pop properly on dark surface
    val statusColor = when (record.status.lowercase()) {
        "verified" -> if (isDark) Color(0xFF81C784) else Color(0xFF2E7D32)
        "tampered" -> if (isDark) Color(0xFFFFB74D) else Color(0xFFEF6C00)
        else -> if (isDark) Color(0xFFE57373) else Color(0xFFC62828)
    }

    val subtitleColor = if (isDark) Color.LightGray else Color.Gray

    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier.size(12.dp).background(statusColor, shape = RoundedCornerShape(50))
        )
        Spacer(modifier = Modifier.width(16.dp))
        Column {
            Text(record.filename, fontWeight = FontWeight.Bold, maxLines = 1)
            Text("${record.authority} • ${record.status.uppercase()}", style = MaterialTheme.typography.bodySmall, color = subtitleColor)
        }
    }
}

// --- UTILITY: Convert Android URI to a real File ---
fun getFileFromUri(context: Context, uri: Uri): File {
    val contentResolver = context.contentResolver

    var fileName = "temp_file"
    contentResolver.query(uri, null, null, null, null)?.use { cursor ->
        if (cursor.moveToFirst()) {
            val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (nameIndex != -1) {
                fileName = cursor.getString(nameIndex)
            }
        }
    }

    if (!fileName.contains(".")) {
        val mimeType = contentResolver.getType(uri)
        val extension = MimeTypeMap.getSingleton().getExtensionFromMimeType(mimeType)
        if (extension != null) {
            fileName += ".$extension"
        }
    }

    val tempFile = File(context.cacheDir, fileName)
    val inputStream = contentResolver.openInputStream(uri)
    val outputStream = FileOutputStream(tempFile)

    inputStream?.use { input ->
        outputStream.use { output ->
            input.copyTo(output)
        }
    }
    return tempFile
}