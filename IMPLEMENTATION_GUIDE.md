# PharmaRepurpose Assistant - Implementation Guide

## ⚠️ Important Notice

This is a **massive enterprise-grade project** that would typically require:
- **Team Size**: 5-8 engineers
- **Timeline**: 8-12 weeks for MVP
- **Complexity**: High (microservices, distributed systems, AI orchestration)

For your hackathon, I've provided:
1. ✅ Complete architecture and documentation
2. ✅ Core infrastructure code (auth, caching, LLM routing, circuit breakers)
3. ✅ Database models and schemas
4. 📋 Clear implementation roadmap for remaining components

## What's Been Completed

### ✅ Backend Foundation
- **Configuration**: `backend/app/config.py` with all settings
- **Database Models**: Complete SQLAlchemy models in `backend/app/models/`
- **Auth System**: JWT authentication with RBAC in `backend/app/utils/auth.py`
- **LLM Adapter**: Intelligent routing (Bolt/OpenAI/Anthropic) with grounding checker
- **Caching**: Redis-based cache manager with TTL
- **Circuit Breaker**: Resilience pattern for external APIs
- **Rate Limiter**: Token bucket implementation
- **PII Redaction**: Pattern-based PII detector

### ✅ Documentation
- **README.md**: Complete user guide with API docs, deployment steps
- **docs/architecture.md**: Deep technical architecture with algorithms and data flows

## What Needs to Be Built

### 1. Celery Task System (HIGH PRIORITY)

**File**: `backend/app/tasks.py`

```python
from celery import Celery, chord, group
from app.config import settings

celery_app = Celery(
    'pharma_tasks',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_soft_time_limit=settings.WORKER_TIMEOUT,
    task_time_limit=settings.WORKER_TIMEOUT + 5,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Import all worker tasks
from app.workers import (
    clinical_worker,
    patent_worker,
    iqvia_worker,
    exim_worker,
    web_intel_worker,
    internal_docs_worker,
    report_generator_worker
)
```

### 2. Worker Agent Services (HIGH PRIORITY)

Create each worker in `backend/app/workers/`:

#### `backend/app/workers/clinical_worker.py`
```python
from celery import Task
from app.tasks import celery_app
from app.utils.circuit_breaker import circuit_breaker
from app.utils.rate_limiter import rate_limiter
import httpx

@celery_app.task(bind=True, max_retries=3)
def clinical_search(self, query_id: str, request: dict):
    """
    Search ClinicalTrials.gov for relevant trials.
    """
    # Implementation:
    # 1. Check circuit breaker
    # 2. Call settings.CLINICAL_TRIALS_API_URL
    # 3. Parse response
    # 4. Extract references
    # 5. Return structured result
    pass
```

Repeat for:
- `patent_worker.py` (USPTO search)
- `iqvia_worker.py` (Market data)
- `exim_worker.py` (Trade data)
- `web_intel_worker.py` (Publications, news)
- `internal_docs_worker.py` (Process internal PDFs with Bolt LLM)
- `report_generator.py` (Create PDF using ReportLab)

### 3. Master Orchestrator (HIGH PRIORITY)

**File**: `backend/app/services/master_service.py`

```python
from celery import chord
from app.tasks import celery_app
from app.workers import *
from app.models.models import SearchRequest
from app.utils.cache import cache_manager
import hashlib

class MasterOrchestrator:
    def normalize_molecule(self, molecule: str) -> str:
        """Normalize drug name to canonical form."""
        # TODO: Implement synonym mapping
        return molecule.strip().title()

    def generate_canonical_key(self, request: QueryRequest) -> str:
        """Generate cache key from query."""
        components = [
            self.normalize_molecule(request.molecule),
            "|".join(sorted(request.indications)),
            "|".join(sorted(request.countries))
        ]
        return hashlib.sha256(":".join(components).encode()).hexdigest()

    async def execute_query(self, query_id: str, request: QueryRequest):
        """Launch parallel worker tasks."""
        # 1. Check cache
        cache_key = self.generate_canonical_key(request)
        cached = await cache_manager.get(f"pharma:query:{cache_key}")
        if cached:
            return cached

        # 2. Build worker task list
        tasks = [
            clinical_search.s(query_id, request.dict()),
            patent_search.s(query_id, request.dict()),
            iqvia_search.s(query_id, request.dict()),
            exim_search.s(query_id, request.dict()),
            web_intel_search.s(query_id, request.dict()),
        ]

        if request.internal_doc_ids:
            tasks.append(internal_docs_process.s(query_id, request.dict()))

        # 3. Execute with chord (parallel + callback)
        job = chord(tasks)(aggregate_results.s(query_id))

        return {"job_id": job.id, "status": "processing"}

    def compute_opportunity_score(self, results: dict) -> float:
        """Calculate weighted composite score."""
        weights = {
            'clinical': 0.40,
            'market': 0.25,
            'ip': 0.15,
            'supply': 0.10,
            'feasibility': 0.10
        }
        # TODO: Implement scoring logic
        return 0.75

@celery_app.task
def aggregate_results(worker_results, query_id: str):
    """Callback after all workers complete."""
    # 1. Compute opportunity score
    # 2. Generate summary with LLM
    # 3. Call report generator
    # 4. Update database
    # 5. Cache result
    pass
```

