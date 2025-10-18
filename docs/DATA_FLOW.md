# PharmaRepurpose Assistant - Data Flow Diagrams

## Complete Query Execution Flow

```
┌─────────────┐
│   User UI   │
│  (React)    │
└──────┬──────┘
       │ POST /api/v1/master/query
       │ {molecule, indications, countries, sensitive, ...}
       ▼
┌────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │          1. Request Validation & Auth                 │ │
│  │          - JWT token verification                     │ │
│  │          - RBAC permission check                      │ │
│  │          - Pydantic schema validation                 │ │
│  └───────────────────┬──────────────────────────────────┘ │
│                      ▼                                      │
│  ┌──────────────────────────────────────────────────────┐ │
│  │      2. Query Normalization (Master Service)         │ │
│  │          - Molecule name canonicalization            │ │
│  │          - Generate cache key hash                    │ │
│  │          - Check Redis cache                          │ │
│  └───────────────────┬──────────────────────────────────┘ │
│                      ▼                                      │
│              ┌──────┴──────┐                               │
│              │ Cache Hit?  │                               │
│              └──────┬──────┘                               │
│         Yes ◄───────┼───────► No                           │
│          │          │         │                            │
│          │          │         ▼                            │
│          │          │  ┌───────────────────────┐          │
│          │          │  │ 3. Persist to DB      │          │
│          │          │  │    SearchRequest      │          │
│          │          │  │    status: PENDING    │          │
│          │          │  └──────────┬────────────┘          │
│          │          │             ▼                        │
│          │          │  ┌───────────────────────┐          │
│          │          │  │ 4. Create Celery      │          │
│          │          │  │    Chord (Group +     │          │
│          │          │  │    Callback)          │          │
│          │          │  └──────────┬────────────┘          │
│          │          │             ▼                        │
│  ┌───────▼──────────▼─────────────▼────────────────────┐ │
│  │                5. Return Response                    │ │
│  │   {query_id, status: "processing", progress_url}    │ │
│  └──────────────────────┬───────────────────────────────┘ │
└────────────────────────┬┼───────────────────────────────┘
                         ││
         ┌───────────────┘└───────────────┐
         │ 202 Accepted                   │
         ▼                                 ▼
┌─────────────┐                   ┌────────────────┐
│   User UI   │                   │ Celery Broker  │
│  Polls      │                   │   (Redis)      │
│  /status    │                   └────────┬───────┘
└─────────────┘                            │
                                           ▼
                          ┌────────────────────────────────┐
                          │    Celery Worker Pool          │
                          │    (Parallel Execution)        │
                          └────────────────┬───────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
              ┌──────────┐          ┌──────────┐          ┌──────────┐
              │ Clinical │          │  Patent  │          │  IQVIA   │
              │  Worker  │          │  Worker  │          │  Worker  │
              └────┬─────┘          └────┬─────┘          └────┬─────┘
                   │                     │                     │
                   ▼                     ▼                     ▼
           ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
           │Circuit Break?│      │Circuit Break?│      │Circuit Break?│
           └──────┬───────┘      └──────┬───────┘      └──────┬───────┘
                  │ Open                 │ Open                 │ Open
                  │ → Degrade            │ → Degrade            │ → Degrade
                  ▼ Closed               ▼ Closed               ▼ Closed
           ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
           │ Rate Limit?  │      │ Rate Limit?  │      │ Rate Limit?  │
           └──────┬───────┘      └──────┬───────┘      └──────┬───────┘
                  │ OK                   │ OK                   │ OK
                  ▼                      ▼                      ▼
           ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
           │ Mock Clinical│      │ Mock USPTO   │      │ Mock IQVIA   │
           │ Trials API   │      │ API          │      │ API          │
           └──────┬───────┘      └──────┬───────┘      └──────┬───────┘
                  │                      │                      │
                  ▼                      ▼                      ▼
              [JSON Data]            [JSON Data]            [JSON Data]
                  │                      │                      │
                  ▼                      ▼                      ▼
           ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
           │ Store in DB: │      │ Store in DB: │      │ Store in DB: │
           │WorkerResult  │      │WorkerResult  │      │WorkerResult  │
           │status: OK    │      │status: OK    │      │status: OK    │
           └──────┬───────┘      └──────┬───────┘      └──────┬───────┘
                  │                      │                      │
                  └──────────────────────┼──────────────────────┘
                                         ▼
                          ┌────────────────────────────────┐
                          │ 6. Aggregation Callback        │
                          │    (After all workers complete)│
                          └────────────┬───────────────────┘
                                       ▼
                          ┌────────────────────────────────┐
                          │ 7. Compute Opportunity Score   │
                          │    - Clinical: 40%             │
                          │    - Market: 25%               │
                          │    - IP Risk: 15% (inverse)    │
                          │    - Supply: 10%               │
                          │    - Feasibility: 10%          │
                          └────────────┬───────────────────┘
                                       ▼
                          ┌────────────────────────────────┐
                          │ 8. Generate Summary with LLM   │
                          │    Route based on sensitivity: │
                          │    - Sensitive → Bolt LLM      │
                          │    - Public → OpenAI/Anthropic │
                          └────────────┬───────────────────┘
                                       ▼
                          ┌────────────────────────────────┐
                          │ 9. Grounding Checker           │
                          │    - Verify references exist   │
                          │    - Compute confidence score  │
                          │    - Annotate claims           │
                          └────────────┬───────────────────┘
                                       ▼
                          ┌────────────────────────────────┐
                          │ 10. Report Generator Worker    │
                          │     - Create PDF with charts   │
                          │     - Upload to S3/MinIO       │
                          │     - Generate signed URL      │
                          └────────────┬───────────────────┘
                                       ▼
                          ┌────────────────────────────────┐
                          │ 11. Update Database            │
                          │     SearchRequest:             │
                          │     - status: COMPLETED        │
                          │     - opportunity_score: 0.78  │
                          │     - summary: {...}           │
                          │     - report_url: s3://...     │
                          └────────────┬───────────────────┘
                                       ▼
                          ┌────────────────────────────────┐
                          │ 12. Cache Result               │
                          │     TTL: 24 hours              │
                          └────────────┬───────────────────┘
                                       ▼
                                ┌──────────┐
                                │ Complete │
                                └──────────┘
                                       ▲
                                       │
┌─────────────┐                       │
│   User UI   │ ──────────────────────┘
│  Polls      │   GET /api/v1/master/status/{query_id}
│  /status    │   Returns: Complete result with report_url
└─────────────┘
```

