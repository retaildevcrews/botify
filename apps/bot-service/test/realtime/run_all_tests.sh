#!/bin/bash

# Run all Botify realtime API tests
# This script runs through various test scenarios to verify the realtime API is working correctly

set -e
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Botify Realtime API Test Suite ===${NC}"
echo "This script will run a series of tests to verify the realtime API"
echo ""

# Get server info
DEFAULT_HOST="localhost"
DEFAULT_PORT="8080"

read -p "Enter host [default: $DEFAULT_HOST]: " HOST
HOST=${HOST:-$DEFAULT_HOST}

read -p "Enter port [default: $DEFAULT_PORT]: " PORT
PORT=${PORT:-$DEFAULT_PORT}

echo -e "\n${YELLOW}Step 1: Checking server status${NC}"
echo "Attempting to connect to http://$HOST:$PORT/realtime-status"

if command -v curl &> /dev/null; then
    if curl -s "http://$HOST:$PORT/realtime-status" -o /dev/null; then
        echo -e "${GREEN}Server is running and responding to HTTP requests${NC}"
    else
        echo -e "${RED}Server is not responding to HTTP requests${NC}"
        echo "Make sure the server is running and accessible"
        echo "Common issues:"
        echo "1. Server not started"
        echo "2. Firewall blocking access"
        echo "3. Wrong host/port"
        exit 1
    fi
else
    echo "curl not found, skipping HTTP check"
fi

echo -e "\n${YELLOW}Step 2: Running quick WebSocket test${NC}"
if [ -f "./quick_test.py" ]; then
    python3 ./quick_test.py --host "$HOST" --port "$PORT"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Quick test completed successfully${NC}"
    else
        echo -e "${RED}Quick test failed${NC}"
        echo "Check the output above for error details"
    fi
else
    echo -e "${RED}quick_test.py not found${NC}"
fi

echo -e "\n${YELLOW}Step 3: Running comprehensive test with error monitoring${NC}"
if [ -f "./test_with_error_monitoring.py" ]; then
    python3 ./test_with_error_monitoring.py --host "$HOST" --port "$PORT"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Comprehensive test completed${NC}"
    else
        echo -e "${RED}Comprehensive test encountered issues${NC}"
        echo "Check the output above for error details"
    fi
else
    echo -e "${RED}test_with_error_monitoring.py not found${NC}"
fi

echo -e "\n${YELLOW}Step 4: Starting HTML test client${NC}"
echo "Would you like to start the HTTP server for the HTML test client?"
read -p "Start server? (y/n) [default: y]: " START_SERVER
START_SERVER=${START_SERVER:-y}

if [[ $START_SERVER == "y" || $START_SERVER == "Y" ]]; then
    if [ -f "./serve_test_client.py" ]; then
        echo "Starting HTTP server on port 8000..."
        echo "Press Ctrl+C to stop the server when done"
        echo "Access the test client at: http://localhost:8000"
        python3 ./serve_test_client.py
    else
        echo -e "${RED}serve_test_client.py not found${NC}"
    fi
fi

echo -e "\n${YELLOW}All tests completed${NC}"
echo "For more detailed testing, refer to the README.md and TROUBLESHOOTING.md files"
