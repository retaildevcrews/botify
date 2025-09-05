# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies based on API-specific pyproject
COPY testapps/api/pyproject.toml /app/
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Copy only necessary application files (exclude tests and top-level data)
COPY testapps/api/src /app/apps/api/src
COPY testapps/api/menu /app/apps/api/menu
COPY testapps/api/prompt_templates /app/apps/api/prompt_templates

EXPOSE 8000

CMD ["uvicorn", "main:app", "--app-dir", "apps/api/src", "--host", "0.0.0.0", "--port", "8000"]