## LLM Routing Decision Tree

```
                    ┌──────────────────┐
                    │  LLM Call Needed │
                    └─────────┬────────┘
                              │
                    ┌─────────▼─────────┐
                    │ Check: sensitive  │
                    │ flag OR           │
                    │ internal_doc_ids  │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Is Sensitive?   │
                    └─────────┬─────────┘
                              │
              ┌───────Yes─────┼─────No─────┐
              │                             │
              ▼                             ▼
    ┌──────────────────┐        ┌──────────────────┐
    │   Route to       │        │ Check prompt hash│
    │   Bolt LLM       │        │ in cache         │
    │   (Internal)     │        └─────────┬────────┘
    └────────┬─────────┘                  │
             │                    ┌────Yes┴No────┐
             │                    │               │
             │                    ▼               ▼
             │            ┌──────────────┐ ┌──────────────┐
             │            │Return Cached │ │Try OpenAI    │
             │            │Response      │ │              │
             │            └──────────────┘ └──────┬───────┘
             │                                    │
             │                            ┌───────▼───────┐
             │                            │  OpenAI OK?   │
             │                            └───────┬───────┘
             │                                    │
             │                         ┌────Yes───┼───No────┐
             │                         │                     │
             │                         ▼                     ▼
             │                ┌──────────────┐    ┌──────────────┐
             │                │Use OpenAI    │    │Try Anthropic │
             │                │Response      │    │              │
             │                └──────┬───────┘    └──────┬───────┘
             │                       │                   │
             │                       │                   ▼
             │                       │          ┌──────────────┐
             │                       │          │Use Anthropic │
             │                       │          │Response      │
             │                       │          └──────┬───────┘
             │                       │                 │
             └───────────────────────┴─────────────────┘
                                     │
                                     ▼
                        ┌────────────────────────┐
                        │  Grounding Checker     │
                        │  - Verify references   │
                        │  - Compute confidence  │
                        └────────────┬───────────┘
                                     │
                                     ▼
                        ┌────────────────────────┐
                        │  Return to Caller      │
                        │  {content, grounding,  │
                        │   provider, confidence}│
                        └────────────────────────┘
```

## Circuit Breaker State Transitions

