# PharmaRepurpose Assistant - Quick Start

## 🚀 Get Running in 10 Minutes

This guide gets you from zero to a working API server with mock services.

## Prerequisites Check

```bash
# Check you have these installed:
docker --version        # Should be 20.x or higher
docker-compose --version # Should be 1.29.x or higher
python --version        # Should be 3.11.x or higher
```

If missing, install:
- **Docker Desktop**: https://www.docker.com/products/docker-desktop
- **Python 3.11**: https://www.python.org/downloads/

## Step 1: Start Infrastructure (2 minutes)

```bash
# From project root
cd pharma-repurpose

# Start PostgreSQL, Redis, MinIO, and all mock services
docker-compose up -d

# Wait 10 seconds for services to initialize
sleep 10

# Verify all services are running
docker-compose ps

# You should see all services in "Up" state
```

**Expected output**:
```
NAME                  STATUS
pharma_postgres       Up (healthy)
pharma_redis          Up (healthy)
pharma_minio          Up (healthy)
pharma_mock_clinical  Up
pharma_mock_iqvia     Up
pharma_mock_exim      Up
pharma_mock_uspto     Up
pharma_mock_web       Up
```

## Step 2: Set Up Backend (3 minutes)

```bash
cd backend

# Create and activate virtual environment
python -m venv venv

# On macOS/Linux:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate

# Install dependencies (this takes 2-3 minutes)
pip install -r requirements.txt

# Copy environment template
cp .env.template .env

# Edit .env if needed (optional for local dev)
# The default values work with Docker Compose
```

## Step 3: Initialize Database (1 minute)

```bash
# Still in backend/ directory with venv activated

# Create database tables
# (Note: This requires implementing Alembic migrations first)
# For now, tables will be created automatically on first API call
# due to SQLAlchemy's create_all() if you add it to main.py

# Quick test database connection
python -c "from app.config import settings; print(f'DB URL: {settings.DATABASE_URL}')"
```

## Step 4: Start API Server (1 minute)

```bash
# Still in backend/ directory
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# You should see:
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
# INFO:     🚀 Starting PharmaRepurpose Assistant
# INFO:     ✅ Cache connected
# INFO:     ✅ Circuit breaker connected
# INFO:     ✅ Rate limiter connected
```

## Step 5: Test It's Working (1 minute)

Open a new terminal:

```bash
# Test health endpoint
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "timestamp": "2024-10-18T...",
#   "environment": "development",
#   "services": {
#     "api": "ok",
#     "database": "ok",
#     "redis": "ok",
#     "celery": "ok"
#   }
# }

# Test mock Clinical Trials service
curl http://localhost:8004/health

# Expected response:
# {"status": "healthy", "service": "clinical_trials_mock"}

# Test mock Clinical Trials search
curl -X POST http://localhost:8004/search \
  -H "Content-Type: application/json" \
  -d '{
    "molecule": "Metformin",
    "indications": ["Cancer"],
    "countries": ["US"]
  }'

# You should get back mock clinical trial data
```

## Step 6: Access the API Documentation (1 minute)

Open your browser and go to:

**Interactive API Docs**: http://localhost:8000/api/v1/docs

You'll see the Swagger UI with all API endpoints documented.

**Alternative Docs**: http://localhost:8000/api/v1/redoc

## Step 7: Test Mock Services (1 minute)

Test all 5 mock services are responding:

```bash
# Clinical Trials
curl http://localhost:8004/health

# IQVIA Market Data
curl http://localhost:8001/health

# EXIM Trade Data
curl http://localhost:8002/health

# USPTO Patents
curl http://localhost:8003/health

# Web Intelligence
curl http://localhost:8005/health

# All should return: {"status": "healthy", "service": "..."}
```

## 🎉 Success!

You now have:
- ✅ PostgreSQL database running
- ✅ Redis cache and message broker running
- ✅ MinIO object storage running
- ✅ FastAPI backend server running
- ✅ 5 mock external services running
- ✅ Prometheus metrics endpoint at `/metrics`

## Next Steps

### A. Implement the Missing Pieces (See IMPLEMENTATION_GUIDE.md)

1. **Create Celery workers** (`backend/app/workers/`)
2. **Build Master orchestrator** (`backend/app/services/master_service.py`)
3. **Add API routers** (`backend/app/routers/`)
4. **Create database migrations** (`backend/alembic/versions/`)

### B. Test a Complete Flow

Once you implement the workers and routers:

```bash
# 1. Start Celery worker (new terminal)
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
celery -A app.tasks worker --loglevel=INFO

# 2. Submit a test query (new terminal)
curl -X POST http://localhost:8000/api/v1/master/query \
  -H "Content-Type: application/json" \
  -d '{
    "molecule": "Metformin",
    "indications": ["Cancer", "Alzheimers"],
    "countries": ["US", "IN"],
    "report_format": "pdf"
  }'

# 3. Check query status
curl http://localhost:8000/api/v1/master/status/{query_id}
```

