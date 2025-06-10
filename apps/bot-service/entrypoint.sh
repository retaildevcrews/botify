#!/bin/bash

if [[ -z "${OPEN_TELEMETRY_COLLECTOR_ENDPOINT}" ]]; then
  COMMAND=("uvicorn" "api.server:app" "--host" "0.0.0.0" "--port" "8080" "--log-config" "./log_config.yaml" "--ws" "websockets")
else
  COMMAND=("opentelemetry-instrument" "--exporter_otlp_protocol" "http/protobuf" "--traces_exporter" "otlp" "--metrics_exporter" "otlp" "--logs_exporter" "otlp" "--service_name" "rag-example.bot-service" "--exporter_otlp_endpoint" "$OPEN_TELEMETRY_COLLECTOR_ENDPOINT" "uvicorn" "api.server:app" "--host" "0.0.0.0" "--port" "8080" "--log-config" "./log_config.yaml" "--proxy-headers" "--forwarded-allow-ips" "*" "--ws" "websockets")
fi

# Run with exec to handle SIGINT (shutdown signals)
exec "${COMMAND[@]}" "$@"
