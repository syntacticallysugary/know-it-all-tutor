"""
Database connection management for Aurora DSQL.
Uses IAM token authentication — no stored credentials.
Each invocation gets a fresh connection with a short-lived token.
"""
import os
import boto3
import psycopg
from contextlib import contextmanager
from typing import Any

import logging

logger = logging.getLogger(__name__)

_dsql_endpoint: str | None = None


def _get_dsql_endpoint() -> str:
    """Return the DSQL cluster endpoint, reading from SSM on first call."""
    global _dsql_endpoint
    if _dsql_endpoint is None:
        env_val = os.environ.get("DSQL_ENDPOINT")
        if env_val:
            _dsql_endpoint = env_val
        else:
            ssm = boto3.client("ssm", region_name=os.environ.get("AWS_REGION", "us-east-1"))
            _dsql_endpoint = ssm.get_parameter(
                Name="/tutor-system/dev/dsql-endpoint"
            )["Parameter"]["Value"]
    return _dsql_endpoint


def _dsql_connection() -> psycopg.Connection:
    """Open a new DSQL connection authenticated via IAM token."""
    endpoint = _get_dsql_endpoint()
    region = os.environ.get("AWS_REGION", "us-east-1")

    client = boto3.client("dsql", region_name=region)
    token = client.generate_db_connect_admin_auth_token(
        hostname=endpoint,
        region=region,
        expires_in=900,
    )

    conn = psycopg.connect(
        host=endpoint,
        port=5432,
        dbname="postgres",
        user="admin",
        password=token,
        sslmode="require",
        connect_timeout=10,
        application_name="tutor-system-lambda",
    )
    conn.autocommit = True
    return conn


@contextmanager
def get_db_cursor():
    """Open a DSQL connection, yield a cursor, then close the connection."""
    conn = _dsql_connection()
    try:
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    finally:
        conn.close()


# Alias used by migration_runner
@contextmanager
def get_db_connection():
    """Yield a raw DSQL connection (autocommit=True)."""
    conn = _dsql_connection()
    try:
        yield conn
    finally:
        conn.close()


def execute_query(query: str, params: tuple = None) -> Any:
    """Execute a query and return all rows, or rowcount for non-SELECT."""
    with get_db_cursor() as cursor:
        cursor.execute(query, params)
        if cursor.description is not None:
            return cursor.fetchall()
        return cursor.rowcount


def execute_query_one(query: str, params: tuple = None) -> Any:
    """Execute a query and return one row, or rowcount for non-SELECT."""
    with get_db_cursor() as cursor:
        cursor.execute(query, params)
        if cursor.description is not None:
            return cursor.fetchone()
        return cursor.rowcount


def health_check() -> bool:
    """Verify DSQL connectivity."""
    try:
        result = execute_query_one("SELECT 1")
        return result is not None and result[0] == 1
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
