"""Domain generation polling worker.

Runs continuously on the LAN machine, claiming pending jobs from the
domain_gen_jobs table and running the two-prompt generation pipeline.

Usage:
  python -m pipeline.domain_gen.poll_worker
  python -m pipeline.domain_gen.poll_worker --interval 120
  python -m pipeline.domain_gen.poll_worker --url https://192.168.1.105/lite/v1 --model thinker1

Requires:
  DB_PROXY_FUNCTION_NAME env var (or --db-proxy-fn flag)
  AWS credentials with lambda:InvokeFunction on that function
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from pathlib import Path

import boto3

from .orchestrator import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_lambda_client: boto3.client = None


def _lambda_invoke(fn_name: str) -> boto3.client:
    """Return a cached boto3 Lambda client."""
    global _lambda_client
    if _lambda_client is None:
        _lambda_client = boto3.client("lambda")
    return _lambda_client


def _db(fn_name: str, query: str, params: list | None = None, return_dict: bool = True) -> list:
    """Execute a query via the DB proxy Lambda and return rows.

    Args:
        fn_name: DB proxy Lambda function name.
        query: SQL query string.
        params: Positional parameters.
        return_dict: Return rows as dicts (default True).

    Returns:
        List of result rows.

    Raises:
        RuntimeError: If the Lambda invocation fails or returns an error.
    """
    payload = {
        "operation": "execute_query",
        "query": query,
        "return_dict": return_dict,
    }
    if params:
        payload["params"] = params

    client = _lambda_invoke(fn_name)
    resp = client.invoke(
        FunctionName=fn_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    raw = resp["Payload"].read()
    envelope = json.loads(raw)

    if resp.get("FunctionError"):
        raise RuntimeError(f"DB proxy Lambda error: {envelope}")

    status = envelope.get("statusCode", 500)
    body = json.loads(envelope.get("body", "{}"))
    if status != 200:
        raise RuntimeError(f"DB query failed ({status}): {body.get('error', body)}")

    return body.get("result", [])


def _claim_job(fn_name: str) -> dict | None:
    """Atomically claim one pending job, returning its row or None.

    Uses a CTE to find and update in a single statement so concurrent
    workers don't double-claim (safe even if only one worker runs).

    Args:
        fn_name: DB proxy Lambda function name.

    Returns:
        Job row dict or None if no pending job exists.
    """
    rows = _db(
        fn_name,
        """
        UPDATE domain_gen_jobs
        SET status = 'running', updated_at = NOW()
        WHERE id = (
            SELECT id FROM domain_gen_jobs
            WHERE status = 'pending'
            ORDER BY created_at
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        )
        RETURNING id, topic, hints, total_terms
        """,
    )
    return rows[0] if rows else None


def _complete_job(fn_name: str, job_id: int, output_path: str) -> None:
    """Mark a job complete with its output path."""
    _db(
        fn_name,
        "UPDATE domain_gen_jobs SET status='complete', output_path=%s, updated_at=NOW() WHERE id=%s",
        params=[output_path, job_id],
    )


def _fail_job(fn_name: str, job_id: int, error: str) -> None:
    """Mark a job failed with an error message."""
    _db(
        fn_name,
        "UPDATE domain_gen_jobs SET status='failed', error_message=%s, updated_at=NOW() WHERE id=%s",
        params=[error[:2000], job_id],
    )


def _process_job(job: dict, base_url: str, model: str, fn_name: str) -> None:
    """Run the pipeline for one job and update the DB.

    Args:
        job: Row dict from domain_gen_jobs.
        base_url: LLM API base URL.
        model: Model identifier.
        fn_name: DB proxy Lambda function name.
    """
    job_id = job["id"]
    topic = job["topic"]
    hints = job.get("hints", "")
    total_terms = job.get("total_terms", 50)

    topic_slug = topic.lower().replace(" ", "_")
    output_path = f"data/{topic_slug}_upload.json"

    logger.info(f"Job {job_id}: starting '{topic}' ({total_terms} terms)")
    try:
        _, upload_json = run_pipeline(
            topic=topic,
            hints=hints,
            total_terms=total_terms,
            base_url=base_url,
            model=model,
        )
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(upload_json, indent=2))

        total = sum(len(d["terms"]) for d in upload_json["domains"])
        logger.info(f"Job {job_id}: complete — {total} terms written to {output_path}")
        _complete_job(fn_name, job_id, output_path)

    except Exception as exc:
        logger.error(f"Job {job_id}: failed — {exc}")
        _fail_job(fn_name, job_id, str(exc))


def main() -> None:
    """Polling worker entry point."""
    parser = argparse.ArgumentParser(
        description="Poll domain_gen_jobs and run the generation pipeline for each pending job.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Seconds between polls when no job is pending (default: 60)",
    )
    parser.add_argument(
        "--url",
        default="https://192.168.1.105/lite/v1",
        help="LLM API base URL",
    )
    parser.add_argument(
        "--model",
        default="thinker1",
        help="Model identifier",
    )
    parser.add_argument(
        "--db-proxy-fn",
        default=os.environ.get("DB_PROXY_FUNCTION_NAME", ""),
        help="DB proxy Lambda function name (default: DB_PROXY_FUNCTION_NAME env var)",
    )
    args = parser.parse_args()

    if not args.db_proxy_fn:
        raise SystemExit("DB_PROXY_FUNCTION_NAME env var or --db-proxy-fn flag required")

    logger.info(f"Polling every {args.interval}s — model: {args.model} @ {args.url}")

    while True:
        try:
            job = _claim_job(args.db_proxy_fn)
            if job:
                _process_job(job, args.url, args.model, args.db_proxy_fn)
            else:
                logger.debug("No pending jobs — sleeping")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Shutting down.")
            break
        except Exception as exc:
            logger.error(f"Poll loop error: {exc}")
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
