# PharmaRepurpose Assistant

An agentic AI platform for pharmaceutical drug repurposing analysis, featuring a Master Agent orchestrating domain-specific Worker Agents to provide comprehensive market intelligence, clinical insights, and regulatory analysis.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend (Vercel)                   │
│  Query Builder │ Progress Dashboard │ Results View │ Admin       │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API / WebSocket
┌────────────────────────────┴────────────────────────────────────┐
│                   FastAPI Backend (Render)                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Master Agent Orchestrator                   │   │
│  │   • Query normalization & caching                       │   │
│  │   • Parallel worker task dispatch (Celery)              │   │
│  │   • Result aggregation & scoring                        │   │
│  │   • LLM routing (Bolt/OpenAI/Anthropic)                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                             │                                    │
│  ┌──────────────────────────┴──────────────────────────────┐   │
│  │              Celery Worker Agents                        │   │
│  ├────────────┬────────────┬────────────┬─────────────────┤   │
│  │  Clinical  │   Patent   │   IQVIA    │      EXIM       │   │
│  │   Trials   │ Landscape  │  Insights  │     Trends      │   │
│  ├────────────┼────────────┼────────────┼─────────────────┤   │
│  │  Internal  │    Web     │   Report   │                 │   │
│  │    Docs    │   Intel    │ Generator  │                 │   │
│  └────────────┴────────────┴────────────┴─────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────────┐
│         Infrastructure & Data Layer                              │
│  Redis (Broker/Cache) │ PostgreSQL │ S3/MinIO │ Prometheus      │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Key Features

### Intelligent LLM Routing
- **Sensitive Data**: Automatically routes internal documents and sensitive content to Bolt internal LLM
- **Public Data**: Uses OpenAI/Anthropic for general web intelligence and creative synthesis
- **Grounding Checker**: Ensures all factual claims are backed by references with confidence scoring
- **Automatic Fallback**: Falls back from OpenAI to Anthropic if quota exceeded

### Worker Agents
1. **Clinical Trials Agent**: Searches trials databases for relevant studies and phase data
2. **Patent Landscape Agent**: Analyzes patent filings, FTO (Freedom to Operate), IP risk
3. **IQVIA Insights Agent**: Market size, CAGR, competitive landscape analysis
4. **EXIM Trends Agent**: Import/export dependencies, supply chain analysis
5. **Internal Knowledge Agent**: Processes proprietary documents with strict privacy
6. **Web Intelligence Agent**: Aggregates publications, guidelines, news
7. **Report Generator Agent**: Creates PDF/Excel/PPT reports with visualizations

### Operational Excellence
- **Circuit Breaker**: Degrades gracefully when external APIs fail (5 failures → 10min cooldown)
- **Rate Limiting**: Token bucket per origin (default 100 calls/min)
- **Caching**: Redis-backed with 24h TTL for identical queries
- **Retry Logic**: Exponential backoff (3 retries, 2^n seconds)
- **Idempotency**: Safe retries with idempotency keys
- **Monitoring**: Prometheus metrics on `/metrics` endpoint

### Security & Compliance
- **JWT Authentication**: Role-based access control (Admin/Researcher/Viewer)
- **PII Redaction**: Automatic detection and redaction before external API calls
- **Audit Logs**: Immutable logs of all queries and results
- **Secrets Management**: Environment-based configuration
- **HTTPS/CORS**: Production-ready security headers

## 📋 Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- (Optional) Render & Vercel accounts for cloud deployment

## 🛠️ Local Development Setup

### 1. Clone and Configure

```bash
git clone <repository>
cd pharma-repurpose

# Backend setup
cd backend
cp .env.template .env
# Edit .env with your configuration
```

### 2. Start Infrastructure with Docker Compose

```bash
# From project root
docker-compose up -d
```

This starts:
- PostgreSQL database (port 5432)
- Redis (port 6379)
- MinIO (port 9000)
- Mock external services (ports 8001-8005)

### 3. Run Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start Celery worker
celery -A app.tasks worker --loglevel=INFO
```

### 4. Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at `http://localhost:5173`

### 5. Run Demo Script

```bash
chmod +x scripts/demo.sh
./scripts/demo.sh
```

## 🔑 Environment Variables

### Critical Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `JWT_SECRET_KEY` | Secret for JWT tokens | Yes |
| `BOLT_LLM_API_KEY` | Bolt internal LLM API key | For sensitive data |
| `OPENAI_API_KEY` | OpenAI API key | For general LLM |
| `ANTHROPIC_API_KEY` | Anthropic API key | Fallback LLM |
| `S3_ACCESS_KEY` | S3 or MinIO access key | Yes |
| `S3_SECRET_KEY` | S3 or MinIO secret key | Yes |

See `.env.template` for complete list.

## 📡 API Documentation

### Authentication

```bash
# Register user
POST /api/v1/auth/register
{
  "email": "researcher@pharma.com",
  "password": "secure_password",
  "role": "researcher"
}

# Login
POST /api/v1/auth/login
{
  "email": "researcher@pharma.com",
  "password": "secure_password"
}
# Returns: {"access_token": "...", "token_type": "bearer"}
```

### Query Submission

```bash
POST /api/v1/master/query
Authorization: Bearer <token>
{
  "molecule": "Metformin",
  "indications": ["Cancer", "Alzheimer's"],
  "countries": ["US", "IN"],
  "sensitive": true,
  "internal_doc_ids": ["doc-123"],
  "report_format": "pdf"
}

# Returns 202 Accepted:
{
  "query_id": "uuid",
  "status": "processing",
  "progress_url": "/api/v1/master/status/uuid"
}
```

