#!/bin/bash

echo "Testing Botify Realtime API format compatibility..."

# Test the status endpoint for diagnostic info
echo -e "\n\033[1;36m=== Checking WebSocket Status ===\033[0m"
STATUS_RESPONSE=$(curl -s http://localhost:8080/realtime-status)

# Check if the response contains WebSocket support info
if [[ $STATUS_RESPONSE == *"websocket_support"* ]]; then
    echo -e "\033[1;32m✓ Server is responding to status checks\033[0m"

    # Check for WebSocket library support
    if [[ $STATUS_RESPONSE == *"has_websocket_support\":true"* ]]; then
        echo -e "\033[1;32m✓ WebSocket support is enabled\033[0m"
    else
        echo -e "\033[1;31m✗ WebSocket support is not enabled\033[0m"
    fi

    # Print turn detection type
    if [[ $STATUS_RESPONSE == *"turn_detection_type"* ]]; then
        TURN_TYPE=$(echo $STATUS_RESPONSE | grep -o '"turn_detection_type":"[^"]*"' | cut -d':' -f2 | tr -d '"')
        echo -e "\033[1;36mℹ Turn detection type: $TURN_TYPE\033[0m"
    fi
else
    echo -e "\033[1;31m✗ Server is not responding to status checks\033[0m"
fi

# Test the API format
echo -e "\n\033[1;36m=== Testing Audio Message Format ===\033[0m"

# Create a test message with both formats
echo -e "\033[1;36mℹ Testing correct format (audio at root level)\033[0m"
python3 -c '
import json
import base64
import websocket
import sys

# Create a simple audio test message with base64-encoded data
audio_data = base64.b64encode(b"test_audio_data").decode("utf-8")

# Correct format: audio at root level
correct_message = {
    "type": "input_audio_buffer.append",
    "audio": audio_data
}

try:
    # Connect to WebSocket
    ws = websocket.create_connection("ws://localhost:8080/realtime")
    print("\033[1;32m✓ Connected to WebSocket server\033[0m")

    # Send the message and get response
    ws.send(json.dumps(correct_message))
    print("\033[1;36mℹ Sent message with correct format\033[0m")

    # Give the server a moment to process and respond
    import time
    time.sleep(1)

    # Check if there is a response
    ws.settimeout(1)
    try:
        response = ws.recv()
        print("\033[1;36mℹ Received response: \033[0m")
        print(response[:200] + "..." if len(response) > 200 else response)

        # Check if it contains an error
        if "error" in response:
            print("\033[1;31m✗ Server returned an error\033[0m")
        else:
            print("\033[1;32m✓ No error in response\033[0m")
    except websocket.WebSocketTimeoutException:
        print("\033[1;36mℹ No immediate response (this may be normal)\033[0m")

    # Close connection
    ws.close()
    print("\033[1;32m✓ Test completed\033[0m")

except Exception as e:
    print(f"\033[1;31m✗ Error: {str(e)}\033[0m")
    sys.exit(1)
'

echo -e "\n\033[1;36m=== Opening Test Client ===\033[0m"
echo -e "\033[1;36mℹ You can open the test client at:\033[0m"
echo -e "\033[1;33mhttp://localhost:8000/test/realtime/\033[0m"
echo -e "or:"
echo -e "\033[1;33mhttp://localhost:8080/test/realtime/\033[0m"
