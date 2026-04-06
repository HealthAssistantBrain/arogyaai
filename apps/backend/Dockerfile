FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y tzdata curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=10 CMD curl --fail --silent --show-error http://localhost:8000/health || exit 1
