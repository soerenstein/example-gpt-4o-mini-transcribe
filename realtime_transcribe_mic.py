import argparse
import asyncio
import base64
import json
import os
import queue
from typing import Any

from dotenv import load_dotenv
import sounddevice as sd
import websockets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Realtime transcription from local microphone via Azure OpenAI transcription sessions."
    )
    parser.add_argument("--device", type=int, default=None, help="Optional microphone device index.")
    parser.add_argument("--sample-rate", type=int, default=24000, help="Microphone capture sample rate.")
    parser.add_argument("--chunk-ms", type=int, default=100, help="Audio chunk duration in milliseconds.")
    parser.add_argument(
        "--idle-timeout",
        type=float,
        default=10.0,
        help="Seconds to wait without events after stopping before exit.",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Optional ISO-639-1 language hint, for example 'en' or 'de'.",
    )
    return parser.parse_args()


def build_ws_url(endpoint: str) -> str:
    return endpoint.rstrip("/").replace("https://", "wss://") + "/openai/v1/realtime?intent=transcription"


async def send_audio_from_queue(ws: Any, audio_queue: "queue.Queue[bytes | None]") -> None:
    while True:
        chunk = await asyncio.to_thread(audio_queue.get)
        if chunk is None:
            break

        payload = {
            "type": "input_audio_buffer.append",
            "audio": base64.b64encode(chunk).decode("ascii"),
        }
        await ws.send(json.dumps(payload))

    await ws.send(json.dumps({"type": "input_audio_buffer.commit"}))


async def listen_for_events(ws: Any, idle_timeout: float) -> None:
    deltas_by_item: dict[str, str] = {}

    while True:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=idle_timeout)
        except asyncio.TimeoutError:
            print("No new realtime events, exiting.")
            break

        event = json.loads(raw)
        event_type = event.get("type", "unknown")

        if event_type == "conversation.item.input_audio_transcription.delta":
            item_id = event.get("item_id", "unknown")
            delta = event.get("delta", "")
            if delta:
                deltas_by_item[item_id] = deltas_by_item.get(item_id, "") + delta

        elif event_type == "conversation.item.input_audio_transcription.completed":
            item_id = event.get("item_id", "unknown")
            transcript = event.get("transcript") or deltas_by_item.get(item_id, "")
            print(f"TRANSCRIPT: {transcript}")
            deltas_by_item.pop(item_id, None)

        elif event_type == "conversation.item.input_audio_transcription.failed":
            print("TRANSCRIPTION FAILED EVENT:")
            print(json.dumps(event, indent=2, ensure_ascii=True))

        elif event_type == "error":
            code = (event.get("error") or {}).get("code")
            if code == "input_audio_buffer_commit_empty":
                continue
            print("ERROR EVENT:")
            print(json.dumps(event, indent=2, ensure_ascii=True))
            break


async def main_async() -> None:
    load_dotenv()
    args = parse_args()

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    transcribe_model = os.getenv("AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT", "gpt-4o-mini-transcribe")

    if not endpoint or not api_key:
        raise RuntimeError("Missing AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY in .env")

    ws_url = build_ws_url(endpoint)
    headers = {"api-key": api_key}
    audio_queue: "queue.Queue[bytes | None]" = queue.Queue()

    frames_per_chunk = max(1, int(args.sample_rate * (args.chunk_ms / 1000.0)))

    def on_audio(indata: bytes, frames: int, time_info: Any, status: sd.CallbackFlags) -> None:
        _ = frames
        _ = time_info
        if status:
            print(f"Audio callback status: {status}")
        audio_queue.put(bytes(indata))

    async with websockets.connect(ws_url, additional_headers=headers, max_size=None) as ws:
        transcription_cfg: dict[str, Any] = {"model": transcribe_model}
        if args.language:
            transcription_cfg["language"] = args.language

        session_update = {
            "type": "session.update",
            "session": {
                "type": "transcription",
                "audio": {
                    "input": {
                        "format": {
                            "type": "audio/pcm",
                            "rate": args.sample_rate,
                        },
                        "transcription": {
                            **transcription_cfg,
                        },
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.5,
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": 400,
                        },
                    },
                },
            },
        }
        await ws.send(json.dumps(session_update))

        producer = asyncio.create_task(send_audio_from_queue(ws, audio_queue))
        consumer = asyncio.create_task(listen_for_events(ws, args.idle_timeout))

        print("Microphone streaming started. Speak now, then press Enter to stop.")
        with sd.RawInputStream(
            samplerate=args.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=frames_per_chunk,
            callback=on_audio,
            device=args.device,
        ):
            await asyncio.to_thread(input)

        audio_queue.put(None)
        await asyncio.gather(producer, consumer)


if __name__ == "__main__":
    asyncio.run(main_async())
