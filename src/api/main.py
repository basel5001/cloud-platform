"""Internal Developer Platform — FastAPI application."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.ai import advisor as ai_advisor
from src.api.database import Database
from src.api.models import (
    AIRequest,
    AIResponse,
    CostReport,
    Environment,
    EnvironmentCreate,
    Service,
    ServiceCreate,
)
from src.provisioner import terraform

load_dotenv()

logger = logging.getLogger("platform")

# ---------------------------------------------------------------------------
# Database singleton
# ---------------------------------------------------------------------------
db = Database()


# ---------------------------------------------------------------------------
# App lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Platform API starting up")
    yield
    logger.info("Platform API shutting down")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Internal Developer Platform",
    description="Self-service infrastructure provisioning, service catalog, and AI-powered recommendations.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "..", "dashboard")


@app.get("/", include_in_schema=False)
async def dashboard():
    return FileResponse(os.path.join(DASHBOARD_DIR, "index.html"))


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

@app.post("/api/services", response_model=Service, status_code=status.HTTP_201_CREATED, tags=["services"])
async def create_service(payload: ServiceCreate) -> Any:
    try:
        row = db.create_service(
            name=payload.name,
            svc_type=payload.type.value,
            owner=payload.owner,
            repo_url=str(payload.repo_url),
        )
    except Exception as exc:
        if "UNIQUE" in str(exc):
            raise HTTPException(status_code=409, detail=f"Service '{payload.name}' already exists")
        raise HTTPException(status_code=500, detail=str(exc))
    return row


@app.get("/api/services", response_model=list[Service], tags=["services"])
async def list_services() -> Any:
    return db.list_services()


@app.get("/api/services/{service_id}", response_model=Service, tags=["services"])
async def get_service(service_id: int) -> Any:
    row = db.get_service(service_id)
    if not row:
        raise HTTPException(status_code=404, detail="Service not found")
    return row


# ---------------------------------------------------------------------------
# Environments
# ---------------------------------------------------------------------------

@app.post("/api/environments", response_model=Environment, status_code=status.HTTP_201_CREATED, tags=["environments"])
async def create_environment(payload: EnvironmentCreate) -> Any:
    svc = db.get_service(payload.service_id)
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    try:
        env_row = db.create_environment(
            service_id=payload.service_id,
            name=payload.name.value,
            region=payload.region,
        )
    except Exception as exc:
        if "UNIQUE" in str(exc):
            raise HTTPException(
                status_code=409,
                detail=f"Environment '{payload.name.value}' already exists for this service",
            )
        raise HTTPException(status_code=500, detail=str(exc))

    # Trigger Terraform provisioning in background (non-blocking for demo)
    workspace = f"{svc['name']}-{payload.name.value}"
    try:
        terraform.plan(workspace, variables={
            "service_name": svc["name"],
            "service_type": svc["type"],
            "environment": payload.name.value,
            "region": payload.region,
        })
        db.update_environment_status(env_row["id"], "running")
        env_row["status"] = "running"
    except Exception:
        logger.exception("Terraform provisioning failed for %s", workspace)
        db.update_environment_status(env_row["id"], "failed")
        env_row["status"] = "failed"

    return env_row


@app.get("/api/environments", response_model=list[Environment], tags=["environments"])
async def list_environments() -> Any:
    return db.list_environments()


@app.delete("/api/environments/{env_id}", tags=["environments"])
async def destroy_environment(env_id: int) -> dict[str, str]:
    env = db.get_environment(env_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")

    if not db.delete_environment(env_id):
        raise HTTPException(status_code=400, detail="Environment already destroyed")

    svc = db.get_service(env["service_id"])
    if not svc:
        raise HTTPException(status_code=404, detail="Parent service not found")
    workspace = f"{svc['name']}-{env['name']}"
    try:
        terraform.destroy(workspace)
        db.update_environment_status(env_id, "destroyed")
    except Exception:
        logger.exception("Terraform destroy failed for %s", workspace)
        db.update_environment_status(env_id, "failed")

    return {"detail": "Environment destruction initiated"}


# ---------------------------------------------------------------------------
# AI advisor
# ---------------------------------------------------------------------------

@app.post("/api/ai/suggest", response_model=AIResponse, tags=["ai"])
async def ai_suggest(payload: AIRequest) -> Any:
    try:
        answer, tokens = ai_advisor.suggest_infrastructure(payload.prompt)
    except Exception as exc:
        logger.exception("Bedrock invocation failed")
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")
    return AIResponse(
        answer=answer,
        model=os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"),
        usage_tokens=tokens,
    )


# ---------------------------------------------------------------------------
# Cost tracking
# ---------------------------------------------------------------------------

@app.get("/api/costs", response_model=CostReport, tags=["costs"])
async def get_costs() -> Any:
    """Return cost summary. Uses AWS Cost Explorer when credentials are available,
    otherwise returns a placeholder report."""
    try:
        import boto3

        ce = boto3.client("ce", region_name=os.getenv("AWS_REGION", "us-east-1"))
        from datetime import datetime, timedelta

        end = datetime.utcnow().strftime("%Y-%m-%d")
        start = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")

        result = ce.get_cost_and_usage(
            TimePeriod={"Start": start, "End": end},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "TAG", "Key": "Service"}],
        )
        breakdown = []
        total = 0.0
        for group in result.get("ResultsByTime", [{}])[0].get("Groups", []):
            amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
            total += amount
            breakdown.append({
                "service_name": group["Keys"][0],
                "environment": "all",
                "amount": round(amount, 2),
                "currency": "USD",
                "period": f"{start}/{end}",
            })
        return CostReport(total=round(total, 2), period=f"{start}/{end}", breakdown=breakdown)
    except Exception:
        return CostReport(total=0.0, period="last-30-days", breakdown=[])
