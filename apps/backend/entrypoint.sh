#!/bin/bash

if [[ -z "${OPEN_TELEMETRY_COLLECTOR_ENDPOINT}" ]]; then
  COMMAND="uvicorn app.server:app --host 0.0.0.0 --port 8080 --log-config ./log_config.yaml"
else
  COMMAND="opentelemetry-instrument --exporter_otlp_protocol http/protobuf --traces_exporter otlp --metrics_exporter otlp --logs_exporter otlp --service_name rag-example.backend --exporter_otlp_endpoint $OPEN_TELEMETRY_COLLECTOR_ENDPOINT uvicorn app.server:app --host 0.0.0.0 --port 8080 --log-config ./log_config.yaml"
fi

# Run with exec to handle SIGINT (shutdown signals)
exec $COMMAND "$@"
