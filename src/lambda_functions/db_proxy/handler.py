"""
Database Proxy Lambda (Lambda B)
Handles all database operations, invoked by other Lambdas via lambda.invoke()
"""
import json
import sys
import os
import time
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

# Add shared modules to path
sys.path.append('/opt/python')

from database import get_db_cursor, execute_query, execute_query_one, health_check
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_MAX_OCC_RETRIES = 3


def _is_occ_conflict(exc: Exception) -> bool:
    """Return True if the exception is a DSQL optimistic concurrency conflict."""
    pgcode = getattr(exc, "pgcode", None) or getattr(getattr(exc, "diag", None), "sqlstate", None)
    if pgcode == "40001":
        return True
    return "change conflicts with another transaction" in str(exc).lower()


def _with_retry(fn):
    """Call fn(), retrying on DSQL OCC conflicts with exponential backoff."""
    for attempt in range(_MAX_OCC_RETRIES):
        try:
            return fn()
        except Exception as exc:
            if _is_occ_conflict(exc) and attempt < _MAX_OCC_RETRIES - 1:
                time.sleep(0.1 * (2 ** attempt))
                continue
            raise


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def lambda_handler(event, context):
    """
    Handle database operations from other Lambdas.

    Event format:
    {
        "operation": "execute_query" | "execute_query_one" | "health_check" | "execute_many",
        "query": "SELECT * FROM users WHERE email = %s",
        "params": ["user@example.com"],
        "return_dict": true
    }
    """
    try:
        return _with_retry(lambda: _dispatch(event))
    except Exception as e:
        logger.error(f"Database proxy error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Database operation failed',
                'message': str(e)
            }, default=json_serial)
        }


def _dispatch(event):
    """Dispatch a database operation from the event payload."""
    operation = event.get('operation')

    if not operation:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing operation parameter'})
        }

    if operation == 'health_check':
        is_healthy = health_check()
        return {
            'statusCode': 200 if is_healthy else 500,
            'body': json.dumps({
                'healthy': is_healthy,
                'message': 'Database connection OK' if is_healthy else 'Database connection failed'
            })
        }

    elif operation == 'execute_query':
        query = event.get('query')
        params = event.get('params')
        return_dict = event.get('return_dict', False)

        if not query:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing query parameter'})
            }

        result = execute_query(query, tuple(params) if params else None)

        if isinstance(result, int):
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'result': [],
                    'row_count': result
                }, default=json_serial)
            }

        if return_dict and result:
            with get_db_cursor() as cursor:
                cursor.execute(query, tuple(params) if params else None)
                columns = [desc[0] for desc in cursor.description]
                result = [dict(zip(columns, row)) for row in result]

        return {
            'statusCode': 200,
            'body': json.dumps({
                'result': result if isinstance(result, list) else None,
                'row_count': len(result) if isinstance(result, list) else result
            }, default=json_serial)
        }

    elif operation == 'execute_query_one':
        query = event.get('query')
        params = event.get('params')
        return_dict = event.get('return_dict', False)

        if not query:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing query parameter'})
            }

        result = execute_query_one(query, tuple(params) if params else None)

        if return_dict and result:
            with get_db_cursor() as cursor:
                cursor.execute(query, tuple(params) if params else None)
                columns = [desc[0] for desc in cursor.description]
                result = dict(zip(columns, result))

        return {
            'statusCode': 200,
            'body': json.dumps({'result': result}, default=json_serial)
        }

    elif operation == 'execute_many':
        query = event.get('query')
        params_list = event.get('params_list')

        if not query or not params_list:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing query or params_list parameter'})
            }

        with get_db_cursor() as cursor:
            cursor.executemany(query, params_list)
            row_count = cursor.rowcount

        return {
            'statusCode': 200,
            'body': json.dumps({
                'row_count': row_count,
                'message': f'Executed {row_count} operations'
            }, default=json_serial)
        }

    else:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Unknown operation: {operation}'})
        }
