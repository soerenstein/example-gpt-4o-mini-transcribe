# Azure Foundry GPT-4o-Mini-Transcribe Samples

This repo is set up in the same style as the Foundry devblog sample flow:

- Python virtual environment
- `requirements.txt`
- `.env` for endpoint and API key
- Standalone scripts for each scenario

It includes:

- File transcription example (`transcribe_file.py`)
- Real-time transcription from microphone over WebSocket (`realtime_transcribe_mic.py`)

## 1. Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your values:

```env
AZURE_OPENAI_ENDPOINT="https://<resource-name>.services.ai.azure.com"
# OR: https://<your-resource-name>.openai.azure.com
AZURE_OPENAI_API_KEY="<your-api-key>"
AZURE_OPENAI_API_VERSION="2025-03-01-preview"
AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT="gpt-4o-mini-transcribe"
```

Notes:

- `AZURE_OPENAI_ENDPOINT` can be either an Azure OpenAI endpoint (`*.openai.azure.com`) or a Foundry endpoint (`*.services.ai.azure.com`).
- `AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT` should be your deployed `gpt-4o-mini-transcribe` deployment name.
- The microphone realtime script uses transcription sessions (`/openai/v1/realtime?intent=transcription`) and is designed to work with your transcribe deployment.

## Quick Start

After `.env` is configured, run any of these directly:

```bash
# 1) Async/file transcription
python transcribe_file.py <file-name>.m4a

# 2) Realtime transcription from microphone
python realtime_transcribe_mic.py
```

## 2. Audio File -> Transcription Response

Run:

```bash
python transcribe_file.py <filename>.m4a
```

What it does:

- Calls the Azure OpenAI transcription endpoint using your deployment.
- For `*.services.ai.azure.com` endpoints, it uses deployment-scoped REST transcription (`/openai/deployments/{deployment}/audio/transcriptions?api-version=...`).
- Prints the full JSON transcription result (including segment/timestamp data when available).

## 3. Real-Time Transcription From Microphone

Run:

```bash
python realtime_transcribe_mic.py
```

What happens:

- The script opens your default microphone, streams PCM16 mono chunks to a transcription session, and prints transcript events.
- Press Enter to stop recording and finalize the last transcript.

Optional flags:

```bash
python realtime_transcribe_mic.py --device 0 --sample-rate 24000 --chunk-ms 100
```

Optional language hint:

```bash
python realtime_transcribe_mic.py --language de
```

macOS notes:

- The first run prompts for microphone permission. Allow access for your terminal app.

## 4. Troubleshooting

- 401/403: endpoint or API key is wrong.
- 404 on realtime endpoint: verify your account supports the GA path `/openai/v1/realtime`.
- No transcript events: verify audio format is PCM16 mono and that `AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT` matches your deployed transcription model name.
