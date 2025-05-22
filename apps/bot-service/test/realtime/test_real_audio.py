#!/usr/bin/env python3

import asyncio
import json
import base64
import websockets
import sys
import logging
import os
import tempfile
import wave
import struct
import random
import math

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_test_audio():
    """Generate a sine wave audio sample that's more realistic than silence."""
    # Create a temporary WAV file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_filename = temp_file.name

    # Parameters for the WAV file
    sample_rate = 16000  # 16kHz
    duration = 1  # seconds
    frequency = 440  # Hz (A4 note)

    # Generate a sine wave
    samples = []
    for i in range(int(duration * sample_rate)):
        # Generate a simple sine wave with some added noise
        t = float(i) / sample_rate
        value = int(32767.0 * 0.5 * (
            0.9 * (math.sin(2 * math.pi * frequency * t)) +
            0.1 * random.uniform(-1, 1)  # Add a small amount of noise
        ))
        samples.append(struct.pack('<h', value))

    # Write samples to a WAV file
    with wave.open(temp_filename, 'wb') as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(samples))

    # Read the WAV file as binary data
    with open(temp_filename, 'rb') as f:
        audio_data = f.read()

    # Clean up
    os.unlink(temp_filename)

    return audio_data

async def test_websocket_connection():
    # Change this to match your server's websocket URL
    uri = "ws://localhost:8080/realtime"

    logger.info(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to WebSocket server")

            # Wait a moment for the connection to fully establish
            await asyncio.sleep(2)

            # Generate more realistic audio data (sine wave)
            audio_binary = generate_test_audio()
            audio_data = base64.b64encode(audio_binary).decode("utf-8")

            # Create message in the format expected by the server
            message = {
                "type": "input_audio_buffer.append",
                "audio": audio_data
            }

            # Log and send the message
            logger.info(f"Sending audio message with {len(audio_data)} bytes")
            await websocket.send(json.dumps(message))

            # Send end-of-stream message
            end_message = {
                "type": "input_audio_buffer.flush"
            }
            logger.info("Sending flush message to indicate end of audio")
            await websocket.send(json.dumps(end_message))

            # Wait for any response - use a much longer timeout
            for _ in range(15):  # Try to receive up to 15 messages
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2)
                    try:
                        parsed = json.loads(response)
                        msg_type = parsed.get("type", "unknown")
                        logger.info(f"Received message type: {msg_type}")
                        logger.info(f"Full message: {parsed}")

                        # Check for errors
                        if msg_type == "error":
                            error_details = parsed.get("error", {})
                            logger.error(f"Error response: {error_details}")
                            if isinstance(error_details, dict):
                                message = error_details.get("message", "Unknown error")
                                error_type = error_details.get("type", "unknown")
                                code = error_details.get("code", "unknown")
                                logger.error(f"Error details - Message: {message}, Type: {error_type}, Code: {code}")
                    except json.JSONDecodeError:
                        logger.info(f"Received non-JSON response: {response[:100]}...")

                except asyncio.TimeoutError:
                    logger.warning("Timeout waiting for response")
                    continue

    except websockets.exceptions.ConnectionClosedError as e:
        logger.error(f"WebSocket connection closed unexpectedly: {e}")
    except ConnectionRefusedError:
        logger.error("Connection refused. Is the server running?")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(test_websocket_connection())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(0)
