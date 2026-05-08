# syntax=docker/dockerfile:1.7
# ──────────────────────────────────────────────────────────────────────────────
# ArogyaAI Backend — Multi-stage, platform-aware Dockerfile
#
# Supports:
#   • Apple Silicon (ARM64) — CPU-only PyTorch, no NVIDIA packages
#   • NVIDIA GPU (x86_64)  — full CUDA-enabled PyTorch
#   • Linux x86_64 CPU     — default PyTorch (CUDA included but unused)
#
# Key design decisions:
#   1. TARGETPLATFORM is auto-injected by Docker BuildKit
#   2. install-ml-deps.sh detects arch and routes to CPU or GPU PyTorch index
#   3. constraints-arm64.txt blocks nvidia-* packages on ARM64
#   4. Multi-stage build separates build tools from runtime
#   5. requirements.txt is NEVER modified — constraints/overlays only
# ──────────────────────────────────────────────────────────────────────────────

# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 1: Builder — install all Python dependencies
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS builder

# ── Build arguments ──────────────────────────────────────────────────────────
ARG TARGETPLATFORM
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ARG CUSTOM_CA_CERT_B64=
ARG ENABLE_GPU=false

# ── Environment ──────────────────────────────────────────────────────────────
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
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=5 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TARGETPLATFORM=${TARGETPLATFORM} \
    ENABLE_GPU=${ENABLE_GPU}

WORKDIR /build

# ── System dependencies for building wheels ──────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        gcc \
        g++ \
        python3-dev \
        libgomp1 \
    && if [ -n "$CUSTOM_CA_CERT_B64" ]; then \
         printf '%s' "$CUSTOM_CA_CERT_B64" | base64 -d > /usr/local/share/ca-certificates/custom-proxy-ca.crt && \
         update-ca-certificates; \
       fi \
    && rm -rf /var/lib/apt/lists/*

# ── Copy dependency files ────────────────────────────────────────────────────
COPY apps/backend/requirements.txt /tmp/requirements.txt
COPY apps/backend/docker/constraints-arm64.txt /tmp/constraints-arm64.txt
COPY apps/backend/docker/install-ml-deps.sh /tmp/install-ml-deps.sh
RUN chmod +x /tmp/install-ml-deps.sh

# ── Install Python dependencies (platform-aware) ────────────────────────────
RUN --mount=type=cache,id=pip-cache,target=/root/.cache/pip \
    bash /tmp/install-ml-deps.sh


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 2: Runtime — lean image with only what's needed to run
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS runtime

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

# ── Runtime system dependencies ──────────────────────────────────────────────
# tesseract-ocr + poppler-utils for OCR pipeline
# libgomp1 for xgboost/lightgbm OpenMP support
# curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
        tzdata \
        curl \
        ca-certificates \
        libgomp1 \
        tesseract-ocr \
        poppler-utils \
    && if [ -n "$CUSTOM_CA_CERT_B64" ]; then \
         printf '%s' "$CUSTOM_CA_CERT_B64" | base64 -d > /usr/local/share/ca-certificates/custom-proxy-ca.crt && \
         update-ca-certificates; \
       fi \
    && rm -rf /var/lib/apt/lists/*

# ── Copy installed Python packages from builder ─────────────────────────────
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# ── Copy application source ─────────────────────────────────────────────────
COPY apps/backend/docker/backend-entrypoint.sh /usr/local/bin/backend-entrypoint
RUN chmod +x /usr/local/bin/backend-entrypoint
COPY . /app
ENV PYTHONPATH=/app:/app/apps/backend
WORKDIR /app/apps/backend

ENTRYPOINT ["/usr/local/bin/backend-entrypoint"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
