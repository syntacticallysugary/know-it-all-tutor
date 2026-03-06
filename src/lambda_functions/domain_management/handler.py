"""
Domain Management Lambda Function Handler (Refactored for Lambda Bridge)
Handles CRUD operations for knowledge domains and terms using DB Proxy
"""
import json
import sys
import os
import logging
from typing import Dict, Any

# Add shared modules to path
sys.path.append('/opt/python')

from db_proxy_client import DBProxyClient
from response_utils import create_success_response, create_created_response, create_error_response
from auth_utils import extract_user_from_cognito_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize DB Proxy client
db_proxy = DBProxyClient(os.environ.get('DB_PROXY_FUNCTION_NAME'))


def lambda_handler(event, context):
    """
    Main handler for domain management operations
    Routes:
    - POST /domains - Create new domain
    - GET /domains - List user's domains
    - GET /domains/{id} - Get specific domain
    - PUT /domains/{id} - Update domain
    - DELETE /domains/{id} - Delete domain
    - POST /domains/{id}/terms - Add terms to domain
    - GET /domains/{id}/terms - Get domain terms
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
        if http_method == 'POST' and path.endswith('/domains'):
            return handle_create_domain(event, user_id)
        elif http_method == 'GET' and path.endswith('/domains'):
            return handle_get_domains(user_id)
        elif http_method == 'GET' and '/domains/' in path and not '/terms' in path:
            return handle_get_domain(event, user_id)
        elif http_method == 'PUT' and '/domains/' in path:
            return handle_update_domain(event, user_id)
        elif http_method == 'DELETE' and '/domains/' in path:
            return handle_delete_domain(event, user_id)
        elif http_method == 'POST' and '/terms' in path:
            return handle_add_terms(event, user_id)
        elif http_method == 'GET' and '/terms' in path:
            return handle_get_terms(event, user_id)
        else:
            return create_error_response(404, 'Endpoint not found')
            
    except Exception as e:
        logger.error(f"Domain management error: {e}", exc_info=True)
        return create_error_response(500, f'Internal server error: {str(e)}')


def handle_create_domain(event, user_id):
    """Create a new domain"""
    try:
        body = json.loads(event.get('body', '{}'))
        
        name = body.get('name', '').strip()
        description = body.get('description', '').strip()
        
        if not name or not description:
            return create_error_response(400, 'Name and description are required')
        
        if len(name) < 2 or len(name) > 100:
            return create_error_response(400, 'Name must be between 2 and 100 characters')
        
        if len(description) < 10 or len(description) > 500:
            return create_error_response(400, 'Description must be between 10 and 500 characters')
        
        # Check for duplicate
        existing = db_proxy.execute_query(
            """
            SELECT id FROM tree_nodes 
            WHERE (user_id = %s OR is_public = true) 
            AND node_type = 'domain' 
            AND data->>'name' = %s
            """,
            params=[user_id, name],
            return_dict=True
        )
        
        if existing and len(existing) > 0:
            return create_error_response(409, 'Domain with this name already exists')
        
        # Create domain
        domain_data = json.dumps({'name': name, 'description': description})
        metadata = json.dumps(body.get('metadata', {}))
        
        result = db_proxy.execute_query(
            """
            INSERT INTO tree_nodes (user_id, node_type, data, metadata)
            VALUES (%s, 'domain', %s, %s)
            RETURNING id, data, metadata, created_at
            """,
            params=[user_id, domain_data, metadata],
            return_dict=True
        )
        
        if not result or len(result) == 0:
            return create_error_response(500, 'Failed to create domain')
        
        domain = result[0]
        
        return create_created_response({
            'message': 'Domain created successfully',
            'domain': {
                'id': domain['id'],
                'name': domain['data']['name'],
                'description': domain['data']['description'],
                'metadata': domain.get('metadata', {}),
                'created_at': domain['created_at']
            }
        })
        
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        logger.error(f"Create domain error: {e}", exc_info=True)
        return create_error_response(500, f'Failed to create domain: {str(e)}')


def handle_get_domains(user_id):
    """Get all domains for user"""
    try:
        domains = db_proxy.execute_query(
            """
            SELECT 
                d.id,
                d.data,
                d.metadata,
                d.created_at,
                d.updated_at,
                COUNT(t.id) as term_count
            FROM tree_nodes d
            LEFT JOIN tree_nodes t ON t.parent_id = d.id AND t.node_type = 'term'
            WHERE (d.user_id = %s OR d.is_public = true) AND d.node_type = 'domain'
            GROUP BY d.id, d.data, d.metadata, d.created_at, d.updated_at
            ORDER BY d.created_at DESC
            """,
            params=[user_id],
            return_dict=True
        )
        
        domain_list = []
        for domain in domains:
            domain_list.append({
                'id': domain['id'],
                'name': domain['data']['name'],
                'description': domain['data']['description'],
                'metadata': domain.get('metadata', {}),
                'term_count': domain['term_count'],
                'created_at': domain['created_at'],
                'updated_at': domain['updated_at']
            })
        
        return create_success_response({
            'domains': domain_list,
            'count': len(domain_list)
        })
        
    except Exception as e:
        logger.error(f"Get domains error: {e}", exc_info=True)
        return create_error_response(500, f'Failed to get domains: {str(e)}')


def handle_get_domain(event, user_id):
    """Get specific domain by ID"""
    try:
        # Extract domain_id from path
        path = event.get('path', '')
        domain_id = path.split('/domains/')[-1].split('/')[0]
        
        domain = db_proxy.execute_query(
            """
            SELECT 
                d.id,
                d.data,
                d.metadata,
                d.created_at,
                d.updated_at,
                COUNT(t.id) as term_count
            FROM tree_nodes d
            LEFT JOIN tree_nodes t ON t.parent_id = d.id AND t.node_type = 'term'
            WHERE d.id = %s AND (d.user_id = %s OR d.is_public = true) AND d.node_type = 'domain'
            GROUP BY d.id, d.data, d.metadata, d.created_at, d.updated_at
            """,
            params=[domain_id, user_id],
            return_dict=True
        )
        
        if not domain or len(domain) == 0:
            return create_error_response(404, 'Domain not found')
        
        d = domain[0]
        
        return create_success_response({
            'domain': {
                'id': d['id'],
                'name': d['data']['name'],
                'description': d['data']['description'],
                'metadata': d.get('metadata', {}),
                'term_count': d['term_count'],
                'created_at': d['created_at'],
                'updated_at': d['updated_at']
            }
        })
        
    except Exception as e:
        logger.error(f"Get domain error: {e}", exc_info=True)
        return create_error_response(500, f'Failed to get domain: {str(e)}')


def handle_update_domain(event, user_id):
    """Update domain"""
    try:
        path = event.get('path', '')
        domain_id = path.split('/domains/')[-1].split('/')[0]
        
        body = json.loads(event.get('body', '{}'))
        
        # Verify ownership
        existing = db_proxy.execute_query(
            "SELECT id FROM tree_nodes WHERE id = %s AND user_id = %s AND node_type = 'domain'",
            params=[domain_id, user_id],
            return_dict=True
        )
        
        if not existing or len(existing) == 0:
            return create_error_response(404, 'Domain not found')
        
        # Build update
        updates = []
        params = []
        
        if 'name' in body or 'description' in body:
            # Get current data
            current = db_proxy.execute_query(
                "SELECT data FROM tree_nodes WHERE id = %s",
                params=[domain_id],
                return_dict=True
            )[0]
            
            data = current['data']
            if 'name' in body:
                data['name'] = body['name'].strip()
            if 'description' in body:
                data['description'] = body['description'].strip()
            
            updates.append("data = %s")
            params.append(json.dumps(data))
        
        if 'metadata' in body:
            updates.append("metadata = %s")
            params.append(json.dumps(body['metadata']))
        
        if not updates:
            return create_error_response(400, 'No valid fields to update')
        
        params.append(domain_id)
        
        result = db_proxy.execute_query(
            f"""
            UPDATE tree_nodes
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id, data, metadata, updated_at
            """,
            params=params,
            return_dict=True
        )
        
        if not result or len(result) == 0:
            return create_error_response(500, 'Failed to update domain')
        
        d = result[0]
        
        return create_success_response({
            'message': 'Domain updated successfully',
            'domain': {
                'id': d['id'],
                'name': d['data']['name'],
                'description': d['data']['description'],
                'metadata': d.get('metadata', {}),
                'updated_at': d['updated_at']
            }
        })
        
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        logger.error(f"Update domain error: {e}", exc_info=True)
        return create_error_response(500, f'Failed to update domain: {str(e)}')


def handle_delete_domain(event, user_id):
    """Delete domain (cascades to terms)"""
    try:
        path = event.get('path', '')
        domain_id = path.split('/domains/')[-1].split('/')[0]
        
        # Verify ownership
        existing = db_proxy.execute_query(
            "SELECT id FROM tree_nodes WHERE id = %s AND user_id = %s AND node_type = 'domain'",
            params=[domain_id, user_id],
            return_dict=True
        )
        
        if not existing or len(existing) == 0:
            return create_error_response(404, 'Domain not found')
        
        # Delete (cascades to terms due to foreign key)
        db_proxy.execute_query(
            "DELETE FROM tree_nodes WHERE id = %s",
            params=[domain_id]
        )
        
        return create_success_response({
            'message': 'Domain deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Delete domain error: {e}", exc_info=True)
        return create_error_response(500, f'Failed to delete domain: {str(e)}')


def handle_add_terms(event, user_id):
    """Add terms to domain"""
    try:
        path = event.get('path', '')
        domain_id = path.split('/domains/')[-1].split('/terms')[0]
        
        body = json.loads(event.get('body', '{}'))
        terms = body.get('terms', [])
        
        if not terms or not isinstance(terms, list):
            return create_error_response(400, 'Terms array is required')
        
        # Verify domain ownership
        domain = db_proxy.execute_query(
            "SELECT id FROM tree_nodes WHERE id = %s AND user_id = %s AND node_type = 'domain'",
            params=[domain_id, user_id],
            return_dict=True
        )
        
        if not domain or len(domain) == 0:
            return create_error_response(404, 'Domain not found')
        
        # Insert terms
        created_terms = []
        for term_data in terms:
            if not term_data.get('term') or not term_data.get('definition'):
                continue
            
            term_json = json.dumps({
                'term': term_data['term'].strip(),
                'definition': term_data['definition'].strip(),
                'example': term_data.get('example', ''),
                'tags': term_data.get('tags', [])
            })
            
            result = db_proxy.execute_query(
                """
                INSERT INTO tree_nodes (user_id, parent_id, node_type, data)
                VALUES (%s, %s, 'term', %s)
                RETURNING id, data, created_at
                """,
                params=[user_id, domain_id, term_json],
                return_dict=True
            )
            
            if result and len(result) > 0:
                t = result[0]
                created_terms.append({
                    'id': t['id'],
                    'term': t['data']['term'],
                    'definition': t['data']['definition'],
                    'created_at': t['created_at']
                })
        
        return create_created_response({
            'message': f'{len(created_terms)} terms added successfully',
            'terms': created_terms
        })
        
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        logger.error(f"Add terms error: {e}", exc_info=True)
        return create_error_response(500, f'Failed to add terms: {str(e)}')


def handle_get_terms(event, user_id):
    """Get terms for domain"""
    try:
        path = event.get('path', '')
        domain_id = path.split('/domains/')[-1].split('/terms')[0]
        
        # Verify domain ownership
        domain = db_proxy.execute_query(
            "SELECT id FROM tree_nodes WHERE id = %s AND user_id = %s AND node_type = 'domain'",
            params=[domain_id, user_id],
            return_dict=True
        )
        
        if not domain or len(domain) == 0:
            return create_error_response(404, 'Domain not found')
        
        # Get terms
        terms = db_proxy.execute_query(
            """
            SELECT id, data, created_at, updated_at
            FROM tree_nodes
            WHERE parent_id = %s AND node_type = 'term'
            ORDER BY created_at
            """,
            params=[domain_id],
            return_dict=True
        )
        
        term_list = []
        for term in terms:
            term_list.append({
                'id': term['id'],
                'term': term['data']['term'],
                'definition': term['data']['definition'],
                'example': term['data'].get('example', ''),
                'tags': term['data'].get('tags', []),
                'created_at': term['created_at'],
                'updated_at': term['updated_at']
            })
        
        return create_success_response({
            'terms': term_list,
            'count': len(term_list)
        })
        
    except Exception as e:
        logger.error(f"Get terms error: {e}", exc_info=True)
        return create_error_response(500, f'Failed to get terms: {str(e)}')
