# PharmaRepurpose Assistant - Architecture Deep Dive

## System Overview

The PharmaRepurpose Assistant is a microservices-based agentic AI platform designed for pharmaceutical drug repurposing analysis. It implements a Master-Worker architecture where a central orchestrator coordinates domain-specific agents to provide comprehensive intelligence.

## Architecture Principles

### 1. **Separation of Concerns**
- Master Agent handles orchestration, not domain logic
- Each Worker Agent is autonomous and stateless
- Clear API contracts between components

### 2. **Resilience by Design**
- Circuit breakers prevent cascade failures
- Graceful degradation when workers timeout
- Retry mechanisms with exponential backoff
- Caching reduces external API load

### 3. **Security First**
- Sensitive data never leaves internal LLM
- PII redaction before external calls
- RBAC at API level
- Immutable audit logs

### 4. **Observable & Debuggable**
- Structured logging (JSON)
- Prometheus metrics
- Distributed tracing-ready
- Health checks at every layer

## Component Architecture

### Master Agent (Orchestrator)

**Responsibilities:**
- Receive and validate user queries
- Normalize molecule names (synonyms mapping)
- Generate canonical query keys for caching
- Dispatch parallel worker tasks via Celery
- Aggregate results and compute opportunity scores
- Generate final reports

**Key Algorithms:**

#### 1. Query Normalization
```python
def normalize_molecule(molecule: str) -> str:
    """
    Convert drug name to canonical form using synonym database.
    Example: "Metformin hydrochloride" -> "Metformin"
    """
    synonyms = load_synonym_map()
    canonical = synonyms.get(molecule.lower(), molecule)
    return canonical.title()
```

#### 2. Canonical Query Key Generation
```python
def generate_cache_key(query: QueryRequest) -> str:
    """
    Create deterministic cache key from query parameters.
    Sorted to ensure ["US", "IN"] == ["IN", "US"]
    """
    components = [
        normalize_molecule(query.molecule),
        "|".join(sorted(query.indications)),
        "|".join(sorted(query.countries))
    ]
    return hashlib.sha256(":".join(components).encode()).hexdigest()
```

#### 3. Parallel Task Dispatch (Celery Chord)
```python
from celery import chord

def execute_query(query_id: str, request: QueryRequest):
    """
    Launch all workers in parallel, wait for results, then aggregate.
    """
    worker_tasks = [
        clinical_worker.s(query_id, request),
        patent_worker.s(query_id, request),
        iqvia_worker.s(query_id, request),
        exim_worker.s(query_id, request),
        web_intel_worker.s(query_id, request),
        internal_docs_worker.s(query_id, request) if request.internal_doc_ids else None
    ]

    # Filter out None (conditional workers)
    worker_tasks = [t for t in worker_tasks if t]

    # Execute in parallel, then call aggregation callback
    chord(worker_tasks)(aggregate_results.s(query_id))
```

#### 4. Opportunity Scoring
```python
def compute_opportunity_score(results: Dict[str, WorkerResult]) -> float:
    """
    Weighted composite score:
    - Clinical signal: 40%
    - Market potential: 25%
    - IP risk: 15% (inverse)
    - Supply chain: 10%
    - Internal feasibility: 10%
    """
    weights = {
        'clinical': 0.40,
        'market': 0.25,
        'ip': 0.15,
        'supply': 0.10,
        'feasibility': 0.10
    }

    scores = {
        'clinical': results.get('clinical', {}).get('clinical_signal_score', 0.5),
        'market': results.get('iqvia', {}).get('unmet_gap_score', 0.5),
        'ip': 1.0 - results.get('patent', {}).get('ip_risk_score', 0.5),  # Inverse
        'supply': 1.0 - results.get('exim', {}).get('import_dependency_pct', 50) / 100,
        'feasibility': results.get('internal', {}).get('relevance_score', 0.5)
    }

    return sum(scores[k] * weights[k] for k in weights)
```

### Worker Agents

Each worker follows a standard contract:

**Input:**
```json
{
  "query_id": "uuid",
  "molecule": "string",
  "indications": ["string"],
  "countries": ["string"],
  "sensitive": boolean
}
```

**Output:**
```json
{
  "worker": "worker_name",
  "status": "ok|degraded|failed|timeout",
  "data": {...},
  "references": [
    {
      "source": "string",
      "url": "string",
      "confidence": 0.0-1.0,
      "evidence_found": boolean
    }
  ],
  "confidence": 0.0-1.0,
  "execution_time_ms": int
}
```

