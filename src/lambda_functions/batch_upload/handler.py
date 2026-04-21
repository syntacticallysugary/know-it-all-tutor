"""
Batch Upload Lambda Function Handler
Handles batch upload validation and processing for knowledge domains with role-based authorization
Requirements: 8.1, 8.2, 8.3, 8.4
"""
import json
import uuid
import logging
import sys
import os
from typing import Dict, Any, List, Optional, Tuple

# Add shared modules to path
sys.path.append('/opt/python')

from db_proxy_client import DBProxyClient
from response_utils import (
    create_success_response, create_created_response, create_error_response,
    create_validation_error_response, create_not_found_response,
    parse_request_body, get_path_parameters, get_query_parameters,
    handle_error
)
from auth_utils import extract_user_from_cognito_event
from authorization_utils import validate_api_access, AuthorizationError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize DB Proxy client
db_proxy = DBProxyClient(os.environ.get('DB_PROXY_FUNCTION_NAME'))


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for batch upload operations with role-based authorization
    """
    logger.info(f"Batch upload handler invoked: {event.get('httpMethod')} {event.get('path')}")
    
    try:
        http_method = event.get('httpMethod')
        path = event.get('path', '')
        
        logger.info(f"Validating authorization for user...")
        
        # Validate authorization for batch upload operations (requires instructor or admin)
        try:
            user_info = validate_api_access(event, ['batch_upload'])
            logger.info(f"Authorization successful for user: {user_info.get('user_id')}")
        except AuthorizationError as e:
            logger.error(f"Authorization failed: {str(e)}")
            return create_error_response(403, str(e))
        
        cognito_sub = user_info['user_id']
        
        # Look up database user ID from cognito_sub
        user_query = "SELECT id FROM users WHERE cognito_sub = %s;"
        user_result = db_proxy.execute_query_one(user_query, [cognito_sub])
        
        if not user_result:
            logger.error(f"User not found in database for cognito_sub: {cognito_sub}")
            return create_error_response(404, "User not found in database")
        
        user_id = user_result[0]
        logger.info(f"Resolved database user_id: {user_id}")
        
        if http_method == 'POST':
            if path.endswith('/validate'):
                return handle_validate_batch_upload(event, user_id)
            elif path.endswith('/upload'):
                return handle_process_batch_upload(event, user_id)
        elif http_method == 'GET':
            if path.endswith('/history'):
                return handle_get_upload_history(event, user_id)
        
        return create_error_response(404, 'Endpoint not found')
        
    except Exception as e:
        logger.error(f"Batch upload error: {str(e)}", exc_info=True)
        return handle_error(e)


def handle_validate_batch_upload(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Handle batch upload validation against the improved schema
    Requirements: 8.3
    """
    try:
        logger.info("Parsing request body...")
        body = parse_request_body(event)
        logger.info(f"Body keys: {list(body.keys())}")
        
        if 'batch_data' not in body:
            logger.warning("Missing batch_data in request body")
            return create_validation_error_response({
                'batch_data': 'Batch data is required'
            })
        
        batch_data = body['batch_data']
        logger.info(f"Batch data keys: {list(batch_data.keys())}")
        logger.info(f"Number of domains: {len(batch_data.get('domains', []))}")
        
        # Validate JSON structure
        logger.info("Validating batch structure...")
        validation_result = validate_batch_structure(batch_data)
        if not validation_result['valid']:
            logger.warning(f"Batch structure validation failed: {validation_result['errors']}")
            return create_validation_error_response(validation_result['errors'])
        
        # Validate domains and terms
        logger.info("Validating domains and terms...")
        domain_validation = validate_domains_and_terms(batch_data.get('domains', []))
        if not domain_validation['valid']:
            logger.warning(f"Domain validation failed: {domain_validation['errors']}")
            return create_validation_error_response(domain_validation['errors'])
        
        # Check for duplicates within batch
        logger.info("Checking for duplicates within batch...")
        duplicate_validation = validate_no_duplicates_in_batch(batch_data.get('domains', []))
        if not duplicate_validation['valid']:
            logger.warning(f"Duplicate validation failed: {duplicate_validation['errors']}")
            return create_validation_error_response(duplicate_validation['errors'])
        
        # Check for duplicates with existing user data
        logger.info("Checking for existing duplicates...")
        existing_duplicates = check_existing_duplicates(batch_data.get('domains', []), user_id)
        logger.info(f"Found {len(existing_duplicates)} existing duplicates")
        
        validation_summary = {
            'valid': True,
            'total_domains': len(batch_data.get('domains', [])),
            'total_terms': sum(len(domain.get('terms', [])) for domain in batch_data.get('domains', [])),
            'existing_duplicates': existing_duplicates,
            'warnings': []
        }
        
        if existing_duplicates:
            validation_summary['warnings'].append(
                f"Found {len(existing_duplicates)} domains that already exist and will be skipped"
            )
        
        logger.info(f"Validation successful: {validation_summary}")
        return create_success_response(validation_summary, 'Batch upload validation completed')
        
    except Exception as e:
        logger.error(f"Error validating batch upload: {str(e)}", exc_info=True)
        return handle_error(e)


