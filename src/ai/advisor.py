"""AWS Bedrock AI advisor for infrastructure recommendations."""

from __future__ import annotations

import json
import os
from typing import Any

import boto3


def _get_client():
    """Return a boto3 Bedrock Runtime client."""
    return boto3.client(
        "bedrock-runtime",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )


def _invoke(prompt: str, system: str = "") -> tuple[str, int]:
    """Send a prompt to the Bedrock Claude model and return (response_text, token_count)."""
    client = _get_client()
    model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]

    body: dict[str, Any] = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2048,
        "messages": messages,
    }
    if system:
        body["system"] = system

    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )

    result = json.loads(response["body"].read())
    text = result.get("content", [{}])[0].get("text", "")
    tokens = result.get("usage", {}).get("input_tokens", 0) + result.get("usage", {}).get(
        "output_tokens", 0
    )
    return text, tokens


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def suggest_infrastructure(description: str) -> tuple[str, int]:
    """Given a service description, return infrastructure recommendations.

    Returns:
        Tuple of (recommendation_text, total_tokens_used).
    """
    system = (
        "You are an expert AWS solutions architect. Given a service description, "
        "recommend the best AWS services, sizing, networking layout, and estimated "
        "monthly cost. Be specific and actionable. Format your answer in Markdown."
    )
    return _invoke(description, system=system)


def generate_terraform(service_type: str, env: str) -> tuple[str, int]:
    """Generate Terraform HCL for a given service type and environment.

    Returns:
        Tuple of (terraform_code, total_tokens_used).
    """
    prompt = (
        f"Generate production-ready Terraform code (HCL) to deploy a '{service_type}' "
        f"service in a '{env}' environment on AWS. Include ECS Fargate or Lambda "
        f"(based on service type), ALB, CloudWatch logging, and IAM roles. "
        f"Use best practices for tagging and security."
    )
    system = (
        "You are a Terraform expert. Return ONLY valid Terraform HCL code. "
        "Include comments explaining each resource."
    )
    return _invoke(prompt, system=system)


def explain_cost(cost_data: dict) -> tuple[str, int]:
    """Explain a cost breakdown in plain English.

    Returns:
        Tuple of (explanation_text, total_tokens_used).
    """
    prompt = (
        f"Explain the following AWS cost breakdown in plain English. "
        f"Highlight any anomalies or optimization opportunities.\n\n"
        f"```json\n{json.dumps(cost_data, indent=2)}\n```"
    )
    system = "You are a FinOps advisor. Be concise and highlight actionable savings."
    return _invoke(prompt, system=system)
