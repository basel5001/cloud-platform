"""Tests for the Internal Developer Platform API."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path, monkeypatch):
    """Use a temporary SQLite database for every test."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    # Re-import to pick up the env change
    import importlib
    import src.api.database as db_mod
    import src.api.main as main_mod
    importlib.reload(db_mod)
    importlib.reload(main_mod)


@pytest.fixture
def client():
    from src.api.main import app
    return TestClient(app)


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


# ------------------------------------------------------------------
# Services – CRUD
# ------------------------------------------------------------------

def test_create_service(client):
    payload = {
        "name": "payment-api",
        "type": "api",
        "owner": "platform-team",
        "repo_url": "https://github.com/org/payment-api",
    }
    resp = client.post("/api/services", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "payment-api"
    assert data["type"] == "api"
    assert data["owner"] == "platform-team"
    assert "id" in data


def test_list_services_empty(client):
    resp = client.get("/api/services")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_services_after_create(client):
    client.post("/api/services", json={
        "name": "web-frontend",
        "type": "web",
        "owner": "ui-team",
        "repo_url": "https://github.com/org/web-frontend",
    })
    resp = client.get("/api/services")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_service_by_id(client):
    create_resp = client.post("/api/services", json={
        "name": "worker-svc",
        "type": "worker",
        "owner": "data-team",
        "repo_url": "https://github.com/org/worker",
    })
    svc_id = create_resp.json()["id"]
    resp = client.get(f"/api/services/{svc_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "worker-svc"


def test_get_service_not_found(client):
    resp = client.get("/api/services/9999")
    assert resp.status_code == 404


def test_create_service_duplicate_name(client):
    payload = {
        "name": "dup-service",
        "type": "api",
        "owner": "team",
        "repo_url": "https://github.com/org/dup",
    }
    client.post("/api/services", json=payload)
    resp = client.post("/api/services", json=payload)
    assert resp.status_code == 409


def test_create_service_validation_error(client):
    resp = client.post("/api/services", json={
        "name": "",
        "type": "api",
        "owner": "team",
        "repo_url": "https://github.com/org/repo",
    })
    assert resp.status_code == 422


def test_create_service_invalid_type(client):
    resp = client.post("/api/services", json={
        "name": "my-service",
        "type": "invalid",
        "owner": "team",
        "repo_url": "https://github.com/org/repo",
    })
    assert resp.status_code == 422


# ------------------------------------------------------------------
# Environments
# ------------------------------------------------------------------

@patch("src.provisioner.terraform.plan", return_value="Plan: 3 to add")
@patch("src.provisioner.terraform.init", return_value="Initialized")
def test_create_environment(mock_init, mock_plan, client):
    svc = client.post("/api/services", json={
        "name": "env-test-svc",
        "type": "api",
        "owner": "team",
        "repo_url": "https://github.com/org/repo",
    }).json()

    resp = client.post("/api/environments", json={
        "service_id": svc["id"],
        "name": "dev",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "dev"
    assert data["status"] in ("running", "provisioning", "failed")


def test_create_environment_service_not_found(client):
    resp = client.post("/api/environments", json={
        "service_id": 9999,
        "name": "dev",
    })
    assert resp.status_code == 404


def test_list_environments_empty(client):
    resp = client.get("/api/environments")
    assert resp.status_code == 200
    assert resp.json() == []


@patch("src.provisioner.terraform.plan", return_value="Plan: 3 to add")
@patch("src.provisioner.terraform.init", return_value="Initialized")
@patch("src.provisioner.terraform.destroy", return_value="Destroyed")
def test_destroy_environment(mock_destroy, mock_init, mock_plan, client):
    svc = client.post("/api/services", json={
        "name": "destroy-test",
        "type": "web",
        "owner": "team",
        "repo_url": "https://github.com/org/repo",
    }).json()

    env = client.post("/api/environments", json={
        "service_id": svc["id"],
        "name": "dev",
    }).json()

    resp = client.delete(f"/api/environments/{env['id']}")
    assert resp.status_code == 200


def test_destroy_environment_not_found(client):
    resp = client.delete("/api/environments/9999")
    assert resp.status_code == 404


# ------------------------------------------------------------------
# AI Advisor
# ------------------------------------------------------------------

@patch("src.ai.advisor.suggest_infrastructure")
def test_ai_suggest(mock_suggest, client):
    mock_suggest.return_value = ("Use ECS Fargate with ALB", 150)
    resp = client.post("/api/ai/suggest", json={
        "prompt": "I need a web service that handles 1000 rps",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "ECS Fargate" in data["answer"]
    assert data["usage_tokens"] == 150


def test_ai_suggest_empty_prompt(client):
    resp = client.post("/api/ai/suggest", json={"prompt": ""})
    assert resp.status_code == 422


# ------------------------------------------------------------------
# Costs
# ------------------------------------------------------------------

def test_costs_returns_report(client):
    resp = client.get("/api/costs")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "breakdown" in data
