#!/usr/bin/env python3

"""
Simple test script for Botify Realtime WebSocket connection.
This script tests the basic functionality with error diagnostics.

Usage:
  python3 quick_test.py [--host HOST] [--port PORT]

Requirements:
  - websockets
"""

import asyncio
import websockets
import json
import base64
import logging
import sys
import argparse
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_silence(duration_seconds=1):
    """Generate silence audio data (all zeros)"""
    # 16kHz, 16-bit mono = 2 bytes per sample
    num_samples = int(16000 * duration_seconds)
    # Create a buffer of zeros (silence)
    silence_data = bytearray(num_samples * 2)
    return base64.b64encode(silence_data).decode('utf-8')

async def run_test(host="localhost", port=8080, path="/realtime"):
    """Run a simple WebSocket test with the Botify Realtime API"""
    uri = f"ws://{host}:{port}{path}"
    logger.info(f"Connecting to {uri}")

    try:
        async with websockets.connect(uri) as ws:
            logger.info("Connected to WebSocket server")

            # Wait for initial session messages
            initial_messages = []
            for _ in range(3):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=2)
                    try:
                        msg = json.loads(response)
                        logger.info(f"Received: {msg['type']}")
                        initial_messages.append(msg)
                    except json.JSONDecodeError:
                        logger.warning(f"Received non-JSON message: {response[:50]}...")
                except asyncio.TimeoutError:
                    break

            if not initial_messages:
                logger.error("No initial messages received from server!")
                return

            # Send a test audio chunk (silence)
            audio_data = generate_silence()
            logger.info(f"Sending audio data ({len(audio_data)} bytes)")

            await ws.send(json.dumps({
                "type": "input_audio_buffer.append",
                "audio": audio_data
            }))

            # Send flush to end the audio stream
            logger.info("Sending flush message")
            await ws.send(json.dumps({
                "type": "input_audio_buffer.flush"
            }))

            # Wait for responses
            for _ in range(10):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=1)
                    try:
                        msg = json.loads(response)
                        msg_type = msg.get("type", "unknown")
                        logger.info(f"Received: {msg_type}")

                        # Check for errors
                        if msg_type == "error":
                            error = msg.get("error", {})
                            if isinstance(error, dict):
                                logger.error(f"Error: {error.get('message', 'Unknown error')}")
                                logger.error(f"Code: {error.get('code', 'unknown')}")
                                logger.error(f"Type: {error.get('type', 'unknown')}")
                    except json.JSONDecodeError:
                        logger.warning(f"Received non-JSON message: {response[:50]}...")
                except asyncio.TimeoutError:
                    continue

            logger.info("Test completed successfully")

    except Exception as e:
        logger.error(f"Error during WebSocket test: {str(e)}")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Simple WebSocket test for Botify Realtime API")
    parser.add_argument("--host", default="localhost", help="Host to connect to")
    parser.add_argument("--port", type=int, default=8080, help="Port to connect to")
    parser.add_argument("--path", default="/realtime", help="WebSocket endpoint path")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    try:
        asyncio.run(run_test(args.host, args.port, args.path))
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(0)
