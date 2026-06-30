"""Terraform CLI wrapper for provisioning infrastructure."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


TERRAFORM_DIR = os.getenv(
    "TERRAFORM_DIR",
    str(Path(__file__).resolve().parent.parent.parent / "terraform"),
)


def _run(
    args: list[str],
    workspace: str,
    *,
    capture: bool = True,
) -> subprocess.CompletedProcess:
    """Execute a terraform command inside *workspace* directory.

    The workspace directory is created under TERRAFORM_DIR/workspaces/<workspace>.
    """
    ws_dir = Path(TERRAFORM_DIR) / "workspaces" / workspace
    ws_dir.mkdir(parents=True, exist_ok=True)

    env = {**os.environ, "TF_IN_AUTOMATION": "1"}

    return subprocess.run(
        ["terraform", *args],
        cwd=str(ws_dir),
        capture_output=capture,
        text=True,
        env=env,
        timeout=600,
    )


def init(workspace: str) -> str:
    """Run ``terraform init`` for a workspace.

    Returns:
        Combined stdout/stderr.
    """
    result = _run(["init", "-input=false", "-no-color"], workspace)
    return result.stdout + result.stderr


def plan(workspace: str, variables: dict[str, str] | None = None) -> str:
    """Run ``terraform plan`` and return the plan output.

    Args:
        workspace: Logical workspace name (maps to a directory).
        variables: Key/value pairs passed as ``-var`` flags.

    Returns:
        The plan output text.
    """
    init(workspace)

    args = ["plan", "-input=false", "-no-color"]
    for key, value in (variables or {}).items():
        args.extend(["-var", f"{key}={value}"])

    result = _run(args, workspace)
    return result.stdout + result.stderr


def apply(workspace: str) -> str:
    """Run ``terraform apply -auto-approve``.

    Returns:
        Combined stdout/stderr.
    """
    init(workspace)
    result = _run(["apply", "-auto-approve", "-input=false", "-no-color"], workspace)
    return result.stdout + result.stderr


def destroy(workspace: str) -> str:
    """Run ``terraform destroy -auto-approve``.

    Returns:
        Combined stdout/stderr.
    """
    result = _run(["destroy", "-auto-approve", "-input=false", "-no-color"], workspace)
    return result.stdout + result.stderr


def get_output(workspace: str) -> dict[str, Any]:
    """Return parsed ``terraform output -json``.

    Returns:
        Dict of output name -> value.
    """
    result = _run(["output", "-json", "-no-color"], workspace)
    if result.returncode != 0:
        return {}
    try:
        raw = json.loads(result.stdout)
        return {k: v.get("value") for k, v in raw.items()}
    except (json.JSONDecodeError, AttributeError):
        return {}
