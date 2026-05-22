"""Domain generation job queue Lambda.

POST /domains/generate              — submit a domain request (any authenticated user)
GET  /domains/generate              — list caller's jobs (admin sees all)
GET  /domains/generate/{id}         — job status + output_json when complete
POST /domains/generate/{id}/approve — save approved terms to tree_nodes
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


def _cognito_sub(event: dict[str, Any]) -> str | None:
    """Return the Cognito sub (user UUID) from the authorizer claims."""
    user_info = extract_user_from_cognito_event(event)
    if not user_info.get("valid"):
        return None
    return user_info.get("user_id")


def _is_admin(event: dict[str, Any]) -> bool:
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    groups_str = claims.get("cognito:groups", "")
    groups = groups_str.split(",") if groups_str else []
    return "admin" in groups


def _db_user_id(cognito_sub: str) -> int | None:
    """Resolve Cognito sub to the integer DB user id."""
    rows = db.execute_query(
        "SELECT id FROM users WHERE cognito_sub = %s",
        params=[cognito_sub],
        return_dict=False,
    )
    return rows[0][0] if rows else None


def _format_job(row: dict, include_output: bool = False) -> dict:
    out = {
        "id":            str(row["id"]),
        "topic":         row["topic"],
        "hints":         row["hints"],
        "total_terms":   row["total_terms"],
        "status":        row["status"],
        "error_message": row.get("error_message"),
        "created_at":    str(row["created_at"]),
        "updated_at":    str(row.get("updated_at", "")),
    }
    if include_output:
        out["output_json"] = row.get("output_json")
    return out


def _create_job(event: dict[str, Any], sub: str) -> dict[str, Any]:
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return create_error_response(400, "Invalid JSON body")

    topic = (body.get("topic") or "").strip()
    if not topic:
        return create_error_response(400, "topic is required")
    if len(topic) > 200:
        return create_error_response(400, "topic must be 200 characters or fewer")

    hints = (body.get("hints") or "").strip()
    total_terms = body.get("total_terms", 50)
    if not isinstance(total_terms, int) or not (1 <= total_terms <= 200):
        return create_error_response(400, "total_terms must be an integer between 1 and 200")

    rows = db.execute_query(
        """
        INSERT INTO domain_gen_jobs (user_id, topic, hints, total_terms)
        VALUES (%s, %s, %s, %s)
        RETURNING id, user_id, topic, hints, total_terms, status, created_at, updated_at
        """,
        params=[sub, topic, hints, total_terms],
        return_dict=True,
    )
    if not rows:
        return create_error_response(500, "Failed to create job")
    return create_response(201, _format_job(rows[0]))


def _list_jobs(event: dict[str, Any], sub: str) -> dict[str, Any]:
    if _is_admin(event):
        rows = db.execute_query(
            """
            SELECT id, user_id, topic, hints, total_terms, status,
                   error_message, created_at, updated_at
            FROM domain_gen_jobs
            ORDER BY created_at DESC
            LIMIT 200
            """,
            return_dict=True,
        )
    else:
        rows = db.execute_query(
            """
            SELECT id, user_id, topic, hints, total_terms, status,
                   error_message, created_at, updated_at
            FROM domain_gen_jobs
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 100
            """,
            params=[sub],
            return_dict=True,
        )
    return create_response(200, {"jobs": [_format_job(r) for r in (rows or [])]})


def _get_job(job_id: str, sub: str, is_admin: bool) -> dict[str, Any]:
    rows = db.execute_query(
        """
        SELECT id, user_id, topic, hints, total_terms, status,
               output_json, error_message, created_at, updated_at
        FROM domain_gen_jobs
        WHERE id = %s
        """,
        params=[job_id],
        return_dict=True,
    )
    if not rows:
        return create_error_response(404, "Job not found")
    row = rows[0]
    if str(row["user_id"]) != sub and not is_admin:
        return create_error_response(403, "Access denied")
    return create_response(200, _format_job(row, include_output=True))


def _approve_job(job_id: str, sub: str, is_admin: bool) -> dict[str, Any]:
    """Save approved terms from a completed job into tree_nodes."""
    rows = db.execute_query(
        "SELECT id, user_id, status, output_json FROM domain_gen_jobs WHERE id = %s",
        params=[job_id],
        return_dict=True,
    )
    if not rows:
        return create_error_response(404, "Job not found")
    row = rows[0]
    if str(row["user_id"]) != sub and not is_admin:
        return create_error_response(403, "Access denied")
    if row["status"] != "complete":
        return create_error_response(400, f"Job is not complete (status: {row['status']})")
    if not row.get("output_json"):
        return create_error_response(400, "Job has no output to approve")

    db_user_id = _db_user_id(sub)
    if not db_user_id:
        return create_error_response(403, "User not found in database")

    output = row["output_json"]
    if isinstance(output, str):
        output = json.loads(output)

    domains_saved = 0
    terms_saved = 0

    for domain in output.get("domains", []):
        domain_data = domain.get("data", {})
        domain_meta = {"created_by": str(db_user_id), "source": "domain_gen"}

        domain_rows = db.execute_query(
            """
            INSERT INTO tree_nodes (id, user_id, node_type, data, metadata, is_public)
            VALUES (gen_random_uuid(), %s, 'domain', %s, %s, false)
            RETURNING id
            """,
            params=[db_user_id, json.dumps(domain_data), json.dumps(domain_meta)],
            return_dict=False,
        )
        if not domain_rows:
            continue
        domain_id = domain_rows[0][0]
        domains_saved += 1

        for term in domain.get("terms", []):
            term_data = term.get("data", {})
            term_meta = term.get("metadata", {})
            db.execute_query(
                """
                INSERT INTO tree_nodes (id, parent_id, user_id, node_type, data, metadata)
                VALUES (gen_random_uuid(), %s, %s, 'term', %s, %s)
                """,
                params=[domain_id, db_user_id, json.dumps(term_data), json.dumps(term_meta)],
                return_dict=False,
            )
            terms_saved += 1

    db.execute_query(
        "UPDATE domain_gen_jobs SET status = 'approved', updated_at = NOW() WHERE id = %s",
        params=[job_id],
        return_dict=False,
    )

    return create_response(200, {
        "message": "Domain saved to your library",
        "domains_saved": domains_saved,
        "terms_saved": terms_saved,
    })


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    sub = _cognito_sub(event)
    if not sub:
        return create_error_response(401, "Unauthorized")

    method = event.get("httpMethod", "")
    path_params = event.get("pathParameters") or {}
    job_id = path_params.get("id")
    is_admin = _is_admin(event)

    # POST /domains/generate/{id}/approve
    if method == "POST" and job_id:
        action = (event.get("pathParameters") or {}).get("action")
        path = event.get("path", "")
        if path.endswith("/approve"):
            return _approve_job(job_id, sub, is_admin)
        return create_error_response(405, "Method not allowed")

    try:
        if method == "POST":
            return _create_job(event, sub)
        if method == "GET" and job_id:
            return _get_job(job_id, sub, is_admin)
        if method == "GET":
            return _list_jobs(event, sub)
        return create_error_response(405, "Method not allowed")
    except Exception:
        logger.exception("Unhandled error in domain_gen handler")
        return create_error_response(500, "Internal server error")
