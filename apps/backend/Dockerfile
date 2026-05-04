# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ARG CUSTOM_CA_CERT_B64=

ENV HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    NO_PROXY=${NO_PROXY} \
    http_proxy=${HTTP_PROXY} \
    https_proxy=${HTTPS_PROXY} \
    no_proxy=${NO_PROXY} \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends tzdata curl ca-certificates libgomp1 tesseract-ocr poppler-utils && \
    if [ -n "$CUSTOM_CA_CERT_B64" ]; then \
      printf '%s' "$CUSTOM_CA_CERT_B64" | base64 -d > /usr/local/share/ca-certificates/custom-proxy-ca.crt && \
      update-ca-certificates; \
    fi && \
    rm -rf /var/lib/apt/lists/*

COPY apps/backend/requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt
COPY apps/backend/docker/backend-entrypoint.sh /usr/local/bin/backend-entrypoint
RUN chmod +x /usr/local/bin/backend-entrypoint
COPY . /app
ENV PYTHONPATH=/app:/app/apps/backend
WORKDIR /app/apps/backend

ENTRYPOINT ["/usr/local/bin/backend-entrypoint"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