### Status Check

```bash
GET /api/v1/master/status/{query_id}
Authorization: Bearer <token>

# Returns:
{
  "query_id": "uuid",
  "status": "completed",
  "molecule": "Metformin",
  "worker_results": [...],
  "opportunity_score": 0.78,
  "summary": {...},
  "report_url": "https://s3.../report.pdf"
}
```

## 🎯 Sample Queries

### Query 1: Metformin for Cancer
```json
{
  "molecule": "Metformin",
  "indications": ["Non-small cell lung cancer", "Breast cancer"],
  "countries": ["US", "IN"],
  "sensitive": false
}
```

### Query 2: Aspirin for Alzheimer's (with internal docs)
```json
{
  "molecule": "Aspirin",
  "indications": ["Alzheimer's disease", "Dementia"],
  "countries": ["US", "GB", "JP"],
  "sensitive": true,
  "internal_doc_ids": ["internal-research-2024-01"]
}
```

### Query 3: Sildenafil for Pulmonary Hypertension
```json
{
  "molecule": "Sildenafil",
  "indications": ["Pulmonary arterial hypertension"],
  "countries": ["US", "DE", "BR"]
}
```

## ☁️ Cloud Deployment

### Render Backend Deployment

1. Create new Web Service:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: Add all variables from `.env.template`

2. Create Background Worker Service:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `celery -A app.tasks worker --loglevel=INFO`
   - **Environment**: Same as web service

3. Add PostgreSQL database (managed)
4. Add Redis (managed or Upstash)
5. Configure S3 bucket for reports

### Vercel Frontend Deployment

```bash
cd frontend
vercel --prod
```

Set environment variable:
- `VITE_API_BASE_URL`: Your Render backend URL

## 🧪 Testing

### Unit Tests
```bash
cd backend
pytest tests/ -v --cov=app
```

### Integration Tests
```bash
pytest tests/integration/ -v
```

### Load Testing
```bash
# Install k6 (https://k6.io/)
k6 run scripts/load_test.js
```

Simulates 50 concurrent users making queries.

## 📊 Monitoring

### Prometheus Metrics

Available at `/metrics`:
- `query_requests_total`: Total queries received
- `worker_task_duration_seconds`: Worker execution time
- `llm_calls_total`: LLM API calls by provider
- `circuit_breaker_state`: Circuit breaker status per service
- `cache_hit_ratio`: Cache effectiveness

### Grafana Dashboard

Import `monitoring/grafana-dashboard.json` for:
- Query throughput and latency
- Worker health status
- LLM usage and costs
- Cache performance
- Queue depth

### Logs

Structured JSON logs to stdout:
```json
{
  "timestamp": "2024-...",
  "level": "INFO",
  "service": "master",
  "query_id": "...",
  "message": "Query completed",
  "duration_ms": 1523
}
```

## 🎨 Frontend Features

- **Query Builder**: Intuitive form with autocomplete for molecules
- **Progress Dashboard**: Real-time worker status with WebSocket updates
- **Results View**: Interactive tables, charts (Chart.js), downloadable CSV
- **Report Download**: One-click PDF/Excel/PPT download
- **Admin Panel**: View logs, queue metrics, system health

## 🏗️ Project Structure

```
pharma-repurpose/
├── backend/
│   ├── app/
│   │   ├── routers/          # API endpoints
│   │   ├── models/           # SQLAlchemy models
│   │   ├── services/         # Business logic
│   │   ├── workers/          # Celery worker agents
│   │   ├── utils/            # Utilities (auth, cache, etc.)
│   │   ├── config.py         # Settings
│   │   └── main.py           # FastAPI app
│   ├── tests/                # Test suite
│   ├── alembic/              # DB migrations
│   ├── data/                 # Sample internal docs
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Page components
│   │   ├── services/         # API clients
│   │   └── types/            # TypeScript types
│   ├── package.json
│   └── vite.config.ts
├── mocks/                    # Mock external services
├── scripts/                  # Demo & utility scripts
├── monitoring/               # Grafana dashboards
├── .github/workflows/        # CI/CD
├── docker-compose.yml
└── README.md
```

## 🤝 Contributing

This is a hackathon project. Key areas for enhancement:
- Additional worker agents (FDA approvals, social media sentiment)
- Advanced NLP for document extraction
- Real-time collaboration features
- Mobile app

## 📄 License

MIT License - see LICENSE file

## 🆘 Troubleshooting

### Workers not processing tasks
```bash
# Check Celery worker logs
docker-compose logs celery-worker

# Verify Redis connection
redis-cli -h localhost ping
```

### Database connection issues
```bash
# Check PostgreSQL
docker-compose logs postgres

# Run migrations
alembic upgrade head
```

### LLM routing not working
- Verify API keys in `.env`
- Check `BOLT_LLM_ENDPOINT` is correct
- Review logs for provider errors

## 📚 Additional Documentation

- [Architecture Deep Dive](docs/architecture.md)
- [API Reference](docs/api.md)
- [Worker Agent Development](docs/workers.md)
- [Deployment Guide](docs/deployment.md)
- [Security Best Practices](docs/security.md)

## 🎯 Demo Video

Coming soon: Full walkthrough of the platform capabilities.

---

**Built for hackathon with focus on production-ready patterns, operational excellence, and secure AI routing.**
