#!/bin/bash

# Quick script to launch the test client in the default browser

# Default browser command
BROWSER_CMD="$BROWSER"

# If $BROWSER is not set, try some common browsers
if [ -z "$BROWSER_CMD" ]; then
    if command -v firefox &> /dev/null; then
        BROWSER_CMD="firefox"
    elif command -v google-chrome &> /dev/null; then
        BROWSER_CMD="google-chrome"
    elif command -v chromium-browser &> /dev/null; then
        BROWSER_CMD="chromium-browser"
    elif command -v brave-browser &> /dev/null; then
        BROWSER_CMD="brave-browser"
    elif command -v microsoft-edge &> /dev/null; then
        BROWSER_CMD="microsoft-edge"
    else
        echo "No browser detected. Please open the file manually:"
        echo "/workspaces/botify/apps/bot-service/test/realtime/index.html"
        exit 1
    fi
fi

# Check server status first
BOT_SERVICE_STATUS=$(curl -s http://localhost:8080/realtime-status || echo '{"status":"error"}')

if [[ "$BOT_SERVICE_STATUS" == *"error"* ]]; then
    echo "Warning: Bot service does not appear to be running or is not responding."
    echo "You may want to check if the container is running with: docker-compose ps"

    read -p "Do you still want to open the test client? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
        exit 0
    fi
fi

# Launch the browser with the test client
echo "Launching test client in $BROWSER_CMD..."
"$BROWSER_CMD" "/workspaces/botify/apps/bot-service/test/realtime/index.html"