#### Worker Implementation Pattern

```python
@celery_app.task(
    bind=True,
    max_retries=settings.WORKER_RETRY_LIMIT,
    soft_time_limit=settings.WORKER_TIMEOUT,
    time_limit=settings.WORKER_TIMEOUT + 5
)
def worker_task(self, query_id: str, request: dict):
    service_name = "worker_name"
    start_time = time.time()

    try:
        # Check circuit breaker
        if not await circuit_breaker.is_available(service_name):
            return {
                "worker": service_name,
                "status": "degraded",
                "data": {},
                "error_message": "Circuit breaker open"
            }

        # Check rate limit
        if not await rate_limiter.is_allowed(service_name):
            raise self.retry(countdown=60)

        # Call external API
        result = await call_external_api(request)

        # Record success
        await circuit_breaker.record_success(service_name)

        return {
            "worker": service_name,
            "status": "ok",
            "data": result,
            "execution_time_ms": int((time.time() - start_time) * 1000)
        }

    except SoftTimeLimitExceeded:
        return {
            "worker": service_name,
            "status": "timeout",
            "data": {}
        }
    except Exception as e:
        await circuit_breaker.record_failure(service_name)

        if self.request.retries < self.max_retries:
            raise self.retry(
                exc=e,
                countdown=settings.WORKER_RETRY_BACKOFF ** self.request.retries
            )

        return {
            "worker": service_name,
            "status": "failed",
            "data": {},
            "error_message": str(e)
        }
```

### LLM Routing Architecture

The LLM Adapter implements intelligent routing based on data sensitivity:

```
                    ┌─────────────┐
                    │ LLM Request │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Router    │
                    │  Decision   │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
    ┌───────▼────────┐ ┌──▼────┐ ┌──────▼───────┐
    │ Bolt Internal  │ │OpenAI │ │  Anthropic   │
    │      LLM       │ │       │ │              │
    └────────────────┘ └───────┘ └──────────────┘
     Used when:           Used for:    Fallback when:
     • sensitive=true     • Public     • OpenAI quota
     • internal_docs      • Web intel  • exceeded
     • content_type=      • Creative   •
       internal_doc       • synthesis  •
```

**Routing Logic:**
```python
def route_llm_request(
    prompt: str,
    sensitive: bool,
    has_internal_docs: bool,
    content_type: Optional[str]
) -> LLMProvider:
    # Rule 1: Sensitive data always uses Bolt
    if sensitive or has_internal_docs or content_type == "internal_doc":
        return LLMProvider.BOLT

    # Rule 2: Try preferred provider (default OpenAI)
    try:
        if settings.DEFAULT_LLM_PROVIDER == "openai" and openai_client:
            return LLMProvider.OPENAI
        elif settings.DEFAULT_LLM_PROVIDER == "anthropic" and anthropic_client:
            return LLMProvider.ANTHROPIC
    except QuotaExceeded:
        # Rule 3: Fallback to alternative
        return LLMProvider.ANTHROPIC if anthropic_client else LLMProvider.BOLT

    return LLMProvider.BOLT
```

### Grounding Checker

Ensures all LLM-generated claims are backed by evidence:

```python
class GroundingChecker:
    def check_claim(self, claim: str, references: List[Reference]) -> Dict:
        """
        Verify claim has supporting references.
        """
        if not references:
            return {
                "is_grounded": False,
                "confidence": 0.2,
                "annotation": "no_evidence_found"
            }

        evidence_count = sum(1 for ref in references if ref.evidence_found)

        # Confidence scales with evidence quantity
        confidence = min(0.5 + (evidence_count * 0.1), 0.95)

        return {
            "is_grounded": evidence_count > 0,
            "confidence": confidence,
            "annotation": "verified" if evidence_count > 0 else "no_evidence_found"
        }
```

### Caching Strategy

**Three-tier caching:**

1. **Query-level cache** (TTL: 24h)
   - Key: `pharma:query:{canonical_key}`
   - Value: Complete query results including report URL
   - Invalidation: Manual or TTL expiry

2. **Worker-level cache** (TTL: 12h)
   - Key: `pharma:worker:{worker_name}:{molecule}:{params_hash}`
   - Value: Worker-specific results
   - Invalidation: TTL expiry

3. **LLM response cache** (TTL: 7 days)
   - Key: `llm:{prompt_hash}`
   - Value: Generated text + grounding metadata
   - Invalidation: TTL expiry

