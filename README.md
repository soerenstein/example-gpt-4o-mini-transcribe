# Azure Foundry GPT-4o-Mini-Transcribe Samples

This repo now separates the examples by language and keeps sample audio shared:

- `python/` for the Python scripts and Python dependencies
- `kotlin/` for the Gradle-based Kotlin example
- `samples/` for example audio files used by either implementation
- `.env` at the repo root for shared Azure configuration

It includes:

- `python/transcribe_file.py` for file transcription in Python
- `python/realtime_transcribe_mic.py` for realtime microphone transcription in Python
- `kotlin/src/main/kotlin/TranscribeFile.kt` for file transcription in Kotlin with OkHttp

## 1. Repository Layout

```text
.
├── .env.example
├── README.md
├── kotlin/
│   ├── build.gradle.kts
│   ├── settings.gradle.kts
│   ├── gradlew
│   ├── gradle/wrapper/gradle-wrapper.jar
│   ├── gradle/wrapper/gradle-wrapper.properties
│   └── src/main/kotlin/TranscribeFile.kt
├── python/
│   ├── realtime_transcribe_mic.py
│   ├── requirements.txt
│   └── transcribe_file.py
└── samples/
	├── sst-24k-mono.wav
	└── sst.m4a
```

## 2. Shared Setup

```bash
cp .env.example .env
```

Edit `.env` with your Azure values:

```env
AZURE_OPENAI_ENDPOINT="https://<resource-name>.services.ai.azure.com"
# OR: https://<your-resource-name>.openai.azure.com
AZURE_OPENAI_API_KEY="<your-api-key>"
AZURE_OPENAI_API_VERSION="2025-03-01-preview"
AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT="gpt-4o-mini-transcribe"

# Optional: explicit deployment-scoped endpoint for the Kotlin example.
AZURE_OPENAI_TRANSCRIBE_ENDPOINT="https://<resource-name>.services.ai.azure.com/openai/deployments/gpt-4o-mini-transcribe/audio/transcriptions?api-version=2025-03-01-preview"

# Optional: audio file path for the Kotlin example when no CLI argument is provided.
AZURE_OPENAI_AUDIO_FILE="samples/sst-24k-mono.wav"

# Optional multipart hints for the Kotlin example.
# AZURE_OPENAI_LANGUAGE="de"
# AZURE_OPENAI_TEMPERATURE="0"
```

Notes:

- `AZURE_OPENAI_ENDPOINT` can be either an Azure OpenAI endpoint (`*.openai.azure.com`) or a Foundry endpoint (`*.services.ai.azure.com`).
- `AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT` should be your deployed `gpt-4o-mini-transcribe` deployment name.
- `AZURE_OPENAI_TRANSCRIBE_ENDPOINT` is the most direct option for the Kotlin sample because it already contains the deployment-scoped `/audio/transcriptions` path.

## 3. Python Example

Setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r python/requirements.txt
```

Run file transcription:

```bash
python python/transcribe_file.py samples/sst.m4a
```

Run realtime microphone transcription:

```bash
python python/realtime_transcribe_mic.py
```

Optional realtime flags:

```bash
python python/realtime_transcribe_mic.py --device 0 --sample-rate 24000 --chunk-ms 100
python python/realtime_transcribe_mic.py --language de
```

## 4. Kotlin Example

Prerequisite:

```bash
java -version
```

The Kotlin example uses OkHttp and sends `multipart/form-data` to a deployment-scoped endpoint like:

```text
https://<resource>.services.ai.azure.com/openai/deployments/<deployment-name>/audio/transcriptions?api-version=2025-03-01-preview
```

It sends these form parts by default:

- `file`
- `response_format=text`

It can also send these optional parts when corresponding env vars are set:

- `language`
- `temperature`

Run directly with Gradle:

```bash
cd kotlin
./gradlew --no-daemon run --args="../samples/sst-24k-mono.wav"
```

The Kotlin example automatically loads the repo-root `.env` file when present, so you do not need to `export` the variables manually for this command.

If you want to run it from the repo root without changing shells, use a subshell:

```bash
(cd kotlin && ./gradlew --no-daemon run --args="../samples/sst-24k-mono.wav")
```

The Kotlin folder includes a checked-in Gradle wrapper, so you do not need a separate `gradle` install.
The build is configured to emit JVM 17 bytecode, but it can compile with a newer installed JDK such as Java 26.

Behavior:

- The program prints the transcription result to stdout.
- On non-2xx responses, it throws an error that includes the full response body.
- It does not add a multipart `model` field by default because the deployment name is already part of the URL.

## 5. Troubleshooting

- 401/403: endpoint or API key is wrong.
- 404 on realtime endpoint: verify your account supports the GA path `/openai/v1/realtime`.
- No transcript events: verify audio format is PCM16 mono and that `AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT` matches your deployed transcription model name.
- Kotlin multipart 400 error: do not manually set `Content-Type: multipart/form-data`. OkHttp must generate the boundary itself.
- Missing multipart boundary: this is usually caused by overriding the request `Content-Type` header manually.
- Wrong auth header: API key auth must use `api-key: <key>`. `Authorization: Bearer ...` is only for Entra ID tokens.
- Hard-to-diagnose 400 responses: always log the full error response body. The Kotlin example throws with the response body included.
- `gradle: command not found`: use `./gradlew` inside `kotlin/`. The repo includes a Gradle wrapper, not a global Gradle install.
- `Missing AZURE_OPENAI_TRANSCRIBE_ENDPOINT`: make sure the repo-root `.env` exists and contains either `AZURE_OPENAI_TRANSCRIBE_ENDPOINT` or the combination of `AZURE_OPENAI_ENDPOINT` plus `AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT`.

## 6. Python vs Kotlin Notes

- The Python example uses `requests` helpers for multipart upload, while the Kotlin example builds the multipart request explicitly with OkHttp.
- In Kotlin, you should not add `Content-Type: multipart/form-data` yourself. The OkHttp multipart builder generates the correct header including the boundary.
- The Kotlin example defaults to `response_format=text` and prints raw text, while the Python file example prints JSON.
- The Kotlin example uses API key auth with `api-key`, not `Authorization: Bearer`.