### C. Build the Frontend

```bash
# Already set up in your project!
cd frontend
npm install
npm run dev

# Frontend will be at http://localhost:5173
```

## 🛠 Troubleshooting

### Problem: "Port already in use"

```bash
# Find what's using the port
lsof -i :8000  # On macOS/Linux
netstat -ano | findstr :8000  # On Windows

# Kill the process or use a different port
uvicorn app.main:app --reload --port 8001
```

### Problem: "Connection to database failed"

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Restart if needed
docker-compose restart postgres
```

### Problem: "Redis connection refused"

```bash
# Check Redis is running
docker-compose ps redis

# Test connection
redis-cli -h localhost -p 6379 ping
# Should respond: PONG

# Restart if needed
docker-compose restart redis
```

### Problem: "Mock service not responding"

```bash
# Check all mock services
docker-compose ps | grep mock

# Restart specific mock
docker-compose restart mock-clinical

# View logs
docker-compose logs mock-clinical
```

### Problem: "Import errors in Python"

```bash
# Make sure you're in the venv
which python  # Should show path to venv/bin/python

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## 📊 View Prometheus Metrics

```bash
# Metrics endpoint (raw Prometheus format)
curl http://localhost:8000/metrics

# You'll see metrics like:
# http_requests_total{endpoint="/health",method="GET",status="200"} 5.0
# http_request_duration_seconds_bucket{endpoint="/health",method="GET",le="0.1"} 5.0
```

## 🗄 Access MinIO Console

1. Open http://localhost:9001 in your browser
2. Login with:
   - Username: `minioadmin`
   - Password: `minioadmin123`
3. Create bucket: `pharma-reports`

## 🗃 Access PostgreSQL

```bash
# Using psql
docker exec -it pharma_postgres psql -U pharma -d pharma_repurpose

# Once in psql:
\dt                    # List tables
\d users              # Describe users table
SELECT * FROM users;  # Query users
\q                    # Quit
```

## 🔴 Redis CLI

```bash
# Connect to Redis
docker exec -it pharma_redis redis-cli

# Test commands
PING                           # Should return PONG
SET test "Hello"              # Set a key
GET test                      # Get a key
KEYS *                        # List all keys
QUIT                          # Exit
```

## 📁 Project Structure Quick Reference

```
pharma-repurpose/
├── backend/
│   ├── app/
│   │   ├── main.py           ← FastAPI app (READY)
│   │   ├── config.py         ← Settings (READY)
│   │   ├── models/           ← Database models (READY)
│   │   ├── services/         ← Business logic (LLM adapter READY)
│   │   ├── utils/            ← Utilities (ALL READY)
│   │   ├── routers/          ← API endpoints (TO BUILD)
│   │   └── workers/          ← Celery tasks (TO BUILD)
│   ├── requirements.txt      ← Dependencies (READY)
│   ├── Dockerfile           ← Container config (READY)
│   └── .env                 ← Configuration (READY)
├── mocks/                   ← Mock services (ALL READY)
├── frontend/                ← React app (TO BUILD)
├── docker-compose.yml       ← Orchestration (READY)
└── docs/                    ← Documentation (ALL READY)
```

## 🎯 Current Status

**What's Working:**
- ✅ All infrastructure services
- ✅ FastAPI server with health check
- ✅ All mock external APIs
- ✅ Cache, circuit breaker, rate limiter
- ✅ LLM routing logic
- ✅ Database models
- ✅ Auth utilities
- ✅ Prometheus metrics

**What Needs Implementation:**
- 🔨 Celery worker tasks (7 workers)
- 🔨 Master orchestrator
- 🔨 API routers (auth, master, workers)
- 🔨 Database migrations
- 🔨 Report generator
- 🔨 React frontend

**Estimated Time to Complete MVP:** 15-20 hours

## 📚 Learn More

- **Full Documentation**: See `README.md`
- **Architecture Details**: See `docs/architecture.md`
- **Implementation Guide**: See `IMPLEMENTATION_GUIDE.md`
- **Project Summary**: See `PROJECT_SUMMARY.md`

## 🆘 Need Help?

1. Check the error message carefully
2. Look in the relevant documentation file
3. Check Docker logs: `docker-compose logs [service-name]`
4. Check backend logs in the terminal running uvicorn
5. Verify all environment variables in `.env`

## 🎬 Ready to Build?

You have a solid foundation. Follow the **IMPLEMENTATION_GUIDE.md** to build the remaining components in the recommended order.

**Recommended next step**: Implement one complete worker (Clinical) following the pattern in the guide, then copy it for the other workers.

Good luck with your hackathon! 🚀
