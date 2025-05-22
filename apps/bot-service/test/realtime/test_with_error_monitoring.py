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
import argparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration options with defaults
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8080
DEFAULT_PATH = "/realtime"

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

async def check_server_status(host, port):
    """Check server status and configuration via the status endpoint."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            status_url = f"http://{host}:{port}/realtime-status"
            logger.info(f"Checking server status at {status_url}")

            try:
                async with session.get(status_url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info("Server status check successful")

                        # Check for WebSocket support
                        if not data.get("websocket_support", {}).get("has_websocket_support", False):
                            logger.warning("Server does not have WebSocket support!")
                            libraries = data.get("websocket_support", {}).get("libraries_available", [])
                            logger.warning(f"Available WebSocket libraries: {libraries}")

                        # Check environment configuration
                        env_config = data.get("environment_config", {})
                        if not env_config.get("all_required_vars_set", True):
                            missing_vars = env_config.get("missing_vars", [])
                            logger.warning(f"Missing environment variables: {missing_vars}")

                        # Display turn detection configuration
                        turn_detection = env_config.get("turn_detection_type", "unknown")
                        logger.info(f"Turn detection type: {turn_detection}")

                        return data
                    else:
                        logger.warning(f"Server status check failed: {response.status} {response.reason}")
                        return None
            except aiohttp.ClientError as e:
                logger.error(f"Failed to connect to status endpoint: {e}")
                return None
    except ImportError:
        logger.warning("aiohttp not available, skipping server status check")
        return None

async def send_test_message(websocket, message_type, **kwargs):
    """Send a test message and log it."""
    message = {"type": message_type, **kwargs}
    logger.info(f"Sending message: {message_type}")
    await websocket.send(json.dumps(message))
    return message

async def process_response(response):
    """Process and log the response from the server."""
    try:
        parsed = json.loads(response)
        msg_type = parsed.get("type", "unknown")
        logger.info(f"Received message type: {msg_type}")

        if msg_type == "error":
            handle_error_response(parsed)
        elif msg_type == "conversation.item.input_audio_transcription.completed":
            transcript = parsed.get("transcript", "")
            if transcript:
                logger.info(f"Transcription: {transcript}")
            else:
                logger.warning("Empty transcription received")
        elif msg_type == "response.audio_transcript.delta":
            logger.info(f"Response delta: {parsed.get('delta', '')}")

        return parsed
    except json.JSONDecodeError:
        logger.info(f"Received non-JSON response: {response[:100]}...")
        return response

def handle_error_response(parsed):
    """Handle and log error responses with detailed information."""
    error_details = parsed.get("error", {})
    logger.error(f"Error response: {error_details}")

    if isinstance(error_details, dict):
        message = error_details.get("message", "Unknown error")
        error_type = error_details.get("type", "unknown")
        code = error_details.get("code", "unknown")
        param = error_details.get("param", "none")
        event_id = error_details.get("event_id", "none")
        details = error_details.get("details", "none")

        logger.error(f"Error details:")
        logger.error(f"  - Message: {message}")
        logger.error(f"  - Type: {error_type}")
        logger.error(f"  - Code: {code}")
        logger.error(f"  - Parameter: {param}")
        logger.error(f"  - Event ID: {event_id}")

        # Provide troubleshooting assistance based on error type
        if code == "internal_error" or error_type == "server_error":
            logger.error("Internal server error detected - likely a configuration issue with the Azure OpenAI API")
            logger.error("Check the server logs for more details and consider adjusting turn_detection settings")

            # Specific guidance for turn detection errors
            if "turn_detection" in message.lower() or param == "turn_detection":
                logger.error("This appears to be a turn detection configuration error.")
                logger.error("Recommended actions:")
                logger.error("1. Try using 'server_vad' for AZURE_SPEECH_SERVICES_TURN_DETECTION_TYPE")
                logger.error("2. Ensure noise reduction is properly configured for 'azure_semantic_vad'")
                logger.error("3. Check if the current parameters are compatible with the chosen turn detection type")

        elif code == "client_error" or error_type == "invalid_request_error":
            logger.error("Client-side error detected - check the format of your request")
            if "audio" in message.lower() or param == "audio":
                logger.error("This appears to be related to the audio format or data")
                logger.error("Ensure audio is correctly base64 encoded and in PCM16 format")

        elif code == "configuration_error":
            logger.error("Configuration error detected - check server environment variables")
            logger.error("You may need to restart the server after adjusting configuration")

async def test_websocket_connection(host=DEFAULT_HOST, port=DEFAULT_PORT, path=DEFAULT_PATH):
    """Test the WebSocket connection with detailed error reporting."""
    uri = f"ws://{host}:{port}{path}"
    logger.info(f"Connecting to {uri}...")

    # First check server status
    await check_server_status(host, port)

    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to WebSocket server")

            # Wait for session.created and session.updated messages
            logger.info("Waiting for initial session messages...")
            session_updated = False

            for _ in range(5):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2)
                    parsed = await process_response(response)

                    if isinstance(parsed, dict) and parsed.get("type") == "session.updated":
                        session_updated = True
                        break

                except asyncio.TimeoutError:
                    logger.warning("Timeout waiting for session messages")
                    break

            if not session_updated:
                logger.error("Did not receive session.updated message, aborting test")
                return

            logger.info("Session setup complete, sending audio test message")

            # Generate more realistic audio data (sine wave)
            audio_binary = generate_test_audio()
            audio_data = base64.b64encode(audio_binary).decode("utf-8")

            # Send audio message
            await send_test_message(websocket, "input_audio_buffer.append", audio=audio_data)

            # Send end-of-stream message
            await send_test_message(websocket, "input_audio_buffer.flush")

            # Wait for responses with explicit error checking
            received_response = False
            for _ in range(20):  # Try to receive up to 20 messages
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1)
                    parsed = await process_response(response)
                    received_response = True

                    # Stop if we receive an error
                    if isinstance(parsed, dict) and parsed.get("type") == "error":
                        break

                except asyncio.TimeoutError:
                    # Just a short timeout for our polling loop
                    continue

            if not received_response:
                logger.warning("No responses received from server after sending audio")

    except websockets.exceptions.ConnectionClosedError as e:
        logger.error(f"WebSocket connection closed unexpectedly: {e}")
        logger.error(f"Close code: {e.code}, Close reason: {e.reason if hasattr(e, 'reason') else 'None'}")
    except ConnectionRefusedError:
        logger.error("Connection refused. Is the server running?")
        logger.error(f"Tried to connect to: {uri}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test WebSocket connection to Botify Realtime API')
    parser.add_argument('--host', default=DEFAULT_HOST, help=f'Host to connect to (default: {DEFAULT_HOST})')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help=f'Port to connect to (default: {DEFAULT_PORT})')
    parser.add_argument('--path', default=DEFAULT_PATH, help=f'WebSocket path (default: {DEFAULT_PATH})')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    return parser.parse_args()

if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()

    # Set logging level
    if args.debug:
        logger.setLevel(logging.DEBUG)

    try:
        logger.info(f"Starting WebSocket test to {args.host}:{args.port}{args.path}")
        asyncio.run(test_websocket_connection(args.host, args.port, args.path))
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(0)