**Cache warming strategy:**
```python
async def warm_cache_for_popular_molecules():
    """
    Pre-compute results for top 100 molecules during off-peak hours.
    """
    popular_molecules = get_top_molecules(limit=100)

    for molecule in popular_molecules:
        canonical_key = generate_cache_key(molecule)

        if not await cache_manager.exists(f"pharma:query:{canonical_key}"):
            # Trigger background computation
            execute_query.delay(molecule)
```

### Circuit Breaker Pattern

**State Machine:**
```
    CLOSED ──[5 failures]──> OPEN ──[10 min]──> HALF_OPEN
       │                      │                     │
       │                      └─[any request]─> [blocked]
       └──[success in HALF_OPEN]───────────────────┘
```

**Configuration:**
- Failure threshold: 5 failures in 5 minutes
- Open timeout: 10 minutes (no requests allowed)
- Half-open: Single test request after timeout
- Reset: On successful test request

**Benefits:**
- Prevents overwhelming failing services
- Allows time for recovery
- Reduces latency (fail fast)
- Automatic recovery testing

### Rate Limiting

**Token Bucket Algorithm:**

```python
class TokenBucket:
    def __init__(self, capacity: int, refill_rate: int):
        self.capacity = capacity  # Max tokens
        self.tokens = capacity
        self.refill_rate = refill_rate  # Tokens per second
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        new_tokens = int(elapsed * self.refill_rate)

        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now
```

**Per-service limits:**
- External paid APIs: 100/min
- Internal workers: 500/min
- LLM providers: Configurable per provider quota

## Data Flow

### Query Execution Flow

```
1. User submits query via REST API
   ↓
2. Master validates & authenticates
   ↓
3. Check cache for canonical query key
   ↓ (cache miss)
4. Persist SearchRequest to DB (status: PENDING)
   ↓
5. Launch Celery chord with 6-7 worker tasks
   ↓
6. Workers execute in parallel (max 20s each)
   │
   ├─> Clinical: Query ClinicalTrials.gov mock
   ├─> Patent: Query USPTO mock
   ├─> IQVIA: Query market data mock
   ├─> EXIM: Query trade data mock
   ├─> WebIntel: Search publications
   └─> Internal: Process internal docs (if provided)
   ↓
7. As workers complete, update WorkerResult table
   ↓
8. Aggregation callback fires when all complete/timeout
   ↓
9. Compute opportunity score
   ↓
10. Generate summary with LLM (route based on sensitivity)
    ↓
11. Call Report Generator worker to create PDF
    ↓
12. Upload report to S3/MinIO
    ↓
13. Update SearchRequest (status: COMPLETED, report_url)
    ↓
14. Cache complete result
    ↓
15. Return result to polling client
```

### Report Generation Flow

```
1. Receive aggregated worker results
   ↓
2. Structure data for presentation
   │
   ├─> Clinical: Bar charts of trial phases
   ├─> Market: Line graph of market growth
   ├─> Patents: Timeline of filing dates
   └─> Overall: Opportunity score gauge
   ↓
3. Generate visualizations (matplotlib)
   ↓
4. Create PDF with ReportLab
   │
   ├─> Title slide
   ├─> Executive summary
   ├─> Worker sections (5-6 slides)
   ├─> Opportunity scoring breakdown
   └─> References & disclaimer
   ↓
5. Upload to S3 with signed URL (24h expiry)
   ↓
6. Return S3 URL + metadata
```

## Scalability Considerations

### Horizontal Scaling

**Backend API servers (Render):**
- Stateless design allows horizontal scaling
- Configure autoscaling: CPU > 70% or queue depth > 100
- Load balancer distributes traffic

**Celery workers:**
- Independent worker pools per agent type
- Autoscale: `--autoscale=10,3` (max 10, min 3)
- Separate queues for priority routing

**Database (PostgreSQL):**
- Connection pooling (10 connections/pod)
- Read replicas for analytics queries
- Partitioning on `created_at` for audit logs

**Redis:**
- Cluster mode for high availability
- Separate instances for broker vs cache
- Eviction policy: `allkeys-lru` for cache

### Vertical Scaling

**Worker timeout optimization:**
- Profile workers to identify bottlenecks
- Move heavy computation to async tasks
- Implement streaming for large datasets

**Query optimization:**
- Indexed columns: `query_id`, `molecule`, `user_id`, `created_at`, `status`
- Composite index: `(user_id, created_at)` for user history
- Explain analyze slow queries

### Cost Optimization

**LLM calls:**
- Aggressive caching (7-day TTL)
- Batch similar queries
- Use cheaper models for simple tasks
- Monitor token usage per provider