### 4. FastAPI Routers (HIGH PRIORITY)

#### `backend/app/routers/auth.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import UserCreate, Token
from app.utils.auth import create_access_token, get_password_hash

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # TODO: Create user in database
    pass

@router.post("/login")
async def login(email: str, password: str, db: Session = Depends(get_db)):
    # TODO: Validate credentials, return JWT
    pass
```

#### `backend/app/routers/master.py`
```python
from fastapi import APIRouter, Depends
from app.models.schemas import QueryRequest, QueryResponse
from app.services.master_service import MasterOrchestrator

router = APIRouter(prefix="/master", tags=["master"])

@router.post("/query", response_model=QueryResponse, status_code=202)
async def submit_query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit new drug repurposing query."""
    # TODO: Implementation
    pass

@router.get("/status/{query_id}")
async def get_status(
    query_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get query status and results."""
    # TODO: Implementation
    pass
```

### 5. Main FastAPI App (HIGH PRIORITY)

**File**: `backend/app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from app.config import settings
from app.routers import auth, master, workers
from app.models.database import engine, Base
from app.utils.cache import cache_manager
from app.utils.circuit_breaker import circuit_breaker
from app.utils.rate_limiter import rate_limiter

app = FastAPI(title="PharmaRepurpose Assistant", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(master.router, prefix=settings.API_V1_PREFIX)

# Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.on_event("startup")
async def startup():
    await cache_manager.connect()
    await circuit_breaker.connect()
    await rate_limiter.connect()

@app.on_event("shutdown")
async def shutdown():
    await cache_manager.close()
    await circuit_breaker.close()
    await rate_limiter.close()

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "database": "ok",
            "redis": "ok",
            "celery": "ok"
        }
    }
```

### 6. Mock External Services (MEDIUM PRIORITY)

Create simple Flask/FastAPI apps in `mocks/`:

```python
# mocks/clinical_trials_mock.py
from fastapi import FastAPI

app = FastAPI()

@app.post("/search")
async def search_trials(molecule: str, indications: list):
    return {
        "trials": [
            {
                "id": "NCT12345678",
                "title": f"Study of {molecule} in Cancer",
                "phase": "Phase 3",
                "status": "Recruiting",
                "country": "US",
                "sponsor": "Pharma Corp",
                "url": "https://clinicaltrials.gov/NCT12345678"
            }
        ]
    }
```

Repeat for IQVIA, EXIM, USPTO, Web Search.

### 7. React Frontend (MEDIUM PRIORITY)

**Key Components**:

```typescript
// frontend/src/pages/QueryBuilder.tsx
export const QueryBuilder = () => {
  // Form for molecule, indications, countries
  // Submit button calls POST /api/v1/master/query
  // Redirect to ProgressDashboard
};

// frontend/src/pages/ProgressDashboard.tsx
export const ProgressDashboard = () => {
  // Poll GET /api/v1/master/status/{queryId}
  // Show worker progress with status badges
  // Download button when complete
};

// frontend/src/pages/ResultsView.tsx
export const ResultsView = () => {
  // Display aggregated results
  // Charts with Chart.js
  // Downloadable CSV and PDF
};

// frontend/src/pages/AdminPanel.tsx
export const AdminPanel = () => {
  // System metrics
  // Queue depth
  // Recent queries
  // Log viewer
};
```

### 8. Database Migrations (HIGH PRIORITY)

**File**: `backend/alembic/versions/001_initial_schema.py`

```python
"""Initial schema

Revision ID: 001
"""

