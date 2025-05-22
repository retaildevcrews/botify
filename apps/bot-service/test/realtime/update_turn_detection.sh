#!/bin/bash

# Script to update the turn detection type to address the end-of-utterance detection issue

CREDENTIALS_FILE="/workspaces/botify/apps/credentials.env"

# Check if file exists
if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "Error: $CREDENTIALS_FILE not found"
    exit 1
fi

# Check the current value
CURRENT_VALUE=$(grep "AZURE_SPEECH_SERVICES_TURN_DETECTION_TYPE" "$CREDENTIALS_FILE" | cut -d '=' -f2 | tr -d '"')

echo "Current turn detection type: ${CURRENT_VALUE:-not set}"
echo "Available turn detection types:"
echo "  - server_vad (basic, no end-of-utterance support)"
echo "  - azure_semantic_vad (recommended, with end-of-utterance support)"
echo "  - azure_semantic_vad_en (English only, with end-of-utterance support)"
echo "  - server_sd (simple silence detection)"
echo "  - azure_semantic_vad_multilingual (multilingual support)"
echo "  - none (no turn detection)"

# Prompt for change
read -p "Would you like to change the turn detection type to 'azure_semantic_vad' to enable end-of-utterance detection? (y/n): " CHOICE

if [ "$CHOICE" = "y" ] || [ "$CHOICE" = "Y" ]; then
    # Make a backup of the file
    cp "$CREDENTIALS_FILE" "${CREDENTIALS_FILE}.backup"    # Check if the variable exists in the file
    if grep -q "AZURE_SPEECH_SERVICES_TURN_DETECTION_TYPE" "$CREDENTIALS_FILE"; then
        # Update existing variable
        sed -i 's/AZURE_SPEECH_SERVICES_TURN_DETECTION_TYPE="[^"]*"/AZURE_SPEECH_SERVICES_TURN_DETECTION_TYPE="azure_semantic_vad"/' "$CREDENTIALS_FILE"
    else
        # Add the variable if it doesn't exist
        echo 'AZURE_SPEECH_SERVICES_TURN_DETECTION_TYPE="azure_semantic_vad"' >> "$CREDENTIALS_FILE"
    fi

    echo "Updated $CREDENTIALS_FILE with AZURE_SPEECH_SERVICES_TURN_DETECTION_TYPE=\"azure_semantic_vad\""
    echo "A backup was created at ${CREDENTIALS_FILE}.backup"

    # Prompt to restart services
    read -p "Would you like to restart the botify services now? (y/n): " RESTART
    if [ "$RESTART" = "y" ] || [ "$RESTART" = "Y" ]; then
        cd /workspaces/botify/apps
        docker-compose restart bot-service
        echo "Services restarted. Try connecting again with the test client."
    else
        echo "Remember to restart the services with 'docker-compose restart bot-service' for changes to take effect."
    fi
else
    echo "No changes made to configuration."
fi
