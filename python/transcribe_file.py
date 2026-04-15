import argparse
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
import requests


def build_client(endpoint: str, api_key: str) -> OpenAI:
    base_url = endpoint.rstrip("/") + "/openai/v1/"
    return OpenAI(api_key=api_key, base_url=base_url)


def transcribe_via_deployment_rest(
    endpoint: str,
    api_key: str,
    api_version: str,
    deployment: str,
    audio_file: Path,
) -> dict[str, Any]:
    url = (
        endpoint.rstrip("/")
        + f"/openai/deployments/{deployment}/audio/transcriptions"
        + f"?api-version={api_version}"
    )

    with audio_file.open("rb") as fh:
        response = requests.post(
            url,
            headers={"api-key": api_key},
            files={"file": (audio_file.name, fh)},
            data={"model": deployment},
            timeout=300,
        )

    response.raise_for_status()
    return response.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe an audio file with a GPT-4o-mini-transcribe deployment in Azure Foundry."
    )
    parser.add_argument("audio_file", type=Path, help="Path to input audio file (mp3, mp4, mpeg, mpga, m4a, wav, webm).")
    return parser.parse_args()


def main() -> None:
    load_dotenv()

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-03-01-preview")
    deployment = os.getenv("AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT", "gpt-4o-mini-transcribe")

    if not endpoint or not api_key:
        raise RuntimeError("Missing AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY in .env")

    args = parse_args()
    if not args.audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {args.audio_file}")

    # Foundry-style endpoints commonly require deployment-scoped REST path.
    if endpoint.rstrip("/").endswith(".services.ai.azure.com"):
        result = transcribe_via_deployment_rest(
            endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
            deployment=deployment,
            audio_file=args.audio_file,
        )
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return

    client = build_client(endpoint, api_key)
    try:
        with args.audio_file.open("rb") as fh:
            result = client.audio.transcriptions.create(
                model=deployment,
                file=fh,
                response_format="verbose_json",
            )
        print(json.dumps(result.model_dump(), indent=2, ensure_ascii=True))
    except Exception:
        # Fallback for deployments that only expose deployment-scoped transcription routes.
        result = transcribe_via_deployment_rest(
            endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
            deployment=deployment,
            audio_file=args.audio_file,
        )
        print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
