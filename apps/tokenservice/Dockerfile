FROM python:3.12.4-slim as builder

# Set a working directory
WORKDIR /code

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8

# Copy only necessary files
COPY pyproject.toml /code/

# Install dependencies, no dev dependencies, clean up in the same layer
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --only main && \
    find /usr/local -type f -name '*.pyc' -delete

# Start from a clean, minimal base image
FROM python:3.12.4-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

ENV LOG_LEVEL=INFO

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Install uvicorn
RUN pip install --no-deps --ignore-installed --no-cache-dir uvicorn

WORKDIR /app
COPY . /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser
EXPOSE 8000

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