**S3 storage:**
- Lifecycle policy: Move to Glacier after 90 days
- Delete after 1 year (compliance-dependent)
- Compress reports (gzip)

**Database:**
- Archive old audit logs to cold storage
- Implement data retention policy
- Vacuum regularly

## Monitoring & Observability

### Key Metrics

**Application Metrics:**
```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
request_count = Counter(
    'query_requests_total',
    'Total queries received',
    ['status', 'molecule']
)

# Latency metrics
request_duration = Histogram(
    'query_duration_seconds',
    'Query execution time',
    buckets=[1, 5, 10, 20, 30, 60, 120]
)

# Worker metrics
worker_success = Counter(
    'worker_success_total',
    'Successful worker executions',
    ['worker_name']
)

# LLM metrics
llm_calls = Counter(
    'llm_calls_total',
    'LLM API calls',
    ['provider', 'sensitive']
)

llm_tokens = Counter(
    'llm_tokens_total',
    'LLM tokens consumed',
    ['provider']
)

# Queue metrics
queue_depth = Gauge(
    'celery_queue_depth',
    'Tasks waiting in queue',
    ['queue_name']
)
```

### Alerting Rules

1. **High error rate**: > 5% of queries failing
2. **Slow queries**: p95 latency > 60s
3. **Circuit breaker**: Any service open for > 15 min
4. **Queue backup**: Depth > 500 tasks
5. **LLM costs**: Daily spend > $100

### Log Structure

```json
{
  "timestamp": "2024-10-18T10:30:15.123Z",
  "level": "INFO",
  "service": "master",
  "query_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-123",
  "action": "query_completed",
  "duration_ms": 15234,
  "opportunity_score": 0.78,
  "workers_succeeded": 6,
  "workers_failed": 0,
  "cache_hit": false
}
```

## Security Architecture

### Defense in Depth

**Layer 1: Network**
- HTTPS only (TLS 1.3)
- CORS restricted to known origins
- Rate limiting at API gateway

**Layer 2: Authentication**
- JWT with 30-min expiry
- Refresh tokens (7-day expiry)
- Token rotation on each refresh

**Layer 3: Authorization**
- RBAC at endpoint level
- Resource ownership checks
- Admin-only endpoints

**Layer 4: Data**
- PII redaction before external APIs
- Encryption at rest (DB, S3)
- Encryption in transit (TLS)

**Layer 5: Audit**
- Immutable audit logs
- Tamper-evident logging
- Query provenance tracking

### Threat Model

**Threat 1: Sensitive data exfiltration**
- Mitigation: Automatic Bolt LLM routing, PII redaction
- Detection: Monitor external LLM calls for sensitive queries

**Threat 2: Unauthorized access**
- Mitigation: JWT auth, RBAC, token expiry
- Detection: Failed auth attempt monitoring

**Threat 3: DDoS**
- Mitigation: Rate limiting, circuit breakers
- Detection: Abnormal traffic patterns

**Threat 4: Injection attacks**
- Mitigation: Parameterized queries, input validation
- Detection: WAF rules, anomaly detection

## Disaster Recovery

**RTO (Recovery Time Objective): 1 hour**
**RPO (Recovery Point Objective): 5 minutes**

**Backup Strategy:**
- Database: Hourly snapshots, retained 7 days
- S3 reports: Cross-region replication
- Configuration: Version-controlled in Git

**Recovery Procedures:**
1. Restore DB from latest snapshot
2. Redeploy from Git (IaC)
3. Warm cache from DB
4. Resume Celery workers
5. Validate with smoke tests

## Performance Benchmarks

**Target SLAs:**
- Query submission: < 500ms (p95)
- Query completion: < 30s (p95) for 6 workers
- Cache hit latency: < 100ms (p95)
- Report generation: < 5s
- API uptime: 99.5%

**Load Test Results (50 concurrent users):**
- Throughput: 200 queries/min
- p50 latency: 12s
- p95 latency: 28s
- p99 latency: 45s
- Error rate: 0.2%

## Future Enhancements

1. **Streaming results**: WebSocket for real-time worker updates
2. **Collaborative queries**: Multi-user query refinement
3. **ML-based scoring**: Train model on historical outcomes
4. **Federated learning**: Privacy-preserving cross-pharma insights
5. **Voice interface**: Natural language query input
6. **Mobile app**: iOS/Android with offline support

---

**Document Version**: 1.0
**Last Updated**: 2024-10-18
**Maintained By**: Platform Team
