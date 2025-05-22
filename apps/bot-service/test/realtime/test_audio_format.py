#!/usr/bin/env python3

import asyncio
import json
import base64
import websockets
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_websocket_connection():
    # Change this to match your server's websocket URL
    uri = "ws://localhost:8080/realtime"

    logger.info(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to WebSocket server")

            # Wait a moment for the connection to fully establish
            await asyncio.sleep(2)

            # Create a minimal audio message with a small amount of test data
            # This creates a short silent audio sample
            audio_data = base64.b64encode(b"\x00" * 1000).decode("utf-8")

            # Create message in the format expected by the server
            message = {
                "type": "input_audio_buffer.append",
                "audio": audio_data
            }

            # Log and send the message
            logger.info(f"Sending audio message with {len(audio_data)} bytes")
            await websocket.send(json.dumps(message))

            # Wait for any response - use a much longer timeout
            for _ in range(10):  # Try to receive up to 10 messages
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    try:
                        parsed = json.loads(response)
                        msg_type = parsed.get("type", "unknown")
                        logger.info(f"Received message type: {msg_type}")

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

            # Stay connected for a total of 30 seconds to catch any delayed responses
            logger.info("Waiting for 30 seconds to capture any additional responses...")
            await asyncio.sleep(30)

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
