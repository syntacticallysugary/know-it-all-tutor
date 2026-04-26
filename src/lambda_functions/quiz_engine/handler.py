"""
Quiz Engine Lambda Function Handler
Handles quiz session management and question presentation
"""
import json
import os
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add /opt/python to path for Lambda layer modules
import sys
sys.path.append('/opt/python')

import boto3
from response_utils import create_response, handle_error
from auth_utils import extract_user_from_cognito_event
from db_proxy_client import DBProxyClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize DB Proxy client
db_proxy = DBProxyClient(os.environ.get('DB_PROXY_FUNCTION_NAME'))

# Initialize Lambda client for Answer Evaluator invocation
lambda_client = boto3.client('lambda')
ANSWER_EVALUATOR_FUNCTION_NAME = os.environ.get('ANSWER_EVALUATOR_FUNCTION_NAME')

PASS_THRESHOLD = 0.50


def invoke_answer_evaluator(student_answer: str, correct_answer: str, threshold: float = PASS_THRESHOLD) -> Dict:
    """Invoke Answer Evaluator Lambda"""
    payload = {
        'answer': student_answer,
        'correct_answer': correct_answer
    }
    
    response = lambda_client.invoke(
        FunctionName=ANSWER_EVALUATOR_FUNCTION_NAME,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    if result.get('statusCode') != 200:
        raise Exception(f"Answer Evaluator error: {result.get('body')}")

    body = result['body']
    return json.loads(body) if isinstance(body, str) else body


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for quiz engine operations
    """
    try:
        http_method = event.get('httpMethod')
        path = event.get('path', '')
        
        # Verify authentication using Cognito authorizer context
        auth_result = extract_user_from_cognito_event(event)
        if not auth_result['valid']:
            return create_response(401, {'error': 'Unauthorized'})
        
        # Get database user ID from cognito_sub
        cognito_sub = auth_result['user_id']  # This is actually the Cognito sub
        user_query = "SELECT id FROM users WHERE cognito_sub = %s"
        user_result = db_proxy.execute_query_one(user_query, (cognito_sub,), return_dict=True)
        
        if not user_result:
            return create_response(404, {'error': 'User not found in database'})
        
        user_id = user_result['id']  # This is the database user ID
        
        if http_method == 'POST':
            if '/quiz/start' in path:
                return handle_start_quiz(event, user_id)
            elif '/quiz/answer' in path:
                return handle_submit_answer(event, user_id)
            elif '/quiz/pause' in path:
                return handle_pause_quiz(event, user_id)
            elif '/quiz/resume' in path:
                return handle_resume_quiz(event, user_id)
            elif '/quiz/restart' in path:
                return handle_restart_quiz(event, user_id)
        elif http_method == 'GET':
            if '/quiz/question' in path:
                return handle_get_next_question(event, user_id)
            elif '/quiz/complete' in path:
                return handle_complete_quiz(event, user_id)
            elif '/quiz/session/' in path:
                return handle_get_session(event, user_id)
        elif http_method == 'DELETE':
            if '/quiz/session/' in path:
                return handle_delete_session(event, user_id)
        
        return create_response(404, {'error': 'Endpoint not found'})
        
    except Exception as e:
        return handle_error(e)


def handle_start_quiz(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle quiz session creation"""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        domain_id = body.get('domain_id')
        quiz_mode = body.get('quiz_mode', 'forward')

        if not domain_id:
            return create_response(400, {'error': 'domain_id is required'})

        if quiz_mode not in ('forward', 'reverse'):
            return create_response(400, {'error': "quiz_mode must be 'forward' or 'reverse'"})
        
        # Validate domain exists and belongs to user or is public
        domain_query = """
            SELECT id, data->>'name' as name, user_id, is_public
            FROM tree_nodes 
            WHERE id = %s AND node_type = 'domain'
        """
        domain_result = db_proxy.execute_query_one(domain_query, (domain_id,), return_dict=True)
        
        if not domain_result:
            return create_response(404, {'error': 'Domain not found'})
        
        domain_user_id = domain_result['user_id']
        is_public = domain_result.get('is_public', False)
        
        # Check if user has access to this domain (owner or public domain)
        if domain_user_id != user_id and not is_public:
            return create_response(403, {'error': 'Access denied to this domain'})
        
        # Get all terms in the domain
        terms_query = """
            SELECT id, data->>'term' as term, data->>'definition' as definition
            FROM tree_nodes 
            WHERE parent_id = %s AND node_type = 'term'
            ORDER BY created_at
        """
        terms_result = db_proxy.execute_query(terms_query, (domain_id,), return_dict=True)
        
        if not terms_result:
            return create_response(400, {'error': 'Domain has no terms to quiz on'})
        
        # Check for existing active session matching this mode
        existing_session_query = """
            SELECT id, current_term_index, total_questions, session_data
            FROM quiz_sessions
            WHERE user_id = %s AND domain_id = %s AND status = 'active'
            AND COALESCE(session_data->>'quiz_mode', 'forward') = %s
        """
        existing_session = db_proxy.execute_query_one(existing_session_query, (user_id, domain_id, quiz_mode), return_dict=True)

        if existing_session:
            # Return existing session
            session_id = existing_session['id']
            current_index = existing_session['current_term_index']
            total_questions = existing_session['total_questions']
            session_data = existing_session['session_data'] or {}

            # Get current question
            if current_index < len(terms_result):
                current_term = terms_result[current_index]
                current_question = build_question(current_term['id'], current_term, current_index + 1, total_questions, quiz_mode)
            else:
                current_question = None

            return create_response(200, {
                'session_id': str(session_id),
                'status': 'resumed',
                'domain_name': domain_result['name'],
                'quiz_mode': quiz_mode,
                'current_question': current_question,
                'progress': {
                    'current_index': current_index,
                    'total_questions': total_questions,
                    'completed': current_index >= total_questions
                }
            })
        
        # Create new quiz session
        session_id = str(uuid.uuid4())
        total_questions = len(terms_result)
        
        # Prepare session data with term order and quiz mode
        session_data = {
            'term_order': [str(term['id']) for term in terms_result],
            'domain_name': domain_result['name'],
            'quiz_mode': quiz_mode
        }

        # Insert new session
        insert_session_query = """
            INSERT INTO quiz_sessions (id, user_id, domain_id, status, current_term_index, total_questions, session_data)
            VALUES (%s, %s, %s, 'active', 0, %s, %s)
        """
        db_proxy.execute_query(insert_session_query, (
            session_id, user_id, domain_id, total_questions, json.dumps(session_data)
        ))

        # Get first question
        first_term = terms_result[0]
        current_question = build_question(first_term['id'], first_term, 1, total_questions, quiz_mode)

        return create_response(200, {
            'session_id': session_id,
            'status': 'started',
            'domain_name': domain_result['name'],
            'quiz_mode': quiz_mode,
            'current_question': current_question,
            'progress': {
                'current_index': 0,
                'total_questions': total_questions,
                'completed': False
            }
        })
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        logger.error(f"Error starting quiz: {str(e)}")
        return handle_error(e)


def handle_submit_answer(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle answer submission and evaluation"""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        session_id = body.get('session_id')
        student_answer = body.get('answer', '').strip()
        
        if not session_id:
            return create_response(400, {'error': 'session_id is required'})
        
        if not student_answer:
            return create_response(400, {'error': 'answer is required'})
        
        # Verify session exists and belongs to user
        session_query = """
            SELECT qs.id, qs.status, qs.current_term_index, qs.total_questions, 
                   qs.session_data, qs.correct_answers, tn.data->>'name' as domain_name
            FROM quiz_sessions qs
            JOIN tree_nodes tn ON qs.domain_id = tn.id
            WHERE qs.id = %s AND qs.user_id = %s
        """
        session_result = db_proxy.execute_query_one(session_query, (session_id, user_id), return_dict=True)
        
        if not session_result:
            return create_response(404, {'error': 'Quiz session not found'})
        
        current_status = session_result['status']
        current_index = session_result['current_term_index']
        total_questions = session_result['total_questions']
        session_data = session_result['session_data'] or {}
        correct_answers = session_result['correct_answers']
        domain_name = session_result['domain_name']
        
        if current_status != 'active':
            return create_response(400, {'error': f'Cannot submit answer for quiz in {current_status} state'})
        
        # Check if quiz is already completed
        if current_index >= total_questions:
            return create_response(400, {'error': 'Quiz is already completed'})
        
        # Get current term details
        term_order = session_data.get('term_order', [])
        if current_index >= len(term_order):
            return create_response(400, {'error': 'No current question available'})
        
        term_id = term_order[current_index]
        
        # Get term details for evaluation
        term_query = """
            SELECT data->>'term' as term, data->>'definition' as definition
            FROM tree_nodes 
            WHERE id = %s
        """
        term_result = db_proxy.execute_query_one(term_query, (term_id,), return_dict=True)
        
        if not term_result:
            return create_response(404, {'error': 'Current question not found'})
        
        quiz_mode = session_data.get('quiz_mode', 'forward')
        term_text = term_result['term']
        definition_text = term_result['definition']

        if quiz_mode == 'reverse':
            # Reverse mode: student must supply the exact term (case-insensitive)
            correct_answer = term_text
            is_correct = student_answer.strip().lower() == correct_answer.strip().lower()
            similarity_score = 1.0 if is_correct else 0.0
            feedback = "Correct!" if is_correct else f"Incorrect. The correct answer is: {correct_answer}"
        else:
            # Forward mode: semantic evaluation of the student's definition
            correct_answer = definition_text
            evaluator_feedback = None
            if ANSWER_EVALUATOR_FUNCTION_NAME:
                try:
                    evaluator_feedback = invoke_answer_evaluator(student_answer, correct_answer)
                except Exception as eval_err:
                    logger.warning("Answer evaluator failed, falling back to Jaccard: %s", eval_err)

            if evaluator_feedback:
                similarity_score = float(evaluator_feedback.get('similarity', 0.0))
                feedback = evaluator_feedback.get('feedback', '')
            else:
                similarity_score = calculate_simple_similarity(student_answer.lower(), correct_answer.lower())
                feedback = ''

            is_correct = similarity_score >= PASS_THRESHOLD

            if not feedback:
                if is_correct:
                    feedback = "Correct! Well done."
                else:
                    feedback = f"Incorrect. The correct answer is: {correct_answer}"
        
        # Record the progress
        progress_query = """
            INSERT INTO progress_records (user_id, term_id, session_id, student_answer, correct_answer, 
                                        is_correct, similarity_score, feedback)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        db_proxy.execute_query(progress_query, (
            user_id, term_id, session_id, student_answer, correct_answer,
            is_correct, similarity_score, feedback
        ))
        
        # Update session progress
        new_correct_answers = correct_answers + (1 if is_correct else 0)
        new_index = current_index + 1
        
        # Check if quiz is completed
        quiz_completed = new_index >= total_questions
        
        if quiz_completed:
            # Mark session as completed
            update_session_query = """
                UPDATE quiz_sessions 
                SET current_term_index = %s, correct_answers = %s, status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            db_proxy.execute_query(update_session_query, (new_index, new_correct_answers, session_id))
        else:
            # Update session progress
            update_session_query = """
                UPDATE quiz_sessions 
                SET current_term_index = %s, correct_answers = %s
                WHERE id = %s
            """
            db_proxy.execute_query(update_session_query, (new_index, new_correct_answers, session_id))
        
        # Prepare next question if not completed
        next_question = None
        if not quiz_completed and new_index < len(term_order):
            next_term_id = term_order[new_index]
            next_term_query = """
                SELECT data->>'term' as term, data->>'definition' as definition
                FROM tree_nodes
                WHERE id = %s
            """
            next_term_result = db_proxy.execute_query_one(next_term_query, (next_term_id,), return_dict=True)

            if next_term_result:
                next_question = build_question(next_term_id, next_term_result, new_index + 1, total_questions, quiz_mode)
        
        return create_response(200, {
            'session_id': session_id,
            'evaluation': {
                'is_correct': is_correct,
                'similarity_score': round(similarity_score, 2),
                'feedback': feedback,
                'correct_answer': correct_answer
            },
            'progress': {
                'current_index': new_index,
                'total_questions': total_questions,
                'correct_answers': new_correct_answers,
                'completed': quiz_completed
            },
            'next_question': next_question,
            'quiz_completed': quiz_completed
        })
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        logger.error(f"Error submitting answer: {str(e)}")
        return handle_error(e)


def handle_restart_quiz(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle quiz restart functionality"""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        domain_id = body.get('domain_id')
        quiz_mode = body.get('quiz_mode', 'forward')

        if not domain_id:
            return create_response(400, {'error': 'domain_id is required'})

        # Validate domain exists and user has access
        domain_query = """
            SELECT id, data->>'name' as name, user_id, is_public
            FROM tree_nodes
            WHERE id = %s AND node_type = 'domain'
        """
        domain_result = db_proxy.execute_query_one(domain_query, (domain_id,), return_dict=True)

        if not domain_result:
            return create_response(404, {'error': 'Domain not found'})

        domain_user_id = domain_result['user_id']
        is_public = domain_result.get('is_public', False)

        # Check if user has access to this domain (owner or public)
        if domain_user_id != user_id and not is_public:
            return create_response(403, {'error': 'Access denied to this domain'})

        # Abandon active/paused sessions for the same mode only
        abandon_query = """
            UPDATE quiz_sessions
            SET status = 'abandoned'
            WHERE user_id = %s AND domain_id = %s AND status IN ('active', 'paused')
            AND COALESCE(session_data->>'quiz_mode', 'forward') = %s
        """
        db_proxy.execute_query(abandon_query, (user_id, domain_id, quiz_mode))
        
        # Start a new quiz session (reuse the start quiz logic)
        return handle_start_quiz(event, user_id)
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        logger.error(f"Error restarting quiz: {str(e)}")
        return handle_error(e)


def calculate_simple_similarity(answer1: str, answer2: str) -> float:
    """
    Simple similarity calculation based on word overlap
    This is a placeholder for the full semantic similarity evaluation
    """
    words1 = set(answer1.split())
    words2 = set(answer2.split())

    if not words1 and not words2:
        return 1.0

    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union) if union else 0.0


def build_question(term_id: str, term_data: dict, question_number: int, total_questions: int, quiz_mode: str) -> dict:
    q = {
        'term_id': str(term_id),
        'question_number': question_number,
        'total_questions': total_questions
    }
    if quiz_mode == 'reverse':
        q['definition'] = term_data.get('definition', '')
    else:
        q['term'] = term_data.get('term', '')
    return q


def handle_get_next_question(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle getting next question in quiz"""
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        session_id = query_params.get('session_id')
        
        if not session_id:
            return create_response(400, {'error': 'session_id is required'})
        
        # Verify session exists and belongs to user
        session_query = """
            SELECT qs.id, qs.status, qs.current_term_index, qs.total_questions, 
                   qs.session_data, tn.data->>'name' as domain_name
            FROM quiz_sessions qs
            JOIN tree_nodes tn ON qs.domain_id = tn.id
            WHERE qs.id = %s AND qs.user_id = %s
        """
        session_result = db_proxy.execute_query_one(session_query, (session_id, user_id), return_dict=True)
        
        if not session_result:
            return create_response(404, {'error': 'Quiz session not found'})
        
        current_status = session_result['status']
        current_index = session_result['current_term_index']
        total_questions = session_result['total_questions']
        session_data = session_result['session_data'] or {}
        domain_name = session_result['domain_name']
        
        if current_status != 'active':
            return create_response(400, {'error': f'Cannot get question for quiz in {current_status} state'})
        
        # Check if quiz is completed
        if current_index >= total_questions:
            return create_response(200, {
                'session_id': session_id,
                'completed': True,
                'message': 'Quiz completed'
            })
        
        quiz_mode = session_data.get('quiz_mode', 'forward')

        # Get current question
        term_order = session_data.get('term_order', [])
        if current_index < len(term_order):
            term_id = term_order[current_index]

            term_query = """
                SELECT data->>'term' as term, data->>'definition' as definition
                FROM tree_nodes
                WHERE id = %s
            """
            term_result = db_proxy.execute_query_one(term_query, (term_id,), return_dict=True)

            if term_result:
                current_question = build_question(term_id, term_result, current_index + 1, total_questions, quiz_mode)
            else:
                return create_response(404, {'error': 'Question not found'})
        else:
            return create_response(404, {'error': 'Question not found'})

        return create_response(200, {
            'session_id': session_id,
            'domain_name': domain_name,
            'quiz_mode': quiz_mode,
            'current_question': current_question,
            'progress': {
                'current_index': current_index,
                'total_questions': total_questions,
                'completed': False
            }
        })

    except Exception as e:
        logger.error(f"Error getting next question: {str(e)}")
        return handle_error(e)


def handle_pause_quiz(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle pausing quiz session"""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        session_id = body.get('session_id')
        
        if not session_id:
            return create_response(400, {'error': 'session_id is required'})
        
        # Verify session exists and belongs to user
        session_query = """
            SELECT id, status, current_term_index, total_questions
            FROM quiz_sessions 
            WHERE id = %s AND user_id = %s
        """
        session_result = db_proxy.execute_query_one(session_query, (session_id, user_id), return_dict=True)
        
        if not session_result:
            return create_response(404, {'error': 'Quiz session not found'})
        
        current_status = session_result['status']
        
        if current_status != 'active':
            return create_response(400, {'error': f'Cannot pause quiz in {current_status} state'})
        
        # Update session to paused
        update_query = """
            UPDATE quiz_sessions 
            SET status = 'paused', paused_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        db_proxy.execute_query(update_query, (session_id,))
        
        return create_response(200, {
            'session_id': session_id,
            'status': 'paused',
            'message': 'Quiz paused successfully'
        })
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        logger.error(f"Error pausing quiz: {str(e)}")
        return handle_error(e)


def handle_resume_quiz(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle resuming quiz session"""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        session_id = body.get('session_id')
        
        if not session_id:
            return create_response(400, {'error': 'session_id is required'})
        
        # Verify session exists and belongs to user
        session_query = """
            SELECT qs.id, qs.status, qs.current_term_index, qs.total_questions, 
                   qs.session_data, tn.data->>'name' as domain_name
            FROM quiz_sessions qs
            JOIN tree_nodes tn ON qs.domain_id = tn.id
            WHERE qs.id = %s AND qs.user_id = %s
        """
        session_result = db_proxy.execute_query_one(session_query, (session_id, user_id), return_dict=True)
        
        if not session_result:
            return create_response(404, {'error': 'Quiz session not found'})
        
        current_status = session_result['status']
        current_index = session_result['current_term_index']
        total_questions = session_result['total_questions']
        session_data = session_result['session_data'] or {}
        domain_name = session_result['domain_name']
        
        if current_status != 'paused':
            return create_response(400, {'error': f'Cannot resume quiz in {current_status} state'})
        
        # Check if quiz is already completed
        if current_index >= total_questions:
            return create_response(400, {'error': 'Quiz is already completed'})
        
        # Update session to active
        update_query = """
            UPDATE quiz_sessions 
            SET status = 'active', paused_at = NULL
            WHERE id = %s
        """
        db_proxy.execute_query(update_query, (session_id,))
        
        quiz_mode = session_data.get('quiz_mode', 'forward')

        # Get current question
        term_order = session_data.get('term_order', [])
        if current_index < len(term_order):
            term_id = term_order[current_index]

            term_query = """
                SELECT data->>'term' as term, data->>'definition' as definition
                FROM tree_nodes
                WHERE id = %s
            """
            term_result = db_proxy.execute_query_one(term_query, (term_id,), return_dict=True)

            if term_result:
                current_question = build_question(term_id, term_result, current_index + 1, total_questions, quiz_mode)
            else:
                current_question = None
        else:
            current_question = None

        return create_response(200, {
            'session_id': session_id,
            'status': 'resumed',
            'domain_name': domain_name,
            'quiz_mode': quiz_mode,
            'current_question': current_question,
            'progress': {
                'current_index': current_index,
                'total_questions': total_questions,
                'completed': current_index >= total_questions
            }
        })

    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        logger.error(f"Error resuming quiz: {str(e)}")
        return handle_error(e)


def handle_complete_quiz(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle quiz completion and summary"""
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        session_id = query_params.get('session_id')
        
        if not session_id:
            return create_response(400, {'error': 'session_id is required'})
        
        # Verify session exists and belongs to user
        session_query = """
            SELECT qs.id, qs.status, qs.current_term_index, qs.total_questions, 
                   qs.correct_answers, qs.started_at, qs.completed_at, qs.session_data,
                   tn.data->>'name' as domain_name
            FROM quiz_sessions qs
            JOIN tree_nodes tn ON qs.domain_id = tn.id
            WHERE qs.id = %s AND qs.user_id = %s
        """
        session_result = db_proxy.execute_query_one(session_query, (session_id, user_id), return_dict=True)
        
        if not session_result:
            return create_response(404, {'error': 'Quiz session not found'})
        
        current_status = session_result['status']
        current_index = session_result['current_term_index']
        total_questions = session_result['total_questions']
        correct_answers = session_result['correct_answers']
        started_at = session_result['started_at']
        completed_at = session_result['completed_at']
        session_data = session_result['session_data'] or {}
        domain_name = session_result['domain_name']
        quiz_mode = session_data.get('quiz_mode', 'forward')
        
        # Check if quiz is completed
        if current_status != 'completed':
            # If quiz is not completed but all questions are answered, mark as completed
            if current_index >= total_questions:
                update_query = """
                    UPDATE quiz_sessions 
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                db_proxy.execute_query(update_query, (session_id,))
                completed_at = datetime.now()
            else:
                return create_response(400, {'error': 'Quiz is not yet completed'})
        
        # Get detailed progress records for this session
        progress_query = """
            SELECT pr.term_id, pr.student_answer, pr.correct_answer, pr.is_correct,
                   pr.similarity_score, pr.feedback, pr.created_at,
                   tn.data->>'term' as term, tn.data->>'definition' as definition
            FROM progress_records pr
            JOIN tree_nodes tn ON pr.term_id = tn.id
            WHERE pr.session_id = %s
            ORDER BY pr.created_at
        """
        progress_results = db_proxy.execute_query(progress_query, (session_id,), return_dict=True)
        
        # Calculate performance metrics
        total_attempts = len(progress_results)
        correct_count = sum(1 for record in progress_results if record['is_correct'])
        incorrect_count = total_attempts - correct_count
        
        if total_attempts > 0:
            accuracy_percentage = (correct_count / total_attempts) * 100
            average_similarity = sum(record['similarity_score'] or 0 for record in progress_results) / total_attempts
        else:
            accuracy_percentage = 0
            average_similarity = 0
        
        # Calculate time taken
        if started_at and completed_at:
            time_taken_seconds = (completed_at - started_at).total_seconds()
            time_taken_minutes = int(time_taken_seconds // 60)
            time_taken_seconds = int(time_taken_seconds % 60)
        else:
            time_taken_minutes = 0
            time_taken_seconds = 0
        
        # Prepare detailed results
        detailed_results = []
        for record in progress_results:
            detailed_results.append({
                'term': record['term'],
                'definition': record['definition'],
                'student_answer': record['student_answer'],
                'correct_answer': record['correct_answer'],
                'is_correct': record['is_correct'],
                'similarity_score': round(record['similarity_score'] or 0, 2),
                'feedback': record['feedback']
            })
        
        # Generate performance summary
        if accuracy_percentage >= 90:
            performance_level = 'Excellent'
            performance_message = 'Outstanding performance! You have mastered this domain.'
        elif accuracy_percentage >= 80:
            performance_level = 'Good'
            performance_message = 'Good job! You have a solid understanding of this domain.'
        elif accuracy_percentage >= 70:
            performance_level = 'Fair'
            performance_message = 'Fair performance. Consider reviewing the terms you missed.'
        else:
            performance_level = 'Needs Improvement'
            performance_message = 'You may want to study this domain more before retaking the quiz.'
        
        # Check if user can restart quiz (for practice)
        can_restart = True  # Always allow restart for practice
        
        quiz_summary = {
            'session_id': session_id,
            'domain_name': domain_name,
            'quiz_mode': quiz_mode,
            'status': 'completed',
            'completion_time': completed_at.isoformat() if completed_at else None,
            'performance': {
                'total_questions': total_questions,
                'correct_answers': correct_count,
                'incorrect_answers': incorrect_count,
                'accuracy_percentage': round(accuracy_percentage, 1),
                'average_similarity_score': round(average_similarity, 2),
                'performance_level': performance_level,
                'performance_message': performance_message
            },
            'timing': {
                'time_taken_minutes': time_taken_minutes,
                'time_taken_seconds': time_taken_seconds,
                'total_seconds': int((completed_at - started_at).total_seconds()) if started_at and completed_at else 0
            },
            'detailed_results': detailed_results,
            'actions': {
                'can_restart': can_restart,
                'can_review': True
            }
        }
        
        return create_response(200, quiz_summary)
        
    except Exception as e:
        logger.error(f"Error getting quiz completion summary: {str(e)}")
        return handle_error(e)


def handle_get_session(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle GET /quiz/session/{sessionId} - Get session details"""
    try:
        # Extract session_id from path parameters
        path_parameters = event.get('pathParameters', {})
        session_id = path_parameters.get('sessionId')
        
        if not session_id:
            return create_response(400, {'error': 'session_id is required'})
        
        # Validate UUID format
        try:
            uuid.UUID(session_id)
        except ValueError:
            return create_response(400, {'error': 'Invalid session_id format'})
        
        # Get session from database
        session_query = """
            SELECT 
                qs.id, qs.user_id, qs.domain_id, qs.status,
                qs.current_question_index, qs.total_questions,
                qs.started_at, qs.completed_at, qs.paused_at,
                d.name as domain_name
            FROM quiz_sessions qs
            JOIN domains d ON qs.domain_id = d.id
            WHERE qs.id = %s
        """
        session = db_proxy.execute_query_one(session_query, (session_id,), return_dict=True)
        
        if not session:
            return create_response(404, {'error': 'Quiz session not found'})
        
        # Verify session ownership
        if session['user_id'] != user_id:
            return create_response(403, {'error': 'Access denied to this quiz session'})
        
        # Get progress count
        progress_query = """
            SELECT COUNT(*) as answered_count
            FROM progress_records
            WHERE session_id = %s
        """
        progress_result = db_proxy.execute_query_one(progress_query, (session_id,), return_dict=True)
        answered_count = progress_result['answered_count'] if progress_result else 0
        
        # Build response
        session_details = {
            'session_id': session['id'],
            'domain_id': session['domain_id'],
            'domain_name': session['domain_name'],
            'status': session['status'],
            'progress': {
                'current_question': session['current_question_index'],
                'total_questions': session['total_questions'],
                'answered_count': answered_count,
                'percentage_complete': round((answered_count / session['total_questions'] * 100), 1) if session['total_questions'] > 0 else 0
            },
            'timestamps': {
                'started_at': session['started_at'].isoformat() if session['started_at'] else None,
                'completed_at': session['completed_at'].isoformat() if session['completed_at'] else None,
                'paused_at': session['paused_at'].isoformat() if session['paused_at'] else None
            }
        }
        
        return create_response(200, session_details)
        
    except Exception as e:
        logger.error(f"Error getting session details: {str(e)}")
        return handle_error(e)


def handle_delete_session(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle DELETE /quiz/session/{sessionId} - Delete session"""
    try:
        # Extract session_id from path parameters
        path_parameters = event.get('pathParameters', {})
        session_id = path_parameters.get('sessionId')
        
        if not session_id:
            return create_response(400, {'error': 'session_id is required'})
        
        # Validate UUID format
        try:
            uuid.UUID(session_id)
        except ValueError:
            return create_response(400, {'error': 'Invalid session_id format'})
        
        # Verify session exists and user owns it
        session_query = "SELECT user_id FROM quiz_sessions WHERE id = %s"
        session = db_proxy.execute_query_one(session_query, (session_id,), return_dict=True)
        
        if not session:
            return create_response(404, {'error': 'Quiz session not found'})
        
        if session['user_id'] != user_id:
            return create_response(403, {'error': 'Access denied to this quiz session'})
        
        # Delete progress records first (foreign key constraint)
        delete_progress_query = "DELETE FROM progress_records WHERE session_id = %s"
        db_proxy.execute_query(delete_progress_query, (session_id,))
        
        # Delete session
        delete_session_query = "DELETE FROM quiz_sessions WHERE id = %s"
        db_proxy.execute_query(delete_session_query, (session_id,))
        
        logger.info(f"Deleted quiz session {session_id} for user {user_id}")
        
        return create_response(200, {
            'message': 'Quiz session deleted successfully',
            'session_id': session_id
        })
        
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        return handle_error(e)
