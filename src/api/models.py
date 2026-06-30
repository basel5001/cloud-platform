"""Pydantic models for the Internal Developer Platform API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ServiceType(str, Enum):
    WEB = "web"
    API = "api"
    WORKER = "worker"


class EnvironmentName(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class EnvironmentStatus(str, Enum):
    PROVISIONING = "provisioning"
    RUNNING = "running"
    DESTROYING = "destroying"
    DESTROYED = "destroyed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9-]*$")
    type: ServiceType
    owner: str = Field(..., min_length=1, max_length=128)
    repo_url: str = Field(..., min_length=1)


class Service(BaseModel):
    id: int
    name: str
    type: ServiceType
    owner: str
    repo_url: str
    created_at: str


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

class EnvironmentCreate(BaseModel):
    service_id: int
    name: EnvironmentName
    region: str = Field(default="us-east-1")


class Environment(BaseModel):
    id: int
    service_id: int
    name: EnvironmentName
    status: EnvironmentStatus
    region: str
    created_at: str
    destroyed_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Cost
# ---------------------------------------------------------------------------

class CostEntry(BaseModel):
    service_name: str
    environment: str
    amount: float
    currency: str = "USD"
    period: str


class CostReport(BaseModel):
    total: float
    currency: str = "USD"
    period: str
    breakdown: list[CostEntry] = []


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------

class AIRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4096)


class AIResponse(BaseModel):
    answer: str
    model: str
    usage_tokens: int = 0