def validate_batch_structure(batch_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the overall structure of the batch upload JSON
    """
    errors = {}
    
    # Check required top-level fields
    if not isinstance(batch_data, dict):
        errors['batch_data'] = 'Batch data must be a JSON object'
        return {'valid': False, 'errors': errors}
    
    # Validate batch_metadata (optional)
    if 'batch_metadata' in batch_data:
        metadata = batch_data['batch_metadata']
        if not isinstance(metadata, dict):
            errors['batch_metadata'] = 'batch_metadata must be an object'
        else:
            # Validate metadata types if present
            if 'total_domains' in metadata and not isinstance(metadata['total_domains'], int):
                errors['batch_metadata.total_domains'] = 'total_domains must be an integer'
            if 'total_terms' in metadata and not isinstance(metadata['total_terms'], int):
                errors['batch_metadata.total_terms'] = 'total_terms must be an integer'
    
    # Validate domains array
    if 'domains' not in batch_data:
        errors['domains'] = 'domains array is required'
    else:
        domains = batch_data['domains']
        if not isinstance(domains, list):
            errors['domains'] = 'domains must be an array'
        elif len(domains) == 0:
            errors['domains'] = 'At least one domain is required'
    
    return {'valid': len(errors) == 0, 'errors': errors}


def validate_domains_and_terms(domains: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate individual domains and their terms
    """
    errors = {}
    
    for i, domain in enumerate(domains):
        domain_prefix = f'domains[{i}]'
        
        # Validate domain structure
        if not isinstance(domain, dict):
            errors[domain_prefix] = 'Each domain must be an object'
            continue
        
        # Check required domain fields
        if 'node_type' not in domain or domain['node_type'] != 'domain':
            errors[f'{domain_prefix}.node_type'] = 'node_type must be "domain"'
        
        if 'data' not in domain:
            errors[f'{domain_prefix}.data'] = 'data field is required'
        else:
            domain_data = domain['data']
            if not isinstance(domain_data, dict):
                errors[f'{domain_prefix}.data'] = 'data must be an object'
            else:
                # Validate required domain data fields
                required_domain_fields = ['name', 'description']
                for field in required_domain_fields:
                    if field not in domain_data:
                        errors[f'{domain_prefix}.data.{field}'] = f'{field} is required'
                    elif not isinstance(domain_data[field], str) or not domain_data[field].strip():
                        errors[f'{domain_prefix}.data.{field}'] = f'{field} must be a non-empty string'
                
                # Validate field lengths
                if 'name' in domain_data:
                    name = domain_data['name'].strip()
                    if len(name) < 2 or len(name) > 100:
                        errors[f'{domain_prefix}.data.name'] = 'Domain name must be between 2 and 100 characters'
                
                if 'description' in domain_data:
                    description = domain_data['description'].strip()
                    if len(description) < 10 or len(description) > 500:
                        errors[f'{domain_prefix}.data.description'] = 'Domain description must be between 10 and 500 characters'
        
        # Validate terms array
        if 'terms' not in domain:
            errors[f'{domain_prefix}.terms'] = 'terms array is required'
        else:
            terms = domain['terms']
            if not isinstance(terms, list):
                errors[f'{domain_prefix}.terms'] = 'terms must be an array'
            elif len(terms) == 0:
                errors[f'{domain_prefix}.terms'] = 'At least one term is required per domain'
            else:
                # Validate each term
                for j, term in enumerate(terms):
                    term_prefix = f'{domain_prefix}.terms[{j}]'
                    
                    if not isinstance(term, dict):
                        errors[term_prefix] = 'Each term must be an object'
                        continue
                    
                    # Check required term fields
                    if 'node_type' not in term or term['node_type'] != 'term':
                        errors[f'{term_prefix}.node_type'] = 'node_type must be "term"'
                    
                    if 'data' not in term:
                        errors[f'{term_prefix}.data'] = 'data field is required'
                    else:
                        term_data = term['data']
                        if not isinstance(term_data, dict):
                            errors[f'{term_prefix}.data'] = 'data must be an object'
                        else:
                            # Validate required term data fields
                            required_term_fields = ['term', 'definition']
                            for field in required_term_fields:
                                if field not in term_data:
                                    errors[f'{term_prefix}.data.{field}'] = f'{field} is required'
                                elif not isinstance(term_data[field], str) or not term_data[field].strip():
                                    errors[f'{term_prefix}.data.{field}'] = f'{field} must be a non-empty string'
                            
                            # Validate field lengths
                            if 'term' in term_data:
                                term_name = term_data['term'].strip()
                                if len(term_name) < 2 or len(term_name) > 200:
                                    errors[f'{term_prefix}.data.term'] = 'Term must be between 2 and 200 characters'
                            
                            if 'definition' in term_data:
                                definition = term_data['definition'].strip()
                                if len(definition) < 10 or len(definition) > 10000:
                                    errors[f'{term_prefix}.data.definition'] = 'Definition must be between 10 and 10000 characters'
    
    return {'valid': len(errors) == 0, 'errors': errors}


def validate_no_duplicates_in_batch(domains: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Check for duplicate domains and terms within the batch upload
    """
    errors = {}
    domain_names = set()
    
    for i, domain in enumerate(domains):
        if not isinstance(domain, dict) or 'data' not in domain:
            continue
        
        domain_data = domain['data']
        if not isinstance(domain_data, dict) or 'name' not in domain_data:
            continue
        
        domain_name = domain_data['name'].strip().lower()
        
        # Check for duplicate domain names
        if domain_name in domain_names:
            errors[f'domains[{i}].data.name'] = f'Duplicate domain name: "{domain_data["name"]}"'
        else:
            domain_names.add(domain_name)
        
        # Check for duplicate terms within this domain
        if 'terms' in domain and isinstance(domain['terms'], list):
            term_names = set()
            for j, term in enumerate(domain['terms']):
                if not isinstance(term, dict) or 'data' not in term:
                    continue
                
                term_data = term['data']
                if not isinstance(term_data, dict) or 'term' not in term_data:
                    continue
                
                term_name = term_data['term'].strip().lower()
                
                if term_name in term_names:
                    errors[f'domains[{i}].terms[{j}].data.term'] = f'Duplicate term in domain: "{term_data["term"]}"'
                else:
                    term_names.add(term_name)
    
    return {'valid': len(errors) == 0, 'errors': errors}


def check_existing_duplicates(domains: List[Dict[str, Any]], user_id: str) -> List[str]:
    """
    Check for domains that already exist for this user
    """
    existing_duplicates = []
    
    for domain in domains:
        if not isinstance(domain, dict) or 'data' not in domain:
            continue
        
        domain_data = domain['data']
        if not isinstance(domain_data, dict) or 'name' not in domain_data:
            continue
        
        domain_name = domain_data['name'].strip()
        
        # Check if domain already exists for this user
        existing_domain = db_proxy.execute_query_one(
            """
            SELECT id FROM tree_nodes 
            WHERE user_id = %s AND node_type = 'domain' 
            AND data->>'name' = %s
            """,
            (user_id, domain_name)
        )
        
        if existing_domain:
            existing_duplicates.append(domain_name)
    
    return existing_duplicates


def handle_process_batch_upload(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Handle batch domain and term insertion with transaction management
    Requirements: 8.4
    """
    try:
        body = parse_request_body(event)
        
        if 'batch_data' not in body:
            return create_validation_error_response({
                'batch_data': 'Batch data is required'
            })
        
        batch_data = body['batch_data']
        
        # Re-validate the batch data
        validation_result = validate_batch_structure(batch_data)
        if not validation_result['valid']:
            return create_validation_error_response(validation_result['errors'])
        
        domain_validation = validate_domains_and_terms(batch_data.get('domains', []))
        if not domain_validation['valid']:
            return create_validation_error_response(domain_validation['errors'])
        
        # Process the batch upload in a transaction
        result = process_batch_upload_transaction(batch_data, user_id)
        
        if not result['success']:
            # Record failed upload in history
            upload_record = record_upload_history(
                user_id, 
                batch_data.get('batch_metadata', {}).get('filename', 'unknown'),
                result.get('domains_created_before_failure', 0),
                result.get('terms_created_before_failure', 0),
                status='failed',
                error_message=result['error']
            )
            
            return create_error_response(500, result['error'], {
                'upload_id': upload_record['id'],
                'domains_processed': result.get('domains_processed', 0),
                'recovery_action': result.get('recovery_action', 'Transaction rolled back')
            })
        
        # Record successful upload history
        upload_record = record_upload_history(
            user_id, 
            batch_data.get('batch_metadata', {}).get('filename', 'unknown'),
            result['domains_created'],
            result['terms_created'],
            status='completed'
        )
        
        response_data = {
            'upload_id': upload_record['id'],
            'domains_created': result['domains_created'],
            'terms_created': result['terms_created'],
            'domains_skipped': result['domains_skipped'],
            'processing_summary': result['summary']
        }
        
        return create_created_response(
            response_data,
            f'Batch upload completed: {result["domains_created"]} domains, {result["terms_created"]} terms created'
        )
        
    except Exception as e:
        logger.error(f"Error processing batch upload: {str(e)}")
        return handle_error(e)


def process_batch_upload_transaction(batch_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Process batch upload using DB Proxy
    Note: DB Proxy doesn't support explicit transactions, so each operation is atomic.
    Requirements: 8.4
    """
    try:
        domains_created = 0
        terms_created = 0
        domains_skipped = 0
        processing_summary = []
        failed_domains = []
        
        # Process each domain in the batch
        for domain_index, domain in enumerate(batch_data.get('domains', [])):
            try:
                domain_data = domain['data']
                domain_name = domain_data['name'].strip()
                
                # Check if domain already exists
                existing_domain = db_proxy.execute_query(
                    """
                    SELECT id FROM tree_nodes 
                    WHERE (user_id = %s OR is_public = true) AND node_type = 'domain' 
                    AND data->>'name' = %s
                    """,
                    params=[user_id, domain_name],
                    return_dict=True
                )
                
                # Determine if creating new domain or merging terms
                if existing_domain and len(existing_domain) > 0:
                    # Domain exists - merge terms
                    domain_id = existing_domain[0]['id']
                    domains_skipped += 1
                    
                    # Get existing terms for this domain
                    existing_terms = db_proxy.execute_query(
                        """
                        SELECT data->>'term' as term_name
                        FROM tree_nodes
                        WHERE parent_id = %s AND node_type = 'term'
                        """,
                        params=[domain_id],
                        return_dict=True
                    )
                    existing_term_names = {t['term_name'].lower() for t in existing_terms}
                    
                    domain_terms_created = 0
                    terms_skipped = 0
                    
                else:
                    # New domain - validate and create
                    if not domain_name or len(domain_name.strip()) < 2:
                        raise ValueError(f"Invalid domain name: '{domain_name}'")
                    
                    if not domain_data.get('description') or len(domain_data['description'].strip()) < 10:
                        raise ValueError(f"Invalid domain description for '{domain_name}'")
                    
                    # Create domain
                    domain_id = str(uuid.uuid4())
                    domain_payload = {
                        'name': domain_name,
                        'description': domain_data['description'].strip(),
                        'created_by': str(user_id)
                    }
                    
                    # Preserve optional domain fields
                    optional_fields = ['subject', 'difficulty', 'estimated_hours', 'prerequisites']
                    for field in optional_fields:
                        if field in domain_data:
                            domain_payload[field] = domain_data[field]
                    
                    # Preserve domain metadata
                    domain_metadata = {'term_count': 0}
                    if 'metadata' in domain and isinstance(domain['metadata'], dict):
                        domain_metadata.update(domain['metadata'])
                    
                    # Insert domain (mark as public for batch uploads)
                    db_proxy.execute_query(
                        """
                        INSERT INTO tree_nodes (id, user_id, node_type, data, metadata, is_public)
                        VALUES (%s, %s, 'domain', %s, %s, true)
                        """,
                        params=[domain_id, user_id, json.dumps(domain_payload), json.dumps(domain_metadata)]
                    )
                    
                    domains_created += 1
                    domain_terms_created = 0
                    terms_skipped = 0
                    existing_term_names = set()
                
                # Process terms for this domain (new or existing)
                for term_index, term in enumerate(domain.get('terms', [])):
                    try:
                        term_data = term['data']
                        term_name = term_data['term'].strip()
                        term_definition = term_data['definition'].strip()
                        
                        # Skip if term already exists in domain
                        if term_name.lower() in existing_term_names:
                            terms_skipped += 1
                            continue
                        
                        # Validate term data
                        if not term_name or len(term_name) < 2:
                            raise ValueError(f"Invalid term name: '{term_name}' in domain '{domain_name}'")
                        
                        if not term_definition or len(term_definition) < 10:
                            raise ValueError(f"Invalid term definition for '{term_name}' in domain '{domain_name}'")
                        
                        term_id = str(uuid.uuid4())
                        
                        # Build term payload
                        term_payload = {
                            'term': term_name,
                            'definition': term_definition
                        }
                        
                        # Add optional term fields
                        optional_term_fields = ['difficulty', 'module', 'examples', 'code_example']
                        for field in optional_term_fields:
                            if field in term_data:
                                term_payload[field] = term_data[field]
                        
                        # Preserve term metadata
                        term_metadata = term.get('metadata', {})
                        
                        # Insert term
                        db_proxy.execute_query(
                            """
                            INSERT INTO tree_nodes (id, parent_id, user_id, node_type, data, metadata)
                            VALUES (%s, %s, %s, 'term', %s, %s)
                            """,
                            params=[term_id, domain_id, user_id, json.dumps(term_payload), json.dumps(term_metadata)]
                        )
                        
                        domain_terms_created += 1
                        terms_created += 1
                        
                    except Exception as term_error:
                        logger.error(f"Error processing term {term_index} in domain '{domain_name}': {str(term_error)}")
                        raise ValueError(f"Failed to process term in domain '{domain_name}': {str(term_error)}")
                
                # Update domain term count
                current_term_count = len(existing_term_names) + domain_terms_created
                db_proxy.execute_query(
                    """
                    UPDATE tree_nodes 
                    SET metadata = jsonb_set(metadata, '{term_count}', %s::jsonb),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    params=[json.dumps(current_term_count), domain_id]
                )
                
                # Create summary message
                if domain_id in [d['id'] for d in existing_domain] if existing_domain else []:
                    processing_summary.append(
                        f"Merged into existing domain '{domain_name}': "
                        f"{domain_terms_created} new terms added, {terms_skipped} duplicates skipped"
                    )
                else:
                    processing_summary.append(f"Created domain '{domain_name}' with {domain_terms_created} terms")
                
            except Exception as domain_error:
                error_msg = f"Error processing domain {domain_index + 1} '{domain.get('data', {}).get('name', 'unknown')}': {str(domain_error)}"
                logger.error(error_msg)
                failed_domains.append({
                    'domain_index': domain_index,
                    'domain_name': domain.get('data', {}).get('name', 'unknown'),
                    'error': str(domain_error)
                })
                # Continue with other domains instead of failing entire batch
                continue
        
        # Return results
        logger.info(f"Batch upload completed: {domains_created} domains, {terms_created} terms created")
        
        return {
            'success': True,
            'domains_created': domains_created,
            'terms_created': terms_created,
            'domains_skipped': domains_skipped,
            'failed_domains': failed_domains,
            'summary': processing_summary,
            'total_processed': len(batch_data.get('domains', []))
        }
        
    except Exception as e:
        error_msg = f"Database transaction failed: {str(e)}"
        logger.error(f"Error in batch upload: {error_msg}")
        
        return {
            'success': False,
            'error': error_msg,
            'domains_created': domains_created,
            'terms_created': terms_created
        }


def record_upload_history(user_id: str, filename: str, domains_count: int, terms_count: int, status: str = 'completed', error_message: str = None) -> Dict[str, Any]:
    """
    Record batch upload in history for tracking with comprehensive metadata
    """
    upload_id = str(uuid.uuid4())
    
    metadata = {
        'domains_created': domains_count,
        'terms_created': terms_count,
        'total_items': domains_count + terms_count,
        'upload_timestamp': str(uuid.uuid1().time),
        'processing_details': {
            'status': status,
            'has_errors': error_message is not None
        }
    }
    
    # Add error details if present
    if error_message:
        metadata['error_details'] = {
            'message': error_message,
            'timestamp': str(uuid.uuid1().time)
        }
    
    try:
        db_proxy.execute_query(
            """
            INSERT INTO batch_uploads (id, admin_id, filename, subject_count, status, error_message, metadata, processed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """,
            (upload_id, user_id, filename, domains_count, status, error_message, json.dumps(metadata))
        )
        
        logger.info(f"Recorded upload history: {upload_id} for user {user_id}, status: {status}")
        
    except Exception as e:
        logger.error(f"Failed to record upload history: {str(e)}")
        # Don't fail the entire operation if history recording fails
        pass
    
    return {
        'id': upload_id,
        'filename': filename,
        'domains_count': domains_count,
        'terms_count': terms_count,
        'status': status,
        'error_message': error_message
    }


def handle_get_upload_history(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Handle retrieving upload history for the user
    """
    try:
        # Get upload history for the user
        uploads = db_proxy.execute_query(
            """
            SELECT 
                id, filename, subject_count, status, uploaded_at, 
                processed_at, error_message, metadata
            FROM batch_uploads
            WHERE admin_id = %s
            ORDER BY uploaded_at DESC
            LIMIT 50
            """,
            (user_id,)
        )
        
        upload_list = []
        for upload in uploads:
            upload_data = {
                'id': upload[0],
                'filename': upload[1],
                'subject_count': upload[2],
                'status': upload[3],
                'uploaded_at': upload[4].isoformat() if upload[4] else None,
                'processed_at': upload[5].isoformat() if upload[5] else None,
                'error_message': upload[6],
                'metadata': upload[7] if upload[7] else {}
            }
            upload_list.append(upload_data)
        
        return create_success_response(upload_list)
        
    except Exception as e:
        logger.error(f"Error retrieving upload history: {str(e)}")
        return handle_error(e)