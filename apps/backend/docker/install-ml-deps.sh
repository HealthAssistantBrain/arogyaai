#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# install-ml-deps.sh — Platform-aware Python dependency installer
#
# Ensures that:
#   • ARM64 (Apple Silicon / Graviton) builds get CPU-only PyTorch wheels
#     and never download NVIDIA CUDA packages.
#   • x86_64 builds continue to use the default (CUDA-enabled) PyTorch wheels.
#
# Environment / build-args consumed:
#   TARGETPLATFORM  — set automatically by Docker BuildKit (e.g. linux/arm64)
#   ENABLE_GPU      — if "true" on x86_64, uses CUDA PyTorch index explicitly
#
# Usage (inside Dockerfile):
#   COPY apps/backend/docker/install-ml-deps.sh /tmp/install-ml-deps.sh
#   RUN bash /tmp/install-ml-deps.sh
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Pip reliability defaults ─────────────────────────────────────────────────
export PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT:-120}"
export PIP_RETRIES="${PIP_RETRIES:-5}"
export PIP_DISABLE_PIP_VERSION_CHECK=1

PIP_INSTALL="pip install --no-cache-dir --retries ${PIP_RETRIES} --timeout ${PIP_DEFAULT_TIMEOUT}"

# ── Detect platform ─────────────────────────────────────────────────────────
ARCH="${TARGETPLATFORM:-}"
if [ -z "$ARCH" ]; then
    # Fallback: detect from uname
    MACHINE=$(uname -m)
    case "$MACHINE" in
        aarch64|arm64) ARCH="linux/arm64" ;;
        x86_64|amd64)  ARCH="linux/amd64" ;;
        *)             ARCH="linux/$MACHINE" ;;
    esac
fi

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Platform-Aware ML Dependency Installer                     ║"
echo "║  Detected platform: ${ARCH}                                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# ── ARM64 path: CPU-only PyTorch, no NVIDIA packages ────────────────────────
if echo "$ARCH" | grep -qi "arm64\|aarch64"; then
    echo ""
    echo "▸ ARM64 detected — installing CPU-safe ML dependencies"
    echo "▸ NVIDIA CUDA packages will be excluded"
    echo ""

    TORCH_INDEX="https://download.pytorch.org/whl/cpu"

    # Step 1: Pre-install PyTorch (CPU-only) from the dedicated index.
    #         This satisfies the torch dependency for sentence-transformers,
    #         llama-index, etc. without pulling CUDA wheels.
    echo "── Step 1/4: Installing PyTorch (CPU) from ${TORCH_INDEX} ──"
    $PIP_INSTALL \
        torch torchvision torchaudio \
        --index-url "$TORCH_INDEX"

    # Step 2: Install onnxruntime (CPU) explicitly before fastembed can
    #         pull a GPU variant.
    echo "── Step 2/4: Installing onnxruntime (CPU) ──"
    $PIP_INSTALL onnxruntime

    # Step 3: Install packages that would transitively pull nvidia-* deps.
    #         We install them with --no-deps to prevent nvidia-nccl-cu12 etc.
    #         from being resolved. Their actual (non-NVIDIA) dependencies
    #         will be pulled in Step 4 via the full requirements install.
    echo "── Step 3/4: Pre-installing ML packages (--no-deps to block NVIDIA) ──"
    $PIP_INSTALL --no-deps \
        transformers \
        sentence-transformers \
        tokenizers \
        safetensors \
        huggingface-hub

    # Step 4: Install the full requirements.txt.
    #         torch + transformers + sentence-transformers are already satisfied.
    #         pip will only install their remaining (non-NVIDIA) deps.
    echo "── Step 4/4: Installing remaining requirements ──"
    $PIP_INSTALL -r /tmp/requirements.txt

    # Step 5: Post-install safety net — remove any nvidia packages that
    #         might have slipped through as transitive dependencies.
    echo ""
    echo "── Post-install: Removing any accidentally installed NVIDIA packages ──"
    NVIDIA_PKGS=$(pip list --format=freeze 2>/dev/null | grep -i "^nvidia" | cut -d= -f1 || true)
    if [ -n "$NVIDIA_PKGS" ]; then
        echo "  Removing: $NVIDIA_PKGS"
        echo "$NVIDIA_PKGS" | xargs pip uninstall -y 2>/dev/null || true
    else
        echo "  ✓ No NVIDIA packages found — clean install"
    fi

    echo ""
    echo "✓ ARM64 ML dependency installation complete"

# ── x86_64 path: default behavior (CUDA wheels if available) ────────────────
else
    echo ""
    echo "▸ x86_64 detected — installing with default PyTorch (CUDA-enabled)"
    echo ""

    ENABLE_GPU="${ENABLE_GPU:-false}"

    if [ "$ENABLE_GPU" = "true" ]; then
        echo "── GPU mode: installing PyTorch with CUDA 12.4 index ──"
        $PIP_INSTALL \
            torch torchvision torchaudio \
            --index-url "https://download.pytorch.org/whl/cu124"
        echo "── Installing remaining requirements ──"
        $PIP_INSTALL -r /tmp/requirements.txt
    else
        echo "── CPU mode (x86_64): installing requirements normally ──"
        # Even on x86_64 CPU-only, the default PyPI torch works fine
        # (it includes CUDA support but won't use it without a GPU).
        $PIP_INSTALL -r /tmp/requirements.txt
    fi

    echo ""
    echo "✓ x86_64 ML dependency installation complete"
fi

echo ""
echo "── Installed packages summary ──"
TOTAL_PKGS=$(pip list --format=freeze 2>/dev/null | wc -l | tr -d ' ')
echo "  Total packages installed: ${TOTAL_PKGS}"
echo ""
