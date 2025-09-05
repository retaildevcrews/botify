#!/usr/bin/env python3
"""
Headless CLI to stream a WAV file to the Realtime API (Azure/OpenAI) without running the proxy server.

Usage:
  python apps/tools/test_realtime_audio.py --wav /workspaces/starbucks_menu/audio/orders1/segment_008.wav \
      [--chunk-ms 100] [--timeout 90] [--verbose]

Env vars: AZURE_OPENAI_API_KEY/OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT/OPENAI_ENDPOINT,
AZURE_OPENAI_DEPLOYMENT/OPENAI_MODEL, AZURE_OPENAI_API_VERSION/OPENAI_API_VERSION, plus REALTIME_* flags.
"""
import argparse
import asyncio
import logging
import os
import sys

# Ensure repo root and api/src are on sys.path for package imports
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
API_SRC = os.path.abspath(os.path.join(REPO_ROOT, "apps", "api", "src"))
if API_SRC not in sys.path:
    sys.path.insert(0, API_SRC)

from realtime.realtime_common import run_audio_e2e  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stream a WAV file to Realtime WS without running the server")
    parser.add_argument("--wav", required=True, help="Path to WAV file to stream")
    parser.add_argument("--chunk-ms", type=int, default=100, help="Chunk duration in milliseconds (default: 100)")
    parser.add_argument("--timeout", type=int, default=90, help="Timeout in seconds for the response (default: 90)")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.verbose:
        logging.getLogger().setLevel("DEBUG")

    wav_path = args.wav
    if not os.path.isabs(wav_path):
        wav_path = os.path.abspath(wav_path)

    if not os.path.exists(wav_path):
        print(f"WAV file not found: {wav_path}", file=sys.stderr)
        return 2

    async def _run() -> int:
        return await run_audio_e2e(wav_path, chunk_ms=args.chunk_ms, timeout_sec=args.timeout)

    try:
        return asyncio.run(_run())
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