```
                        ┌──────────────┐
                        │   CLOSED     │
                        │ (Normal ops) │
                        └──────┬───────┘
                               │
                    ┌──────────▼──────────┐
                    │ External API Call   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Success?          │
                    └──────────┬──────────┘
                               │
                    ┌─────Yes──┼──No──────┐
                    │                      │
                    ▼                      ▼
            ┌──────────────┐      ┌──────────────┐
            │Reset Failure │      │Increment     │
            │Counter to 0  │      │Failure Count │
            └──────┬───────┘      └──────┬───────┘
                   │                     │
                   │              ┌──────▼───────┐
                   │              │ Failures >= 5│
                   │              │ in 5 min?    │
                   │              └──────┬───────┘
                   │                     │
                   │          ┌────Yes───┼───No────┐
                   │          │                     │
                   │          ▼                     │
                   │  ┌──────────────┐             │
                   │  │   OPEN       │             │
                   │  │ (Block all)  │◄────────────┘
                   │  └──────┬───────┘
                   │         │
                   │         │ Wait 10 minutes
                   │         │
                   │         ▼
                   │  ┌──────────────┐
                   │  │  HALF_OPEN   │
                   │  │ (Test mode)  │
                   │  └──────┬───────┘
                   │         │
                   │  ┌──────▼───────┐
                   │  │ Single test  │
                   │  │ request      │
                   │  └──────┬───────┘
                   │         │
                   │  ┌──────▼───────┐
                   │  │  Success?    │
                   │  └──────┬───────┘
                   │         │
                   │  ┌──Yes─┼─No──┐
                   │  │            │
                   └──┘            └──► Back to OPEN
                                       (10 min wait)
```

## Cache Strategy - Three Tier Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Incoming Request                      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────────┐
        │ TIER 1: Query-Level Cache              │
        │ Key: pharma:query:{canonical_key}      │
        │ TTL: 24 hours                          │
        │ Contains: Complete aggregated result   │
        └────────────┬───────────────────────────┘
                     │
            ┌────Hit─┼─Miss────┐
            │                  │
            ▼                  ▼
    ┌──────────────┐   ┌────────────────────────────┐
    │Return Cached │   │ TIER 2: Worker-Level Cache │
    │Result        │   │ Key: pharma:worker:{name}: │
    │              │   │      {molecule}:{params}   │
    │Cache Hit:    │   │ TTL: 12 hours              │
    │TRUE          │   │ Contains: Worker-specific  │
    └──────────────┘   │          results           │
                       └────────────┬───────────────┘
                                    │
                           ┌────Hit─┼─Miss────┐
                           │                  │
                           ▼                  ▼
                   ┌──────────────┐   ┌────────────────────┐
                   │Use Cached    │   │Execute Worker      │
                   │Worker Result │   │Call External API   │
                   └──────────────┘   └────────┬───────────┘
                                                │
                                                ▼
                                       ┌────────────────────┐
                                       │Cache Worker Result │
                                       │(Tier 2)            │
                                       └────────┬───────────┘
                                                │
                                                ▼
                              ┌──────────────────────────────┐
                              │ TIER 3: LLM Response Cache   │
                              │ Key: llm:{prompt_hash}       │
                              │ TTL: 7 days                  │
                              │ Contains: Generated text +   │
                              │          grounding metadata  │
                              └──────────────────────────────┘
```

## Security & PII Flow

```
                    ┌──────────────────┐
                    │ User Input Text  │
                    └─────────┬────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ PII Detector     │
                    │ Scan for:        │
                    │ - Email          │
                    │ - Phone          │
                    │ - SSN            │
                    │ - Credit Card    │
                    └─────────┬────────┘
                              │
                    ┌─────────▼─────────┐
                    │  PII Detected?    │
                    └─────────┬─────────┘
                              │
                    ┌────Yes──┼──No─────┐
                    │                   │
                    ▼                   ▼
          ┌──────────────────┐  ┌──────────────┐
          │ Redact PII       │  │ Pass through │
          │ Replace with:    │  │ unchanged    │
          │ [REDACTED_EMAIL] │  └──────┬───────┘
          │ [REDACTED_PHONE] │         │
          └────────┬─────────┘         │
                   │                   │
                   └─────────┬─────────┘
                             │
                    ┌────────▼────────┐
                    │ Check sensitive │
                    │ flag            │
                    └────────┬────────┘
                             │
                    ┌───Yes──┼──No────┐
                    │                 │
                    ▼                 ▼
          ┌──────────────────┐ ┌────────────────┐
          │ Route to Bolt    │ │ OK for external│
          │ LLM (Internal)   │ │ LLM providers  │
          └──────────────────┘ └────────────────┘
