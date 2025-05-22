#!/bin/bash

# Script to rebuild and restart the bot-service with WebSocket support

echo "Stopping current services..."
cd /workspaces/botify/apps
docker-compose down

echo "Rebuilding bot-service container with WebSocket support..."
docker-compose build bot-service

echo "Starting services..."
docker-compose up -d

echo "Waiting for services to start..."
sleep 5

echo "Checking bot-service logs for WebSocket support..."
docker-compose logs bot-service | grep -i websocket

echo "Services are now running. You can test the WebSocket connection using the test client."
echo "If you encounter any issues, check the logs with: docker-compose logs -f bot-service"
