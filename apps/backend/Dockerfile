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
    PIP_CERT=/etc/ssl/certs/ca-certificates.crt

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends tzdata curl ca-certificates && \
    if [ -n "$CUSTOM_CA_CERT_B64" ]; then \
      printf '%s' "$CUSTOM_CA_CERT_B64" | base64 -d > /usr/local/share/ca-certificates/custom-proxy-ca.crt && \
      update-ca-certificates; \
    fi && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY docker/backend-entrypoint.sh /usr/local/bin/backend-entrypoint
RUN chmod +x /usr/local/bin/backend-entrypoint

ENTRYPOINT ["/usr/local/bin/backend-entrypoint"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=12 CMD curl --fail --silent --show-error http://localhost:8000/health || exit 1
