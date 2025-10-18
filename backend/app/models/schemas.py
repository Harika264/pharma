from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    RESEARCHER = "researcher"
    VIEWER = "viewer"


class QueryStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEGRADED = "degraded"


class WorkerStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"
    TIMEOUT = "timeout"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[UserRole] = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.RESEARCHER


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class QueryRequest(BaseModel):
    query_id: Optional[str] = None
    molecule: str = Field(..., min_length=1, max_length=255)
    indications: List[str] = Field(default_factory=list)
    countries: List[str] = Field(default_factory=list, max_items=20)
    sensitive: bool = False
    internal_doc_ids: List[str] = Field(default_factory=list)
    report_format: str = Field(default="pdf", pattern="^(pdf|excel|ppt)$")

    @validator('countries')
    def validate_countries(cls, v):
        valid_countries = {'IN', 'US', 'GB', 'DE', 'FR', 'CN', 'JP', 'BR', 'AU', 'CA'}
        for country in v:
            if country not in valid_countries:
                raise ValueError(f'Invalid country code: {country}')
        return v


class QueryResponse(BaseModel):
    query_id: str
    status: QueryStatus
    progress_url: str


class WorkerResultData(BaseModel):
    worker: str
    status: WorkerStatus
    data: Dict[str, Any]
    references: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    execution_time_ms: Optional[int] = None
    error_message: Optional[str] = None


class QueryStatusResponse(BaseModel):
    query_id: str
    status: QueryStatus
    molecule: str
    indications: List[str]
    countries: List[str]

    worker_results: List[WorkerResultData] = Field(default_factory=list)

    opportunity_score: Optional[float] = None
    summary: Optional[Dict[str, Any]] = None
    report_url: Optional[str] = None

    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str]


class Reference(BaseModel):
    source: str
    url: Optional[str] = None
    doc_id: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_found: bool = True


class ClinicalTrialData(BaseModel):
    id: str
    title: str
    phase: str
    status: str
    country: str
    sponsor: str
    results_summary: Optional[str] = None
    url: str


class ClinicalWorkerResponse(BaseModel):
    trials: List[ClinicalTrialData]
    clinical_signal_score: float = Field(ge=0.0, le=1.0)


class PatentData(BaseModel):
    patent_number: str
    title: str
    applicant: str
    filing_date: str
    status: str
    claims_summary: Optional[str] = None
    url: str


class PatentWorkerResponse(BaseModel):
    patents: List[PatentData]
    fto_flags: List[str]
    ip_risk_score: float = Field(ge=0.0, le=1.0)


class MarketData(BaseModel):
    market_size_usd: float
    cagr: float
    competitors: List[str]
    market_trend: str


class IQVIAWorkerResponse(BaseModel):
    market: MarketData
    unmet_gap_score: float = Field(ge=0.0, le=1.0)


class TradeData(BaseModel):
    import_dependency_pct: float
    top_sources: List[Dict[str, Any]]
    trend_timeseries: List[Dict[str, Any]]


class EXIMWorkerResponse(BaseModel):
    trade: TradeData


class Publication(BaseModel):
    title: str
    authors: List[str]
    journal: Optional[str] = None
    year: int
    doi: Optional[str] = None
    url: str
    summary: Optional[str] = None


class WebIntelWorkerResponse(BaseModel):
    publications: List[Publication]
    guidelines: List[Dict[str, Any]]
    news: List[Dict[str, Any]]


class InternalDocSummary(BaseModel):
    doc_id: str
    title: str
    key_takeaways: List[str]
    relevance_score: float = Field(ge=0.0, le=1.0)
    extraction_offsets: List[Dict[str, int]]


class InternalWorkerResponse(BaseModel):
    summaries: List[InternalDocSummary]
    relevance_score: float = Field(ge=0.0, le=1.0)


class ReportMetadata(BaseModel):
    s3_path: str
    format: str
    generated_at: datetime
    slides_count: Optional[int] = None
    file_size_bytes: int


class ReportWorkerResponse(BaseModel):
    s3_path: str
    slides_meta: Optional[Dict[str, Any]] = None
