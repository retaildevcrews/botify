# Use recommended base image from Speech SDK Docs
# https://learn.microsoft.com/en-us/azure/ai-services/speech-service/quickstarts/setup-platform?tabs=linux%2Cdebian%2Cdotnetcli%2Cdotnet%2Cjre%2Cmaven%2Cnodejs%2Cmac%2Cpypi&pivots=programming-language-python#platform-requirements
FROM python:3.12-slim-bullseye

# Set the working directory
WORKDIR /code

# Install speechsdk requirements
RUN apt update && apt install -y ca-certificates libssl-dev libnss3 \
    && update-ca-certificates \
    && apt clean && rm -rf /var/lib/apt/lists/*

# Copy only necessary files
COPY pyproject.toml /code/
COPY poetry.lock /code/

# Install dependencies, no dev dependencies, clean up in the same layer
RUN pip install --no-cache-dir poetry==1.8 \
    && poetry config virtualenvs.create false \
    && poetry install --no-root --only main\
    && find /usr/local -type f -name '*.pyc' -delete

# Copy frontend code
COPY ./streamlit_app ./streamlit_app
COPY ./.streamlit ./.streamlit
COPY ./_additional_version_info.py ./_additional_version_info.py

# Expose the frontend port
EXPOSE 8000

ENV STREAMLIT_LOGGER_LEVEL=info

# Set the entrypoint to run the app
ENTRYPOINT ["python", "-m", "streamlit", "run", "streamlit_app/Home.py", "--server.port", "8000", "--server.address", "0.0.0.0"]
