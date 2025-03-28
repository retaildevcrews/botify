#!/bin/sh

# Create a runtime environment file for React
if [ ! -z "$REACT_APP_API_URL" ]; then
  echo "Setting REACT_APP_API_URL to $REACT_APP_API_URL"
  echo "window.env = { REACT_APP_API_URL: '$REACT_APP_API_URL' };" > /usr/share/nginx/html/env-config.js
else
  echo "REACT_APP_API_URL not set, using default"
  echo "window.env = { REACT_APP_API_URL: 'http://localhost:8000' };" > /usr/share/nginx/html/env-config.js
fi

# Execute CMD
exec "$@"