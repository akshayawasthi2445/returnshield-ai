# ReturnShield AI 🛡️

AI-Powered Returns & Exchange Autopilot for Shopify

## What It Does

ReturnShield AI helps Shopify merchants reduce returns and retain revenue by:
- **Predicting** which orders are likely to be returned (AI risk scoring)
- **Preventing** returns with smart, data-driven size guides
- **Converting** returns into exchanges to retain revenue
- **Analyzing** return patterns to improve your product catalog

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python 3.11 + FastAPI |
| Database | PostgreSQL 16 |
| Cache/Queue | Redis 7 + Celery |
| ML | XGBoost + scikit-learn |
| Frontend | App Bridge + Polaris (embedded Shopify admin) |
| Auth | Shopify OAuth2 + Session Tokens (JWT) |

## Quick Start

### 1. Clone & Configure

```bash
cp .env.example .env
# Edit .env with your Shopify API credentials
```

### 2. Run with Docker

```bash
docker compose up -d
```

This starts:
- **Web server** at `http://localhost:8000`
- **PostgreSQL** at `localhost:5432`
- **Redis** at `localhost:6379`
- **Celery worker** for background tasks
- **Celery beat** for scheduled jobs

### 3. Run Locally (Development)

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Start the server
uvicorn app.main:app --reload --port 8000
```

### 4. Database Migrations

```bash
# Initialize Alembic (first time)
alembic init migrations

# Create a migration
alembic revision --autogenerate -m "Initial models"

# Run migrations
alembic upgrade head
```

## API Documentation

With the server running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Project Structure

```
returnshield-ai/
├── app/
│   ├── main.py           # FastAPI entrypoint
│   ├── config.py          # App configuration
│   ├── database.py        # SQLAlchemy setup
│   ├── dependencies.py    # FastAPI dependencies
│   ├── auth/              # OAuth + session tokens
│   ├── api/v1/            # REST API routes
│   ├── models/            # SQLAlchemy models
│   ├── services/          # Business logic
│   ├── ml/                # ML models
│   ├── workers/           # Celery tasks
│   ├── templates/         # Jinja2 + App Bridge
│   └── static/            # JS/CSS
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## License

MIT
