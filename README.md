# ArogyaAI Monorepo

Welcome to the ArogyaAI Monorepo. This repository contains the Frontend, Backend, and several microservices used in the production architecture.

## Folder Structure

- `apps/frontend`: Existing React application.
- `apps/backend`: Main FastAPI backend orchestrator.
- `services/`: Specialized FastAPI microservices (auth, data, prediction, rag).
- `shared/`: Shared utilities and type definitions.
- `infra/`: Docker, Nginx, and system scripting tools.

## How to Run Frontend (Standalone)

```bash
cd apps/frontend
npm install
npm run dev
```

The frontend is completely unchanged and runs independently just as before.

## How to Run Backend

```bash
cd apps/backend
pip install -r requirements.txt
uvicorn main:app --reload
```

## How to Run Docker (Full Stack)

Make sure Docker Desktop is running.

```bash
docker-compose up --build
```

If your network uses SSL inspection or a proxy that injects its own certificate, export the root CA once before building:

```bash
export CUSTOM_CA_CERT_B64="$(base64 < /path/to/your-root-ca.crt | tr -d '\n')"
docker-compose up --build
```

The Python service images will install that certificate into the container trust store during build, which avoids `SSLCertVerificationError` failures when installing dependencies from PyPI.

## For Pipeline Developers

See: README_PIPELINES.md
