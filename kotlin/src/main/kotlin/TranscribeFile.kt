import java.io.File
import java.nio.file.Files
import io.github.cdimascio.dotenv.Dotenv
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody

private data class Config(
    val endpoint: String,
    val apiKey: String,
    val audioFile: File,
    val language: String?,
    val temperature: String?,
)

private val dotenv: Dotenv? = loadDotenv()

fun main(args: Array<String>) {
    val config = loadConfig(args)
    val request = buildRequest(config)
    val client = OkHttpClient()

    client.newCall(request).execute().use { response ->
        val responseBody = response.body?.string().orEmpty()

        if (!response.isSuccessful) {
            error(
                "Transcription request failed with HTTP ${response.code}. " +
                    "Response body:\n$responseBody"
            )
        }

        println(responseBody)
    }
}

private fun loadConfig(args: Array<String>): Config {
    val endpoint =
        env("AZURE_OPENAI_TRANSCRIBE_ENDPOINT")
            ?: buildDeploymentScopedEndpoint()
            ?: error(
                "Missing AZURE_OPENAI_TRANSCRIBE_ENDPOINT. " +
                    "Alternatively set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT, " +
                    "and optionally AZURE_OPENAI_API_VERSION."
            )

    val apiKey = env("AZURE_OPENAI_API_KEY")
        ?: error("Missing AZURE_OPENAI_API_KEY.")

    val audioPath = args.firstOrNull()?.takeIf { it.isNotBlank() }
        ?: env("AZURE_OPENAI_AUDIO_FILE")
        ?: error("Missing audio file. Pass it as the first argument or set AZURE_OPENAI_AUDIO_FILE.")

    val audioFile = File(audioPath)
    require(audioFile.exists()) { "Audio file does not exist: ${audioFile.absolutePath}" }
    require(audioFile.isFile) { "Audio path is not a file: ${audioFile.absolutePath}" }

    return Config(
        endpoint = endpoint,
        apiKey = apiKey,
        audioFile = audioFile,
        language = env("AZURE_OPENAI_LANGUAGE"),
        temperature = env("AZURE_OPENAI_TEMPERATURE"),
    )
}

private fun buildDeploymentScopedEndpoint(): String? {
    val baseEndpoint = env("AZURE_OPENAI_ENDPOINT") ?: return null
    val deployment = env("AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT") ?: return null
    val apiVersion = env("AZURE_OPENAI_API_VERSION") ?: "2025-03-01-preview"

    return buildString {
        append(baseEndpoint.trimEnd('/'))
        append("/openai/deployments/")
        append(deployment)
        append("/audio/transcriptions?api-version=")
        append(apiVersion)
    }
}

private fun buildRequest(config: Config): Request {
    val mediaType = Files.probeContentType(config.audioFile.toPath())?.toMediaTypeOrNull()
        ?: "application/octet-stream".toMediaTypeOrNull()

    val multipartBody = MultipartBody.Builder()
        .setType(MultipartBody.FORM)
        .addFormDataPart(
            name = "file",
            filename = config.audioFile.name,
            body = config.audioFile.asRequestBody(mediaType),
        )
        .addFormDataPart("response_format", "text")
        .apply {
            config.language?.takeIf { it.isNotBlank() }?.let { addFormDataPart("language", it) }
            config.temperature?.takeIf { it.isNotBlank() }?.let { addFormDataPart("temperature", it) }
            // The deployment name is already encoded in the URL path, so a multipart "model" part is not needed by default.
        }
        .build()

    return Request.Builder()
        .url(config.endpoint)
        .header("api-key", config.apiKey)
        // Authorization: Bearer ... is for Entra ID tokens. API key auth uses the api-key header instead.
        .post(multipartBody)
        // Do not set Content-Type manually here. OkHttp adds the multipart boundary automatically.
        .build()
}

private fun env(name: String): String? =
    System.getenv(name)?.trim()?.takeIf { it.isNotEmpty() }
        ?: dotenv?.get(name)?.trim()?.takeIf { it.isNotEmpty() }

private fun loadDotenv(): Dotenv? {
    val envFile = sequenceOf(File(".env"), File("../.env")).firstOrNull { it.isFile } ?: return null

    return Dotenv.configure()
        .directory(envFile.parentFile?.absolutePath ?: ".")
        .filename(envFile.name)
        .ignoreIfMalformed()
        .ignoreIfMissing()
        .load()
}
