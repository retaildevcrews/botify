#!/usr/bin/env python3

import asyncio
import json
import websockets
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def listen_to_websocket():
    # Change this to match your server's websocket URL
    uri = "ws://localhost:8080/realtime"

    logger.info(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to WebSocket server")

            # Just listen for messages for 30 seconds
            logger.info("Listening for 30 seconds...")
            end_time = asyncio.get_event_loop().time() + 30

            while asyncio.get_event_loop().time() < end_time:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1)
                    try:
                        parsed = json.loads(response)
                        msg_type = parsed.get("type", "unknown")
                        logger.info(f"Received message type: {msg_type}")
                        logger.info(f"Full message: {parsed}")
                    except json.JSONDecodeError:
                        logger.info(f"Received non-JSON response: {response[:100]}...")
                except asyncio.TimeoutError:
                    # Just a timeout for our polling loop
                    pass
                except Exception as e:
                    logger.error(f"Error receiving message: {str(e)}")
                    break

    except websockets.exceptions.ConnectionClosedError as e:
        logger.error(f"WebSocket connection closed unexpectedly: {e}")
    except ConnectionRefusedError:
        logger.error("Connection refused. Is the server running?")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(listen_to_websocket())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(0)