```

## Monitoring & Metrics Flow

```
┌──────────────────────────────────────────────────────────┐
│              Application Layer                            │
│  FastAPI endpoints, Celery workers, LLM calls            │
└────────────────────────┬─────────────────────────────────┘
                         │
                         │ Emit metrics via
                         │ prometheus_client
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│              /metrics Endpoint                            │
│  Exposes Prometheus-formatted metrics                    │
│  - http_requests_total                                   │
│  - http_request_duration_seconds                         │
│  - celery_queue_depth                                    │
│  - llm_calls_total                                       │
│  - circuit_breaker_state                                 │
└────────────────────────┬─────────────────────────────────┘
                         │
                         │ Scraped every 15s
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│              Prometheus Server                            │
│  Time-series database                                    │
│  Stores all metrics with timestamps                      │
└────────────────────────┬─────────────────────────────────┘
                         │
                         │ Queried by
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│              Grafana Dashboard                            │
│  Visualizations:                                         │
│  - Line charts (throughput over time)                   │
│  - Gauges (current queue depth)                         │
│  - Heatmaps (latency distribution)                      │
│  - Alerts (configured thresholds)                       │
└──────────────────────────────────────────────────────────┘
                         │
                         │ Alerts sent to
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│              Alert Manager                                │
│  - Email notifications                                   │
│  - Slack webhooks                                        │
│  - PagerDuty integration                                │
└──────────────────────────────────────────────────────────┘
```

## Database Schema Relationships

```
┌─────────────────────┐
│       users         │
│───────────────────── │
│ id (PK)            │◄────────┐
│ email              │         │
│ hashed_password    │         │
│ role               │         │
│ created_at         │         │
└─────────────────────┘         │
                                │
                                │ user_id (FK)
                                │
┌─────────────────────────────────────────┐
│          search_requests                │
│─────────────────────────────────────────│
│ id (PK)                                │◄────┐
│ user_id (FK) ──────────────────────────┘    │
│ query_id (UNIQUE)                           │
│ molecule                                    │
│ indications (JSON)                          │
│ countries (JSON)                            │
│ sensitive (BOOLEAN)                         │
│ status (ENUM)                               │
│ opportunity_score                           │
│ summary (JSON)                              │
│ report_url                                  │
│ created_at                                  │
└─────────────────────────────────────────────┘
                                              │
                                              │ search_request_id (FK)
                                              │
┌────────────────────────────────────────────────────┐
│              worker_results                        │
│────────────────────────────────────────────────────│
│ id (PK)                                           │
│ search_request_id (FK) ───────────────────────────┘
│ worker_name                                       │
│ status (ENUM)                                     │
│ data (JSON)                                       │
│ references (JSON)                                 │
│ confidence                                        │
│ execution_time_ms                                 │
│ created_at                                        │
└────────────────────────────────────────────────────┘

┌─────────────────────┐
│    audit_logs       │
│─────────────────────│
│ id (PK)            │
│ user_id (FK)       │
│ event_type         │
│ action             │
│ details (JSON)     │
│ created_at         │
└─────────────────────┘

┌──────────────────────────┐
│  internal_documents      │
│──────────────────────────│
│ id (PK)                 │
│ doc_id (UNIQUE)         │
│ title                   │
│ file_path               │
│ content_text            │
│ is_sensitive            │
│ created_at              │
└──────────────────────────┘

┌───────────────────────────┐
│ circuit_breaker_states    │
│───────────────────────────│
│ id (PK)                  │
│ service_name (UNIQUE)    │
│ state                    │
│ failure_count            │
│ last_failure_time        │
│ next_retry_time          │
└───────────────────────────┘

┌─────────────────────┐
│     llm_calls       │
│─────────────────────│
│ id (PK)            │
│ provider           │
│ model              │
│ prompt_hash        │
│ tokens_used        │
│ is_sensitive       │
│ cache_hit          │
│ created_at         │
└─────────────────────┘
```

---

**These diagrams illustrate the complete data flow through the system. Use them to understand how components interact and where to implement new features.**