def upgrade():
    # Create all tables from models
    # See backend/app/models/models.py for schema

def downgrade():
    # Drop all tables
```

Run: `alembic revision --autogenerate -m "Initial schema"`

### 9. Docker Compose (HIGH PRIORITY)

**File**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: pharma
      POSTGRES_PASSWORD: pharma
      POSTGRES_DB: pharma_repurpose
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

  backend:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    env_file:
      - backend/.env

  celery-worker:
    build: ./backend
    command: celery -A app.tasks worker --loglevel=INFO --concurrency=4
    depends_on:
      - postgres
      - redis
    env_file:
      - backend/.env

  mock-clinical:
    build: ./mocks
    command: uvicorn clinical_trials_mock:app --host 0.0.0.0 --port 8004
    ports:
      - "8004:8004"

volumes:
  postgres_data:
  minio_data:
```

### 10. GitHub Actions CI/CD (MEDIUM PRIORITY)

**File**: `.github/workflows/deploy.yml`

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          cd backend
          pip install -r requirements.txt
          pytest

  deploy-backend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Render
        env:
          RENDER_API_KEY: ${{ secrets.RENDER_API_KEY }}
        run: |
          # Trigger Render deployment
          curl -X POST "https://api.render.com/v1/services/${{ secrets.RENDER_SERVICE_ID }}/deploys" \
            -H "Authorization: Bearer $RENDER_API_KEY"

  deploy-frontend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Vercel
        run: |
          cd frontend
          npm install
          npx vercel --prod --token=${{ secrets.VERCEL_TOKEN }}
```

### 11. Monitoring (LOW PRIORITY - Nice to Have)

**File**: `monitoring/grafana-dashboard.json`

Pre-built dashboard JSON with panels for:
- Query throughput
- Worker success/failure rates
- LLM call distribution
- Cache hit ratio
- Queue depth

### 12. Demo Script (HIGH PRIORITY)

**File**: `scripts/demo.sh`

```bash
#!/bin/bash

echo "🚀 Starting PharmaRepurpose Demo..."

# Start infrastructure
docker-compose up -d postgres redis minio

# Wait for services
sleep 5

# Run migrations
cd backend
alembic upgrade head

# Create demo user
python scripts/create_demo_user.py

# Start backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start Celery
celery -A app.tasks worker --loglevel=INFO &
CELERY_PID=$!

sleep 5

# Submit demo query
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@pharma.com","password":"demo123"}' \
  > token.json

TOKEN=$(cat token.json | jq -r .access_token)

curl -X POST http://localhost:8000/api/v1/master/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "molecule": "Metformin",
    "indications": ["Cancer", "Alzheimers"],
    "countries": ["US", "IN"],
    "report_format": "pdf"
  }' > query.json

QUERY_ID=$(cat query.json | jq -r .query_id)

echo "Query submitted: $QUERY_ID"
echo "Polling for results..."

