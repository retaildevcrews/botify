FROM otel/opentelemetry-collector-contrib:0.100.0

COPY otel_config.yaml /etc/otelcol-config.yml

# Set the entrypoint if you need to override the default one
ENTRYPOINT ["/otelcol-contrib"]

CMD [ "--config", "/etc/otelcol-config.yml" ]