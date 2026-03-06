"""
Client for invoking the Database Proxy Lambda (Lambda B)
Used by Lambda A to execute database operations
"""
import json
import boto3
import os
from typing import Any, List, Dict, Optional, Tuple

# Initialize Lambda client
lambda_client = boto3.client('lambda')


class DBProxyClient:
    """Client for invoking database proxy Lambda"""
    
    def __init__(self, function_name: str = None):
        """
        Initialize DB Proxy Client
        
        Args:
            function_name: Name of the DB proxy Lambda function
                          Defaults to DB_PROXY_FUNCTION_NAME env var
        """
        self.function_name = function_name or os.environ.get('DB_PROXY_FUNCTION_NAME')

        if not self.function_name and os.environ.get('LOCAL_DEV') != 'true':
            raise ValueError("DB_PROXY_FUNCTION_NAME environment variable not set")
    
    def _invoke_local(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute database operation directly for LOCAL_DEV mode (no Lambda hop)."""
        from database import get_db_connection

        operation = payload.get('operation')
        query = payload.get('query', '')
        params = payload.get('params')
        return_dict = payload.get('return_dict', False)

        with get_db_connection() as conn:
            cursor = conn.cursor()

            if operation == 'health_check':
                cursor.execute("SELECT 1")
                return {'healthy': True}

            elif operation == 'execute_query':
                cursor.execute(query, params or [])
                if cursor.description is not None:
                    if return_dict:
                        columns = [col.name for col in cursor.description]
                        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    else:
                        rows = cursor.fetchall()
                    return {'result': rows}
                return {'result': []}

            elif operation == 'execute_query_one':
                cursor.execute(query, params or [])
                row = cursor.fetchone()
                if row is not None and return_dict:
                    columns = [col.name for col in cursor.description]
                    row = dict(zip(columns, row))
                return {'result': row}

            elif operation == 'execute_many':
                cursor.executemany(query, payload.get('params_list', []))
                return {'row_count': cursor.rowcount}

            else:
                raise Exception(f"Unknown operation: {operation}")

    def _invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke the DB proxy Lambda

        Args:
            payload: Event payload for the Lambda

        Returns:
            Response from the Lambda
        """
        if os.environ.get('LOCAL_DEV') == 'true':
            return self._invoke_local(payload)

        response = lambda_client.invoke(
            FunctionName=self.function_name,
            InvocationType='RequestResponse',  # Synchronous
            Payload=json.dumps(payload)
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        # Check for Lambda errors
        if response.get('FunctionError'):
            raise Exception(f"Lambda invocation error: {response_payload}")
        
        # Parse body
        status_code = response_payload.get('statusCode', 500)
        body = json.loads(response_payload.get('body', '{}'))
        
        if status_code != 200:
            raise Exception(f"Database operation failed: {body.get('error', 'Unknown error')}")
        
        return body
    
    def health_check(self) -> bool:
        """
        Check database health
        
        Returns:
            True if database is healthy
        """
        try:
            result = self._invoke({'operation': 'health_check'})
            return result.get('healthy', False)
        except Exception:
            return False
    
    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        return_dict: bool = False
    ) -> List[Any]:
        """
        Execute a query and return all rows
        
        Args:
            query: SQL query
            params: Query parameters (tuple)
            return_dict: Return rows as dicts instead of tuples
            
        Returns:
            List of rows
        """
        payload = {
            'operation': 'execute_query',
            'query': query,
            'return_dict': return_dict
        }
        
        if params:
            payload['params'] = list(params)
        
        result = self._invoke(payload)
        return result.get('result', [])
    
    def execute_query_one(
        self,
        query: str,
        params: Optional[Tuple] = None,
        return_dict: bool = False
    ) -> Optional[Any]:
        """
        Execute a query and return single row
        
        Args:
            query: SQL query
            params: Query parameters (tuple)
            return_dict: Return row as dict instead of tuple
            
        Returns:
            Single row or None
        """
        payload = {
            'operation': 'execute_query_one',
            'query': query,
            'return_dict': return_dict
        }
        
        if params:
            payload['params'] = list(params)
        
        result = self._invoke(payload)
        return result.get('result')
    
    def execute_many(
        self,
        query: str,
        params_list: List[Tuple]
    ) -> int:
        """
        Execute a query multiple times (batch operation)
        
        Args:
            query: SQL query
            params_list: List of parameter tuples
            
        Returns:
            Number of rows affected
        """
        payload = {
            'operation': 'execute_many',
            'query': query,
            'params_list': [list(p) for p in params_list]
        }
        
        result = self._invoke(payload)
        return result.get('row_count', 0)
    
    # Quiz-specific operations
    
    def create_quiz_session(self, session_data: Dict[str, Any]) -> str:
        """
        Create a new quiz session record.
        
        Args:
            session_data: Dictionary with user_id, domain_id, total_terms
            
        Returns:
            Session ID (UUID string)
        """
        query = """
            INSERT INTO quiz_sessions (user_id, domain_id, status, current_term_index, total_terms)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            session_data['user_id'],
            session_data['domain_id'],
            session_data.get('status', 'active'),
            session_data.get('current_term_index', 0),
            session_data['total_terms']
        )
        
        result = self.execute_query_one(query, params, return_dict=True)
        return str(result['id'])
    
    def get_quiz_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve quiz session details.
        
        Args:
            session_id: UUID of the quiz session
            
        Returns:
            Session dictionary or None if not found
        """
        query = """
            SELECT id, user_id, domain_id, status, current_term_index, total_terms,
                   started_at, paused_at, completed_at, updated_at
            FROM quiz_sessions
            WHERE id = %s
        """
        return self.execute_query_one(query, (session_id,), return_dict=True)
    
    def update_quiz_session(self, session_id: str, updates: Dict[str, Any]) -> None:
        """
        Update quiz session state.
        
        Args:
            session_id: UUID of the quiz session
            updates: Dictionary of fields to update (status, current_term_index, etc.)
        """
        # Build dynamic UPDATE query based on provided fields
        allowed_fields = ['status', 'current_term_index', 'paused_at', 'completed_at']
        set_clauses = []
        params = []
        
        for field in allowed_fields:
            if field in updates:
                set_clauses.append(f"{field} = %s")
                params.append(updates[field])
        
        if not set_clauses:
            return  # Nothing to update
        
        # Always update updated_at
        set_clauses.append("updated_at = NOW()")
        
        # Add session_id to params for WHERE clause
        params.append(session_id)
        
        query = f"""
            UPDATE quiz_sessions
            SET {', '.join(set_clauses)}
            WHERE id = %s
        """
        
        self.execute_query(query, tuple(params))
    
    def delete_quiz_session(self, session_id: str) -> None:
        """
        Delete a quiz session.
        
        Args:
            session_id: UUID of the quiz session
        """
        query = "DELETE FROM quiz_sessions WHERE id = %s"
        self.execute_query(query, (session_id,))
    
    def get_domain_terms(self, domain_id: str) -> List[Dict[str, Any]]:
        """
        Fetch all terms for a domain.
        
        Args:
            domain_id: UUID of the domain
            
        Returns:
            List of term dictionaries with id, term, and definition
        """
        query = """
            SELECT id, data->>'term' as term, data->>'definition' as definition
            FROM tree_nodes
            WHERE parent_id = %s AND node_type = 'term'
            ORDER BY created_at
        """
        return self.execute_query(query, (domain_id,), return_dict=True)
    
    def record_progress(self, progress_data: Dict[str, Any]) -> str:
        """
        Record a student's answer attempt.
        
        Args:
            progress_data: Dictionary with user_id, term_id, session_id, student_answer,
                          correct_answer, is_correct, similarity_score, attempt_number
            
        Returns:
            Progress record ID (UUID string)
        """
        query = """
            INSERT INTO progress_records 
            (user_id, term_id, session_id, student_answer, correct_answer, 
             is_correct, similarity_score, attempt_number, feedback)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            progress_data['user_id'],
            progress_data['term_id'],
            progress_data.get('session_id'),
            progress_data['student_answer'],
            progress_data['correct_answer'],
            progress_data['is_correct'],
            progress_data.get('similarity_score'),
            progress_data.get('attempt_number', 1),
            progress_data.get('feedback')
        )
        
        result = self.execute_query_one(query, params, return_dict=True)
        return str(result['id'])
    
    def get_user_progress(self, user_id: str, domain_id: str) -> List[Dict[str, Any]]:
        """
        Get progress records for a user in a domain.
        
        Args:
            user_id: UUID of the user
            domain_id: UUID of the domain
            
        Returns:
            List of progress record dictionaries
        """
        query = """
            SELECT pr.id, pr.user_id, pr.term_id, pr.session_id,
                   pr.student_answer, pr.correct_answer, pr.is_correct,
                   pr.similarity_score, pr.attempt_number, pr.feedback, pr.created_at,
                   tn.data->>'term' as term
            FROM progress_records pr
            JOIN tree_nodes tn ON pr.term_id = tn.id
            WHERE pr.user_id = %s AND tn.parent_id = %s
            ORDER BY pr.created_at DESC
        """
        return self.execute_query(query, (user_id, domain_id), return_dict=True)


# Global instance for easy import
db_proxy = None


def get_db_proxy() -> DBProxyClient:
    """Get or create global DB proxy client instance"""
    global db_proxy
    if db_proxy is None:
        db_proxy = DBProxyClient()
    return db_proxy
