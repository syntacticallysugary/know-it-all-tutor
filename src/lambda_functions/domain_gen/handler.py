"""Domain generation job queue Lambda.

POST /domains/generate          — create a pending job (admin only)
GET  /domains/generate          — list all jobs (admin only)
GET  /domains/generate/{id}     — get job status + output path (admin only)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

sys.path.append("/opt/python")

from db_proxy_client import DBProxyClient
from response_utils import create_response, create_error_response
from auth_utils import extract_user_from_cognito_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

db = DBProxyClient(os.environ.get("DB_PROXY_FUNCTION_NAME"))


def _require_admin(event: dict[str, Any]) -> bool:
    """Return True if the caller is in the admin Cognito group."""
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    groups_str = claims.get("cognito:groups", "")
    groups = groups_str.split(",") if groups_str else []
    return "admin" in groups


def _create_job(event: dict[str, Any]) -> dict[str, Any]:
    """Create a new pending domain generation job."""
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return create_error_response(400, "Invalid JSON body")

    topic = (body.get("topic") or "").strip()
    if not topic:
        return create_error_response(400, "topic is required")

    hints = (body.get("hints") or "").strip()
    total_terms = body.get("total_terms", 50)
    if not isinstance(total_terms, int) or total_terms < 1 or total_terms > 200:
        return create_error_response(400, "total_terms must be an integer between 1 and 200")

    result = db.execute_query(
        """
        INSERT INTO domain_gen_jobs (topic, hints, total_terms, status)
        VALUES (%s, %s, %s, 'pending')
        RETURNING id, topic, hints, total_terms, status, created_at
        """,
        params=[topic, hints, total_terms],
        return_dict=True,
    )
    row = result[0] if result else None
    if not row:
        return create_error_response(500, "Failed to create job")

    return create_response(201, _format_job(row))


def _list_jobs(event: dict[str, Any]) -> dict[str, Any]:
    """Return all jobs ordered newest first."""
    rows = db.execute_query(
        """
        SELECT id, topic, hints, total_terms, status, output_path,
               error_message, created_at, updated_at
        FROM domain_gen_jobs
        ORDER BY created_at DESC
        LIMIT 100
        """,
        return_dict=True,
    )
    return create_response(200, {"jobs": [_format_job(r) for r in (rows or [])]})


def _get_job(job_id: str) -> dict[str, Any]:
    """Return one job by ID."""
    try:
        jid = int(job_id)
    except (ValueError, TypeError):
        return create_error_response(400, "Invalid job id")

    rows = db.execute_query(
        """
        SELECT id, topic, hints, total_terms, status, output_path,
               error_message, created_at, updated_at
        FROM domain_gen_jobs
        WHERE id = %s
        """,
        params=[jid],
        return_dict=True,
    )
    if not rows:
        return create_error_response(404, "Job not found")
    return create_response(200, _format_job(rows[0]))


def _format_job(row: dict) -> dict:
    """Serialize a DB row to a JSON-safe dict."""
    return {
        "id": row["id"],
        "topic": row["topic"],
        "hints": row["hints"],
        "total_terms": row["total_terms"],
        "status": row["status"],
        "output_path": row.get("output_path"),
        "error_message": row.get("error_message"),
        "created_at": str(row["created_at"]),
        "updated_at": str(row.get("updated_at", "")),
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Route dispatcher for domain generation endpoints."""
    if not _require_admin(event):
        return create_error_response(403, "Admin access required")

    method = event.get("httpMethod", "")
    path_params = event.get("pathParameters") or {}
    job_id = path_params.get("id")

    try:
        if method == "POST":
            return _create_job(event)
        if method == "GET" and job_id:
            return _get_job(job_id)
        if method == "GET":
            return _list_jobs(event)
        return create_error_response(405, "Method not allowed")
    except Exception as exc:
        logger.exception("Unhandled error in domain_gen handler")
        return create_error_response(500, str(exc))
