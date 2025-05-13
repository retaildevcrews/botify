FROM python:3.12-slim AS builder

# Set a working directory
WORKDIR /code

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8

# Copy only necessary files
COPY pyproject.toml /code/
COPY poetry.lock /code/

# Install dependencies, no dev dependencies, clean up in the same layer
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --only main && \
    find /usr/local -type f -name '*.pyc' -delete

# Start from a clean, minimal base image
FROM python:3.12.8-slim

# Set the working directory
WORKDIR /code

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/opentelemetry* /usr/local/bin/

# Download the spaCy English language model for Presidio image redactor.
# Install the uvicorn server.
# Install Open Telemetry auto-instrumentation dependencies.
RUN python -m spacy download en_core_web_sm && \
    pip install --no-deps --ignore-installed --no-cache-dir uvicorn && \
    opentelemetry-bootstrap -a install

ENV OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true

# Copy bot-service code
COPY ./api ./api
COPY ./app ./app
COPY ./botify_langchain ./botify_langchain
COPY ./common ./common
COPY ./prompts ./prompts
COPY ./log_config.yaml ./log_config.yaml
COPY ./pyproject.toml ./pyproject.toml
COPY ./_additional_version_info.py ./_additional_version_info.py

# Expose the bot-service port
EXPOSE 8080
ENV LOG_LEVEL=INFO

# Copy entrypoint script and set to executable
COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set the entrypoint to run the app
ENTRYPOINT ["/entrypoint.sh"]