# Poll status
while true; do
  STATUS=$(curl -s -H "Authorization: Bearer $TOKEN" \
    http://localhost:8000/api/v1/master/status/$QUERY_ID | jq -r .status)

  echo "Status: $STATUS"

  if [ "$STATUS" = "completed" ]; then
    echo "✅ Query completed!"
    curl -s -H "Authorization: Bearer $TOKEN" \
      http://localhost:8000/api/v1/master/status/$QUERY_ID | jq .
    break
  fi

  sleep 2
done

# Cleanup
kill $BACKEND_PID $CELERY_PID
```

## Quick Start Sequence

### For Hackathon Speed:

1. **Day 1 - Backend Core**
   - [ ] Set up Docker Compose
   - [ ] Create database migrations
   - [ ] Implement `main.py` with health endpoint
   - [ ] Test: `curl http://localhost:8000/health`

2. **Day 1-2 - Worker Foundation**
   - [ ] Create Celery config in `tasks.py`
   - [ ] Implement ONE worker (Clinical) end-to-end
   - [ ] Create mock Clinical Trials API
   - [ ] Test: Submit Celery task manually

3. **Day 2 - Master Orchestrator**
   - [ ] Implement `master_service.py`
   - [ ] Create `/master/query` endpoint
   - [ ] Test: Submit query, verify Celery task created

4. **Day 2-3 - Remaining Workers**
   - [ ] Copy Clinical worker pattern to other 5 workers
   - [ ] Create mock APIs for each
   - [ ] Test: All workers return data

5. **Day 3 - Report Generation**
   - [ ] Implement PDF generation with ReportLab
   - [ ] Upload to MinIO
   - [ ] Test: Download generated PDF

6. **Day 3-4 - Frontend**
   - [ ] Create QueryBuilder form
   - [ ] Implement polling on ProgressDashboard
   - [ ] Display results in ResultsView
   - [ ] Test: End-to-end user flow

7. **Day 4 - Demo Polish**
   - [ ] Add sample molecules and queries
   - [ ] Create demo script
   - [ ] Record demo video
   - [ ] Write presentation

## Sample Data

**File**: `backend/data/sample_molecules.json`
```json
[
  {
    "molecule": "Metformin",
    "approved_for": ["Type 2 Diabetes"],
    "repurpose_candidates": ["Cancer", "Alzheimer's", "PCOS"]
  },
  {
    "molecule": "Aspirin",
    "approved_for": ["Pain", "Inflammation"],
    "repurpose_candidates": ["Cardiovascular disease", "Cancer prevention"]
  },
  {
    "molecule": "Sildenafil",
    "approved_for": ["Erectile dysfunction"],
    "repurpose_candidates": ["Pulmonary hypertension", "Raynaud's"]
  }
]
```

**File**: `backend/data/sample_queries.json`
```json
[
  {
    "query": "Metformin for NSCLC",
    "molecule": "Metformin",
    "indications": ["Non-small cell lung cancer"],
    "countries": ["US", "IN"]
  },
  ...
]
```

## Testing Strategy

### Unit Tests
```python
# tests/test_master_service.py
def test_canonical_key_generation():
    service = MasterOrchestrator()
    key1 = service.generate_canonical_key(query_us_in)
    key2 = service.generate_canonical_key(query_in_us)
    assert key1 == key2  # Order shouldn't matter
```

### Integration Tests
```python
# tests/integration/test_query_flow.py
async def test_end_to_end_query():
    # Submit query
    response = client.post("/api/v1/master/query", json=query_data)
    assert response.status_code == 202

    # Poll status
    # Verify completion
    # Check report URL
```

### Load Tests
```javascript
// scripts/load_test.js (k6)
import http from 'k6/http';

export let options = {
  vus: 50,
  duration: '5m',
};

export default function() {
  const payload = JSON.stringify({
    molecule: 'Metformin',
    indications: ['Cancer'],
    countries: ['US']
  });

  http.post('http://localhost:8000/api/v1/master/query', payload, {
    headers: { 'Content-Type': 'application/json' },
  });
}
```

## Common Pitfalls

1. **Celery not picking up tasks**
   - Check broker URL matches
   - Verify worker is running: `celery -A app.tasks inspect active`

2. **Circuit breaker always open**
   - Reduce failure threshold for testing
   - Check mock services are running

3. **LLM routing incorrect**
   - Verify API keys in `.env`
   - Check `sensitive` flag in requests

4. **Database connection pool exhausted**
   - Increase pool size in `database.py`
   - Check for unclosed sessions

5. **S3/MinIO upload fails**
   - Verify bucket exists: `mc mb minio/pharma-reports`
   - Check credentials

## Success Criteria

- [ ] Submit query via API → Get query_id
- [ ] All 6 workers complete within 30s
- [ ] Opportunity score calculated correctly
- [ ] PDF report generated and downloadable
- [ ] Frontend displays results with charts
- [ ] Demo script runs successfully
- [ ] Load test handles 50 concurrent users

## Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Celery Docs**: https://docs.celeryproject.org/
- **ReportLab Guide**: https://www.reportlab.com/docs/reportlab-userguide.pdf
- **Render Docs**: https://render.com/docs
- **Vercel Docs**: https://vercel.com/docs

## Support

For architecture questions, refer to:
- `docs/architecture.md` - Technical deep dive
- `README.md` - User guide
- This file - Implementation roadmap

---

**Remember**: This is a hackathon. Focus on the demo path (one complete flow) rather than handling every edge case. Build the "happy path" first, then add resilience if time permits.

Good luck! 🚀
