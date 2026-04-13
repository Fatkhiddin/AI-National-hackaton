"""
CRM Service - CRM tizimlar bilan integratsiya
Uy-joy CRM dan ma'lumot olish va qidirish
"""
import json
import logging
import httpx
from typing import Dict, List, Optional, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class CRMService:
    """CRM bilan ishlash uchun service"""
    
    def __init__(self, crm_provider):
        """
        Args:
            crm_provider: CRMProvider model instance
        """
        self.crm_provider = crm_provider
        self.api_url = crm_provider.api_url
        self.api_key = crm_provider.api_key
        self.field_mapping = crm_provider.field_mapping or {}
    
    def extract_requirements_prompt(self, conversation_summary: Dict) -> str:
        """
        Generate AI prompt to extract property requirements from conversation
        
        Args:
            conversation_summary: ConversationSummary.summary_data
            
        Returns:
            Prompt string for AI
        """
        if self.crm_provider.extraction_prompt:
            # Use custom prompt if provided
            return self.crm_provider.extraction_prompt
        
        # Extract ONLY from this one message!
        msg = conversation_summary.get('latest_message', '')
        
        # Ultra-simple extraction prompt
        return f'''
Message: "{msg}"

Extract ONLY numbers from THIS message:
- rooms: number of rooms (3 xonali → 3)
- price_min: minimum price in USD (50000 or 50,000 → 50000)
- price_max: maximum price in USD (80000 or 80,000 → 80000)

If NOT mentioned → null

JSON only:
{{"rooms": 3, "price_min": 50000, "price_max": 80000}}
'''
    
    async def extract_requirements_with_ai(
        self, 
        conversation_summary: Dict,
        ai_service
    ) -> Dict[str, Any]:
        """
        Use AI to extract property requirements from conversation
        
        Args:
            conversation_summary: Should contain ONLY 'latest_message' key
            ai_service: AIService instance
            
        Returns:
            Extracted requirements as dict
        """
        try:
            # Extract ONLY the latest message - ignore ALL other keys
            latest_message_only = conversation_summary.get('latest_message', '')
            
            if not latest_message_only:
                return {'success': False, 'error': 'No message provided'}
            
            # DEBUG: Log what we're processing
            logger.info(f"🐛 Extracting from message ONLY: {latest_message_only[:100]}")
            
            # Create clean context with ONLY latest message
            clean_context = {'latest_message': latest_message_only}
            prompt = self.extract_requirements_prompt(clean_context)
            
            # Call AI service with STRICT system prompt
            result = await ai_service.generate_response(
                system_prompt="Extract ONLY from the message. Do NOT use conversation history or context. Return ONLY JSON. NO markdown, NO explanations!",
                user_message=prompt,
                max_tokens=200
            )
            
            # DEBUG: Log AI response
            logger.info(f"🐛 AI extraction success: {result.get('success')}")
            logger.info(f"🐛 AI response: {result.get('response', 'NONE')[:200]}")
            
            if result.get('success'):
                response_text = result.get('response', '').strip()
                
                # Extract JSON from response
                # Sometimes AI adds extra text, so we need to extract JSON
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    requirements = json.loads(json_str)
                    return {
                        'success': True,
                        'requirements': requirements,
                        'raw_response': response_text
                    }
                else:
                    return {
                        'success': False,
                        'error': 'JSON topilmadi',
                        'raw_response': response_text
                    }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'AI xatolik')
                }
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {
                'success': False,
                'error': f'JSON parse xatolik: {str(e)}'
            }
        except Exception as e:
            logger.error(f"AI extraction error: {e}")
            return {
                'success': False,
                'error': f'Xatolik: {str(e)}'
            }
    
    def map_requirements_to_crm(self, requirements: Dict) -> Dict:
        """
        Map extracted requirements to CRM field names using field_mapping
        
        Args:
            requirements: Extracted requirements from AI
            
        Returns:
            Mapped requirements for CRM API
        """
        property_fields = self.field_mapping.get('property_fields', {})
        
        if not property_fields:
            # If no mapping, return as is
            return requirements
        
        # Map fields
        mapped = {}
        for ai_field, crm_field in property_fields.items():
            if ai_field in requirements:
                value = requirements[ai_field]
                
                # NEVER use location/search filters - they cause empty results
                if ai_field in ('location', 'district', 'address', 'search'):
                    continue
                
                # Skip null, 0, empty values
                if value in (None, 0, '', 'null'):
                    continue
                
                # Handle nested field mapping (e.g., "price.min" -> nested structure)
                if '.' in crm_field:
                    parts = crm_field.split('.')
                    if parts[0] not in mapped:
                        mapped[parts[0]] = {}
                    mapped[parts[0]][parts[1]] = value
                else:
                    mapped[crm_field] = value
        
        return mapped
    
    async def search_properties(self, requirements: Dict) -> Dict[str, Any]:
        """
        Search properties in CRM using requirements
        
        Args:
            requirements: Extracted and mapped requirements
            
        Returns:
            Search results from CRM
        """
        try:
            # Map requirements to CRM format
            crm_params = self.map_requirements_to_crm(requirements)
            
            # Prepare request based on request_template
            template = self.crm_provider.request_template or {}
            method = template.get('method', 'POST').upper()
            endpoint = template.get('endpoint', '')
            headers = template.get('headers', {})
            
            # Replace placeholders in headers
            # Only add Authorization header if we have a valid JWT token (starts with "eyJ")
            if '{api_key}' in str(headers):
                if self.api_key and self.api_key.startswith('eyJ'):
                    # Valid JWT token
                    headers_str = json.dumps(headers).replace('{api_key}', self.api_key)
                    headers = json.loads(headers_str)
                else:
                    # No token or invalid format - remove Authorization header for public access
                    headers = {k: v for k, v in headers.items() if 'authorization' not in k.lower()}
                    logger.info("ℹ️ No valid JWT token, using public API access")
            
            # Build URL
            url = f"{self.api_url.rstrip('/')}{endpoint}" if endpoint else self.api_url
            
            # 🐛 DEBUG: Log full request details
            logger.info(f"🌐 CRM Request: {method} {url}")
            logger.info(f"📦 CRM Params: {crm_params}")
            logger.info(f"📋 CRM Headers: {headers}")
            
            # Make request
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == 'GET':
                    response = await client.get(url, params=crm_params, headers=headers)
                else:  # POST
                    body_template = template.get('body_template', {})
                    body = self._build_request_body(body_template, crm_params)
                    response = await client.post(url, json=body, headers=headers)
                
                # 🐛 DEBUG: Log response
                logger.info(f"📨 CRM Response Status: {response.status_code}")
                logger.info(f"📄 CRM Response Body (first 500 chars): {response.text[:500]}")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✅ CRM JSON parsed successfully")
                    
                    # Parse response based on response_format
                    properties = self._parse_crm_response(data)
                    logger.info(f"🏠 CRM Properties parsed: {len(properties)} items")
                    
                    if properties:
                        logger.info(f"📋 First property sample: {properties[0]}")
                    
                    return {
                        'success': True,
                        'properties': properties,
                        'count': len(properties),
                        'raw_response': data
                    }
                else:
                    error_body = response.text[:500]
                    logger.error(f"❌ CRM API Error {response.status_code}: {error_body}")
                    return {
                        'success': False,
                        'error': f'CRM API xatolik: {response.status_code}',
                        'details': error_body
                    }
                    
        except httpx.TimeoutException:
            return {'success': False, 'error': 'CRM ulanish vaqti tugadi'}
        except Exception as e:
            logger.error(f"CRM search error: {e}")
            return {'success': False, 'error': f'Xatolik: {str(e)}'}
    
    def _build_request_body(self, template: Dict, params: Dict) -> Dict:
        """Build request body from template"""
        body = template.copy()
        
        # Replace {search_criteria} placeholder
        body_str = json.dumps(body)
        if '{search_criteria}' in body_str:
            body_str = body_str.replace(
                '"{search_criteria}"',
                json.dumps(params)
            )
            body = json.loads(body_str)
        else:
            # If no placeholder, merge params into body
            body.update(params)
        
        return body
    
    def _parse_crm_response(self, data: Dict) -> List[Dict]:
        """Parse CRM response to standardized format"""
        response_format = self.field_mapping.get('response_format', {})
        
        # 🐛 DEBUG: Log raw response structure
        logger.info(f"🔍 CRM Response keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
        
        # Try to find array of properties in response
        properties_data = data
        if isinstance(data, dict):
            # Common keys for property lists
            for key in ['data', 'properties', 'items', 'results', 'list']:
                if key in data and isinstance(data[key], list):
                    logger.info(f"✅ Found property list in '{key}' with {len(data[key])} items")
                    properties_data = data[key]
                    break
        
        if not isinstance(properties_data, list):
            properties_data = [properties_data] if properties_data else []
        
        # Map to standard format
        standardized = []
        for prop in properties_data:
            if not response_format:
                # No mapping, return as is
                standardized.append(prop)
            else:
                # Map fields
                mapped_prop = {}
                for std_field, crm_field in response_format.items():
                    value = self._get_nested_value(prop, crm_field)
                    if value is not None:
                        mapped_prop[std_field] = value
                
                standardized.append(mapped_prop)
        
        return standardized
    
    def _get_nested_value(self, data: Dict, key: str) -> Any:
        """Get value from nested dict using dot notation"""
        if '.' not in key:
            return data.get(key)
        
        keys = key.split('.')
        value = data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None
        return value
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test CRM API connection"""
        try:
            if not self.api_url:
                return {'success': False, 'error': 'API URL kiritilmagan'}
            
            # Simple health check
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.api_url)
                
                if response.status_code < 500:
                    return {
                        'success': True,
                        'message': f'✓ CRM ulanish muvaffaqiyatli (HTTP {response.status_code})',
                        'status_code': response.status_code
                    }
                else:
                    return {
                        'success': False,
                        'error': f'CRM server xatolik: {response.status_code}'
                    }
                    
        except httpx.TimeoutException:
            return {'success': False, 'error': '⏱️ Ulanish vaqti tugadi'}
        except Exception as e:
            return {'success': False, 'error': f'❌ Xatolik: {str(e)}'}
