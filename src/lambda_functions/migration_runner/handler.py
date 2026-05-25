"""
Database Migration Runner Lambda
Automatically applies pending migrations during deployment
# v3 - includes progress_records fix - force CDK asset update
"""
import json
import os
import re
import hashlib
import time
from typing import List, Dict, Tuple
import sys

# Add shared layer to path
sys.path.insert(0, '/opt/python')
from database import execute_query, execute_query_one, get_db_connection

def get_migration_files() -> List[Tuple[str, str, str]]:
    """
    Get all migration files embedded in the Lambda
    Returns: List of (version, name, sql_content)
    """
    migrations = []
    
    # Migrations are embedded as environment variables or in /opt/migrations
    migrations_dir = os.environ.get('MIGRATIONS_DIR', '/opt/migrations')
    
    if os.path.exists(migrations_dir):
        for filename in sorted(os.listdir(migrations_dir)):
            if filename.endswith('.sql'):
                version = filename.split('_')[0]
                name = filename[:-4]  # Remove .sql
                
                with open(os.path.join(migrations_dir, filename), 'r') as f:
                    sql_content = f.read()
                
                migrations.append((version, name, sql_content))
    
    return migrations

def calculate_checksum(content: str) -> str:
    """Calculate SHA256 checksum of migration content"""
    return hashlib.sha256(content.encode()).hexdigest()

def get_applied_migrations() -> set:
    """Get set of already applied migration versions"""
    try:
        # First check if migrations table exists
        check_table = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'schema_migrations'
            );
        """
        result = execute_query_one(check_table)
        
        if not result or not result[0]:
            # Table doesn't exist yet, no migrations applied
            return set()
        
        # Get applied migrations
        query = "SELECT version FROM schema_migrations WHERE success = true ORDER BY version;"
        results = execute_query(query)
        return {row[0] for row in results}
    except Exception as e:
        print(f"Error checking applied migrations: {e}")
        return set()

def apply_migration(version: str, name: str, sql_content: str) -> Dict:
    """Apply a single migration and record it."""
    start_time = time.time()
    checksum = calculate_checksum(sql_content)

    try:
        print(f"Applying migration {version}: {name}")

        # DSQL requires one DDL statement per transaction.
        # Strip single-line comments first so semicolons inside comments
        # don't produce spurious split fragments, then execute each statement.
        stripped = re.sub(r'--[^\n]*', '', sql_content)
        for stmt in stripped.split(';'):
            stmt = stmt.strip()
            if stmt:
                execute_query(stmt)

        execution_time = int((time.time() - start_time) * 1000)

        execute_query(
            "INSERT INTO schema_migrations (version, name, checksum, execution_time_ms, success)"
            " VALUES (%s, %s, %s, %s, true)"
            " ON CONFLICT (version) DO UPDATE SET success = true,"
            " execution_time_ms = EXCLUDED.execution_time_ms,"
            " checksum = EXCLUDED.checksum",
            (version, name, checksum, execution_time),
        )

        print(f"✓ Migration {version} applied in {execution_time}ms")
        return {'version': version, 'name': name, 'success': True, 'execution_time_ms': execution_time}

    except Exception as e:
        execution_time = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        print(f"✗ Migration {version} failed: {error_msg}")

        try:
            execute_query(
                "INSERT INTO schema_migrations (version, name, checksum, execution_time_ms, success)"
                " VALUES (%s, %s, %s, %s, false)",
                (version, name, checksum, execution_time),
            )
        except Exception:
            pass

        return {'version': version, 'name': name, 'success': False, 'error': error_msg, 'execution_time_ms': execution_time}

def lambda_handler(event, context):
    """
    Run pending database migrations
    
    Event format:
    {
        "action": "migrate" | "status",
        "dry_run": false  # Optional: just check what would run
    }
    """
    try:
        action = event.get('action', 'migrate')
        dry_run = event.get('dry_run', False)
        
        print(f"Migration runner started (action={action}, dry_run={dry_run})")
        
        # Get all migration files
        all_migrations = get_migration_files()
        print(f"Found {len(all_migrations)} migration files")
        
        # Get already applied migrations
        applied = get_applied_migrations()
        print(f"Already applied: {len(applied)} migrations")
        
        # Find pending migrations
        pending = [(v, n, s) for v, n, s in all_migrations if v not in applied]
        print(f"Pending migrations: {len(pending)}")
        
        if action == 'status':
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'total_migrations': len(all_migrations),
                    'applied_count': len(applied),
                    'pending_count': len(pending),
                    'pending_migrations': [{'version': v, 'name': n} for v, n, _ in pending]
                })
            }
        
        if not pending:
            print("No pending migrations")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No pending migrations',
                    'applied_count': 0
                })
            }
        
        if dry_run:
            print("Dry run - would apply:")
            for version, name, _ in pending:
                print(f"  - {version}: {name}")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Dry run completed',
                    'would_apply': [{'version': v, 'name': n} for v, n, _ in pending]
                })
            }
        
        # Apply pending migrations
        results = []
        for version, name, sql_content in pending:
            result = apply_migration(version, name, sql_content)
            results.append(result)
            
            # Stop on first failure
            if not result['success']:
                print(f"Migration failed, stopping at {version}")
                break
        
        success_count = sum(1 for r in results if r['success'])
        failed_count = len(results) - success_count
        
        all_successful = failed_count == 0
        
        response = {
            'statusCode': 200 if all_successful else 500,
            'body': json.dumps({
                'message': f'Applied {success_count} migrations' + (f', {failed_count} failed' if failed_count else ''),
                'migrations': results,
                'success': all_successful
            })
        }
        
        print(f"Migration run completed: {success_count} successful, {failed_count} failed")
        
        return response
        
    except Exception as e:
        print(f"Migration runner error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Migration runner failed'
            })
        }
