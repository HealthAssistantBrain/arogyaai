import os

dirs = [
    "apps/backend/routes",
    "apps/backend/services",
    "apps/backend/models",
    "apps/backend/db",
    "services/auth-service",
    "services/data-service",
    "services/prediction-service",
    "services/rag-service",
    "shared/types",
    "shared/utils",
    "infra/docker",
    "infra/nginx",
    "infra/scripts",
]

for d in dirs:
    os.makedirs(d, exist_ok=True)

# Generate apps/backend/main.py
backend_main = """from fastapi import FastAPI

app = FastAPI(title="ArogyaAI Main Backend")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "backend"}

@app.get("/auth")
def auth_mock():
    return {"message": "Auth route initialized"}

@app.get("/user")
def user_mock():
    return {"message": "User route initialized"}

@app.get("/data")
def data_mock():
    return {"message": "Data route initialized"}
"""
with open("apps/backend/main.py", "w") as f: f.write(backend_main)

# Minimal services
for svc in ["auth", "data", "prediction", "rag"]:
    code = f"""from fastapi import FastAPI

app = FastAPI(title="ArogyaAI {svc.capitalize()} Service")

@app.get("/health")
def health_check():
    return {{"status": "ok", "service": "{svc}-service"}}
"""
    with open(f"services/{svc}-service/main.py", "w", encoding="utf-8") as f: f.write(code)
    
    dockerfile = f"""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
    with open(f"services/{svc}-service/Dockerfile", "w", encoding="utf-8") as f: f.write(dockerfile)
    with open(f"services/{svc}-service/requirements.txt", "w", encoding="utf-8") as f: f.write("fastapi\\nuvicorn\\n")

# Backend Dockerfile, requirements
with open(f"apps/backend/requirements.txt", "w", encoding="utf-8") as f: f.write("fastapi\\nuvicorn\\n")
with open(f"apps/backend/Dockerfile", "w", encoding="utf-8") as f: f.write(dockerfile)

# docker-compose.yml
dc = """version: '3.8'

services:
  frontend:
    build: 
      context: ./apps/frontend
      dockerfile: Dockerfile
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:8000/api
    networks:
      - arogyaai_net

  backend:
    build: ./apps/backend
    ports:
      - "8000:8000"
    networks:
      - arogyaai_net
    depends_on:
      - postgres
      - redis

  auth-service:
    build: ./services/auth-service
    networks:
      - arogyaai_net

  data-service:
    build: ./services/data-service
    networks:
      - arogyaai_net

  prediction-service:
    build: ./services/prediction-service
    networks:
      - arogyaai_net

  rag-service:
    build: ./services/rag-service
    networks:
      - arogyaai_net

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: arogyaai
    ports:
      - "5432:5432"
    networks:
      - arogyaai_net

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - arogyaai_net

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    networks:
      - arogyaai_net

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./infra/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - frontend
      - backend
    networks:
      - arogyaai_net

networks:
  arogyaai_net:
    driver: bridge
"""
with open("docker-compose.yml", "w", encoding="utf-8") as f: f.write(dc)

# nginx
nginx = """events {}

http {
    upstream frontend {
        server frontend:5173;
    }
    upstream backend {
        server backend:8000;
    }

    server {
        listen 80;

        location /api/ {
            proxy_pass http://backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location / {
            proxy_pass http://frontend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            # For Vite HMR
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
"""
with open("infra/nginx/nginx.conf", "w", encoding="utf-8") as f: f.write(nginx)

# Make new .gitignore. Rename current one to FRONTEND_GITIGNORE so it moves safely.
git = """node_modules/
__pycache__/
*.pyc
.env
dist/
build/
.DS_Store
"""
with open("ROOT_GITIGNORE", "w", encoding="utf-8") as f: f.write(git)

# Readme
readme = """# ArogyaAI Monorepo

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
"""
with open("MONOREPO_README.md", "w", encoding="utf-8") as f: f.write(readme)

# Frontend Dockerfile
front_dk = """FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Development server for Docker-Compose interoperability
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
"""
with open("frontend_dockerfile.txt", "w", encoding="utf-8") as f: f.write(front_dk)

# Create safe migration script
ps1 = """$ErrorActionPreference = "Stop"
Write-Host "Migrating Frontend into Apps/Frontend..."

New-Item -ItemType Directory -Force -Path "apps\\frontend" | Out-Null

$excludeList = @(
    "apps", "services", "shared", "infra", "docker-compose.yml", 
    "MONOREPO_README.md", "frontend_dockerfile.txt", "ROOT_GITIGNORE", 
    ".git", "scaffold.py", "migrate_frontend.ps1"
)

# Move all root contents (the frontend) into apps/frontend
Get-ChildItem -Path . | Where-Object { $_.Name -notin $excludeList } | ForEach-Object {
    Move-Item -Path $_.FullName -Destination "apps\\frontend" -Force
}

# Attach Dockerfile to the frontend
Move-Item -Path "frontend_dockerfile.txt" -Destination "apps\\frontend\\Dockerfile" -Force

# Rename Monorepo Root Files
Rename-Item -Path "MONOREPO_README.md" -NewName "README.md" -Force
Rename-Item -Path "ROOT_GITIGNORE" -NewName ".gitignore" -Force

Write-Host "Migration Complete! Frontend is safely encapsulated."
Write-Host "You can now run 'docker-compose up --build' to test."
"""
with open("migrate_frontend.ps1", "w", encoding="utf-8") as f: f.write(ps1)

print("Scaffold Generation Completed.")
