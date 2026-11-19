# Deployment & Operations Runbook

## 1. Secrets Management
- All API keys (`GOOGLE_API_KEY`) and environment flags (`GEMINI_MODEL`, `LOG_LEVEL`) are injected via environment variables (`.env` locally or secret managers such as AWS Secrets Manager / GCP Secret Manager in cloud production).
- `.env` is strictly excluded via `.gitignore`.

## 2. Containerized Deployment (Docker Compose)
```bash
cp .env.example .env
# Add your GOOGLE_API_KEY in .env
docker-compose up --build