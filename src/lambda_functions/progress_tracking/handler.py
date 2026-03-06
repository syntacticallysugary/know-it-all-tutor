"""
Progress Tracking Lambda Function Handler
Handles dashboard data and progress statistics using DB Proxy
"""
import json
import sys
import os
import logging
from typing import Dict, Any
from datetime import datetime, timedelta

# Add shared modules to path
sys.path.append('/opt/python')

from db_proxy_client import DBProxyClient
from response_utils import create_success_response, create_error_response
from auth_utils import extract_user_from_cognito_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize DB Proxy client
db_proxy = DBProxyClient(os.environ.get('DB_PROXY_FUNCTION_NAME'))


def lambda_handler(event, context):
    """
    Main handler for progress tracking operations
    Routes:
    - GET /progress/dashboard - Get dashboard data with stats and recent activity
    """
    try:
        http_method = event.get('httpMethod')
        path = event.get('path', '')
        
        auth_result = extract_user_from_cognito_event(event)
        if not auth_result['valid']:
            return create_error_response(401, 'Unauthorized - No user identity found')
        cognito_sub = auth_result['user_id']
        
        # Get user_id from database
        user_result = db_proxy.execute_query(
            "SELECT id FROM users WHERE cognito_sub = %s",
            params=[cognito_sub],
            return_dict=True
        )
        
        if not user_result or len(user_result) == 0:
            return create_error_response(404, 'User not found')
        
        user_id = user_result[0]['id']
        
        # Route to appropriate handler
        if http_method == 'GET' and '/dashboard' in path:
            return handle_get_dashboard(user_id)
        else:
            return create_error_response(404, 'Endpoint not found')
            
    except Exception as e:
        logger.error(f"Progress tracking error: {e}", exc_info=True)
        return create_error_response(500, f'Internal server error: {str(e)}')


def handle_get_dashboard(user_id):
    """Get comprehensive dashboard data for user"""
    try:
        # Get all domains with term counts
        domains = db_proxy.execute_query(
            """
            SELECT 
                d.id,
                d.data,
                d.created_at,
                COUNT(DISTINCT t.id) as term_count
            FROM tree_nodes d
            LEFT JOIN tree_nodes t ON t.parent_id = d.id AND t.node_type = 'term'
            WHERE d.user_id = %s AND d.node_type = 'domain'
            GROUP BY d.id, d.data, d.created_at
            ORDER BY d.created_at DESC
            """,
            params=[user_id],
            return_dict=True
        )
        
        # Build domain list (no progress data yet - quiz functionality not implemented)
        domain_list = []
        total_terms = 0
        
        for domain in domains:
            term_count = domain['term_count']
            total_terms += term_count
            
            domain_list.append({
                'id': domain['id'],
                'name': domain['data']['name'],
                'description': domain['data']['description'],
                'term_count': term_count,
                'completion_percentage': 0,  # TODO: Calculate from quiz sessions
                'mastery_percentage': 0,  # TODO: Calculate from quiz sessions
                'mastery_breakdown': {
                    'mastered': 0,
                    'proficient': 0,
                    'developing': 0,
                    'needs_practice': 0,
                    'not_attempted': term_count
                }
            })
        
        # Build dashboard response
        dashboard_data = {
            'user_id': user_id,
            'total_domains': len(domains),
            'domains': domain_list,
            'overall_stats': {
                'total_terms': total_terms,
                'mastered_terms': 0,
                'proficient_terms': 0,
                'developing_terms': 0,
                'needs_practice_terms': 0,
                'not_attempted_terms': total_terms,
                'overall_completion_percentage': 0,
                'overall_mastery_percentage': 0
            },
            'recent_activity': [],  # TODO: Populate from quiz sessions
            'learning_streaks': None  # TODO: Implement streak tracking
        }
        
        return create_success_response(dashboard_data)
        
    except Exception as e:
        logger.error(f"Get dashboard error: {e}", exc_info=True)
        return create_error_response(500, f'Failed to get dashboard: {str(e)}')
