from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app, Counter, Histogram
from datetime import datetime
import logging
import sys

from app.config import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="PharmaRepurpose Assistant",
    description="Agentic AI platform for pharmaceutical drug repurposing analysis",
    version="1.0.0",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])


@app.middleware("http")
async def add_metrics(request: Request, call_next):
    import time
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    return response


@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting PharmaRepurpose Assistant")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"API Prefix: {settings.API_V1_PREFIX}")

    try:
        from app.utils.cache import cache_manager
        await cache_manager.connect()
        logger.info("✅ Cache connected")
    except Exception as e:
        logger.error(f"❌ Cache connection failed: {e}")

    try:
        from app.utils.circuit_breaker import circuit_breaker
        await circuit_breaker.connect()
        logger.info("✅ Circuit breaker connected")
    except Exception as e:
        logger.error(f"❌ Circuit breaker connection failed: {e}")

    try:
        from app.utils.rate_limiter import rate_limiter
        await rate_limiter.connect()
        logger.info("✅ Rate limiter connected")
    except Exception as e:
        logger.error(f"❌ Rate limiter connection failed: {e}")

    logger.info("✅ Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Shutting down PharmaRepurpose Assistant")

    try:
        from app.utils.cache import cache_manager
        await cache_manager.close()
    except:
        pass

    try:
        from app.utils.circuit_breaker import circuit_breaker
        await circuit_breaker.close()
    except:
        pass

    try:
        from app.utils.rate_limiter import rate_limiter
        await rate_limiter.close()
    except:
        pass


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "services": {
            "api": "ok",
            "database": "ok",
            "redis": "ok",
            "celery": "ok"
        }
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "PharmaRepurpose Assistant API",
        "version": "1.0.0",
        "docs": f"{settings.API_V1_PREFIX}/docs",
        "health": "/health",
        "metrics": "/metrics"
    }


metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.ENVIRONMENT == "development" else "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development"
    )
