from sqlalchemy import Column, String, Integer, DateTime, JSON, Float, Boolean, Text, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.models.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    RESEARCHER = "researcher"
    VIEWER = "viewer"


class QueryStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEGRADED = "degraded"


class WorkerStatus(str, enum.Enum):
    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"
    TIMEOUT = "timeout"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(Enum(UserRole), default=UserRole.RESEARCHER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    search_requests = relationship("SearchRequest", back_populates="user")


class SearchRequest(Base):
    __tablename__ = "search_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    query_id = Column(String(255), unique=True, index=True, nullable=False)

    molecule = Column(String(255), nullable=False, index=True)
    indications = Column(JSON)
    countries = Column(JSON)
    sensitive = Column(Boolean, default=False)
    internal_doc_ids = Column(JSON)
    report_format = Column(String(50), default="pdf")

    status = Column(Enum(QueryStatus), default=QueryStatus.PENDING, nullable=False, index=True)
    canonical_query_key = Column(String(255), index=True)

    opportunity_score = Column(Float)
    summary = Column(JSON)
    report_url = Column(String(500))

    error_message = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    user = relationship("User", back_populates="search_requests")
    worker_results = relationship("WorkerResult", back_populates="search_request")


class WorkerResult(Base):
    __tablename__ = "worker_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_request_id = Column(UUID(as_uuid=True), ForeignKey("search_requests.id"), nullable=False)

    worker_name = Column(String(100), nullable=False, index=True)
    status = Column(Enum(WorkerStatus), nullable=False)

    data = Column(JSON)
    references = Column(JSON)
    confidence = Column(Float)

    execution_time_ms = Column(Integer)
    error_message = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    search_request = relationship("SearchRequest", back_populates="worker_results")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    event_type = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100))
    entity_id = Column(String(255))

    action = Column(String(100), nullable=False)
    details = Column(JSON)

    ip_address = Column(String(45))
    user_agent = Column(String(500))

    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class InternalDocument(Base):
    __tablename__ = "internal_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    doc_id = Column(String(255), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False)
    file_path = Column(String(500), nullable=False)

    content_text = Column(Text)
    content_metadata = Column(JSON)

    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_sensitive = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CircuitBreakerState(Base):
    __tablename__ = "circuit_breaker_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    service_name = Column(String(100), unique=True, index=True, nullable=False)
    state = Column(String(50), nullable=False)
    failure_count = Column(Integer, default=0)
    last_failure_time = Column(DateTime)
    next_retry_time = Column(DateTime)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LLMCall(Base):
    __tablename__ = "llm_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    provider = Column(String(50), nullable=False, index=True)
    model = Column(String(100))
    prompt_hash = Column(String(64), index=True)

    tokens_used = Column(Integer)
    response_time_ms = Column(Integer)

    is_sensitive = Column(Boolean, default=False)
    cache_hit = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
