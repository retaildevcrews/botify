#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Botify Realtime Format Test Tool ===${NC}"

# Path to the test client directory
TEST_CLIENT_DIR="/workspaces/botify/apps/bot-service/test/realtime"
PORT=8090

# Check if the port is specified
if [ ! -z "$1" ]; then
    PORT=$1
fi

# Create a custom page to test the current format
echo -e "${YELLOW}Creating test page with current format...${NC}"
cat > "${TEST_CLIENT_DIR}/format_test.html" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Simple Botify Realtime Format Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; max-width: 800px; }
        button { padding: 10px; margin: 5px; }
        pre { background: #f5f5f5; padding: 10px; border-radius: 4px; }
        #status, #messages {
            margin: 10px 0;
            padding: 10px;
            border: 1px solid #ccc;
            min-height: 20px;
        }
        .error { color: red; }
        .success { color: green; }
    </style>
</head>
<body>
    <h1>Simple Botify Realtime Format Test</h1>
    <div>
        <button id="connect">Connect</button>
        <button id="disconnect" disabled>Disconnect</button>
        <button id="testFormat" disabled>Test New Format</button>
        <button id="testOldFormat" disabled>Test Old Format (Should Fail)</button>
    </div>
    <div id="status">Disconnected</div>
    <h3>Messages:</h3>
    <div id="messages"></div>

    <h3>Correct Format:</h3>
    <pre>{
  "type": "input_audio_buffer.append",
  "audio": "base64EncodedAudioData"
}</pre>

    <h3>Old Format (No Longer Supported):</h3>
    <pre>{
  "type": "input_audio_buffer.append",
  "data": {
    "audio": "base64EncodedAudioData"
  }
}</pre>

    <script>
        let socket;
        const statusEl = document.getElementById('status');
        const messagesEl = document.getElementById('messages');
        const connectBtn = document.getElementById('connect');
        const disconnectBtn = document.getElementById('disconnect');
        const testFormatBtn = document.getElementById('testFormat');
        const testOldFormatBtn = document.getElementById('testOldFormat');

        // Event listeners
        connectBtn.addEventListener('click', connect);
        disconnectBtn.addEventListener('click', disconnect);
        testFormatBtn.addEventListener('click', () => testFormat(false));
        testOldFormatBtn.addEventListener('click', () => testFormat(true));

        function connect() {
            try {
                statusEl.textContent = 'Connecting...';
                socket = new WebSocket('ws://localhost:8080/realtime');

                socket.onopen = () => {
                    statusEl.textContent = 'Connected';
                    statusEl.className = 'success';
                    log('✅ WebSocket connection established');
                    connectBtn.disabled = true;
                    disconnectBtn.disabled = false;
                    testFormatBtn.disabled = false;
                    testOldFormatBtn.disabled = false;
                };

                socket.onmessage = (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        const messageType = message.type || 'unknown';

                        if (message.error) {
                            log('❌ ERROR: ' + JSON.stringify(message.error), 'error');
                        } else {
                            log('📩 Received: ' + messageType);
                            console.log('Received message:', message);
                        }
                    } catch (e) {
                        log('❌ Error parsing message: ' + e.message, 'error');
                    }
                };

                socket.onclose = (event) => {
                    statusEl.textContent = 'Disconnected';
                    statusEl.className = '';
                    log(`🔌 Connection closed: ${event.code} ${event.reason || ''}`);
                    connectBtn.disabled = false;
                    disconnectBtn.disabled = true;
                    testFormatBtn.disabled = true;
                    testOldFormatBtn.disabled = true;
                };

                socket.onerror = (error) => {
                    statusEl.className = 'error';
                    log('❌ WebSocket error', 'error');
                };
            } catch (e) {
                log('❌ Error creating WebSocket: ' + e.message, 'error');
            }
        }

        function disconnect() {
            if (socket) {
                socket.close();
            }
        }

        function testFormat(useOldFormat) {
            if (!socket || socket.readyState !== WebSocket.OPEN) {
                log('❌ WebSocket not connected', 'error');
                return;
            }

            // Create a test message
            const testAudio = btoa('test_audio_data_' + Date.now());
            let message;

            if (useOldFormat) {
                // Old format (no longer supported)
                message = {
                    type: 'input_audio_buffer.append',
                    data: {
                        audio: testAudio
                    }
                };
                log('📤 Sending with OLD format (should fail)');
            } else {
                // New format
                message = {
                    type: 'input_audio_buffer.append',
                    audio: testAudio
                };
                log('📤 Sending with NEW format');
            }

            console.log('Sending message:', message);
            socket.send(JSON.stringify(message));
        }

        function log(message, type = '') {
            const el = document.createElement('div');
            if (type) el.className = type;
            el.textContent = `${new Date().toLocaleTimeString()} - ${message}`;
            messagesEl.appendChild(el);
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }
    </script>
</body>
</html>
EOF

echo -e "${GREEN}Created test page at:${NC}"
echo -e "${BLUE}${TEST_CLIENT_DIR}/format_test.html${NC}"

# Offer to open it in the browser
echo -e "${YELLOW}Would you like to open the test page in your browser? (y/n)${NC}"
read -r answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
    if [ -n "$BROWSER" ]; then
        "$BROWSER" "${TEST_CLIENT_DIR}/format_test.html"
    else
        echo -e "${YELLOW}No browser found. You can open the file at:${NC}"
        echo -e "${BLUE}file://${TEST_CLIENT_DIR}/format_test.html${NC}"
    fi
fi

echo -e "${YELLOW}You can also start a test server with:${NC}"
echo -e "${BLUE}python3 ${TEST_CLIENT_DIR}/serve_test_client.py${NC}"

echo -e "${GREEN}Done!${NC}"
