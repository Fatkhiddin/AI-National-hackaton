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
        self.crm_provider = crm_provider
        self.api_url = crm_provider.api_url
        self.api_key = crm_provider.api_key
        self.field_mapping = crm_provider.field_mapping or {}

    def extract_requirements_prompt(self, conversation_summary: Dict) -> str:
        if self.crm_provider.extraction_prompt:
            return self.crm_provider.extraction_prompt

        msg = conversation_summary.get("latest_message", "")

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

    async def extract_requirements_with_ai(self, conversation_summary: Dict, ai_service) -> Dict[str, Any]:
        try:
            latest_message_only = conversation_summary.get("latest_message", "")
            if not latest_message_only:
                return {"success": False, "error": "No message provided"}

            logger.info(f"🐛 Extracting from message ONLY: {latest_message_only[:100]}")
            clean_context = {"latest_message": latest_message_only}
            prompt = self.extract_requirements_prompt(clean_context)

            result = await ai_service.generate_response(
                system_prompt="Extract ONLY from the message. Do NOT use conversation history or context. Return ONLY JSON. NO markdown, NO explanations!",
                user_message=prompt,
                max_tokens=200,
            )

            logger.info(f"🐛 AI extraction success: {result.get('success')}")

            if result.get("success"):
                response_text = result.get("response", "").strip()
                import re

                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    requirements = json.loads(json_str)
                    return {"success": True, "requirements": requirements, "raw_response": response_text}
                else:
                    return {"success": False, "error": "JSON topilmadi", "raw_response": response_text}
            else:
                return {"success": False, "error": result.get("error", "AI xatolik")}

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {"success": False, "error": f"JSON parse xatolik: {str(e)}"}
        except Exception as e:
            logger.error(f"AI extraction error: {e}")
            return {"success": False, "error": f"Xatolik: {str(e)}"}

    def map_requirements_to_crm(self, requirements: Dict) -> Dict:
        property_fields = self.field_mapping.get("property_fields", {})
        if not property_fields:
            return requirements

        mapped = {}
        for ai_field, crm_field in property_fields.items():
            if ai_field in requirements:
                value = requirements[ai_field]
                if ai_field in ("location", "district", "address", "search"):
                    continue
                if value in (None, 0, "", "null"):
                    continue
                if "." in crm_field:
                    parts = crm_field.split(".")
                    if parts[0] not in mapped:
                        mapped[parts[0]] = {}
                    mapped[parts[0]][parts[1]] = value
                else:
                    mapped[crm_field] = value
        return mapped

    async def search_properties(self, requirements: Dict) -> Dict[str, Any]:
        try:
            crm_params = self.map_requirements_to_crm(requirements)

            template = self.crm_provider.request_template or {}
            method = template.get("method", "POST").upper()
            endpoint = template.get("endpoint", "")
            headers = template.get("headers", {})

            if "{api_key}" in str(headers):
                if self.api_key and self.api_key.startswith("eyJ"):
                    headers_str = json.dumps(headers).replace("{api_key}", self.api_key)
                    headers = json.loads(headers_str)
                else:
                    headers = {k: v for k, v in headers.items() if "authorization" not in k.lower()}
                    logger.info("ℹ️ No valid JWT token, using public API access")

            url = f"{self.api_url.rstrip('/')}{endpoint}" if endpoint else self.api_url

            logger.info(f"🌐 CRM Request: {method} {url}")
            logger.info(f"📦 CRM Params: {crm_params}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    response = await client.get(url, params=crm_params, headers=headers)
                else:
                    body_template = template.get("body_template", {})
                    body = self._build_request_body(body_template, crm_params)
                    response = await client.post(url, json=body, headers=headers)

                logger.info(f"📨 CRM Response Status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    properties = self._parse_crm_response(data)
                    logger.info(f"🏠 CRM Properties parsed: {len(properties)} items")
                    return {
                        "success": True,
                        "properties": properties,
                        "count": len(properties),
                        "raw_response": data,
                    }
                else:
                    error_body = response.text[:500]
                    logger.error(f"❌ CRM API Error {response.status_code}: {error_body}")
                    return {
                        "success": False,
                        "error": f"CRM API xatolik: {response.status_code}",
                        "details": error_body,
                    }

        except httpx.TimeoutException:
            return {"success": False, "error": "CRM ulanish vaqti tugadi"}
        except Exception as e:
            logger.error(f"CRM search error: {e}")
            return {"success": False, "error": f"Xatolik: {str(e)}"}

    def _build_request_body(self, template: Dict, params: Dict) -> Dict:
        body = template.copy()
        body_str = json.dumps(body)
        if "{search_criteria}" in body_str:
            body_str = body_str.replace('"{search_criteria}"', json.dumps(params))
            body = json.loads(body_str)
        else:
            body.update(params)
        return body

    def _parse_crm_response(self, data: Dict) -> List[Dict]:
        response_format = self.field_mapping.get("response_format", {})
        properties_data = data
        if isinstance(data, dict):
            for key in ["data", "properties", "items", "results", "list"]:
                if key in data and isinstance(data[key], list):
                    properties_data = data[key]
                    break

        if not isinstance(properties_data, list):
            properties_data = [properties_data] if properties_data else []

        standardized = []
        for prop in properties_data:
            if not response_format:
                standardized.append(prop)
            else:
                mapped_prop = {}
                for std_field, crm_field in response_format.items():
                    value = self._get_nested_value(prop, crm_field)
                    if value is not None:
                        mapped_prop[std_field] = value
                standardized.append(mapped_prop)
        return standardized

    def _get_nested_value(self, data: Dict, key: str) -> Any:
        if "." not in key:
            return data.get(key)
        keys = key.split(".")
        value = data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None
        return value

    async def test_connection(self) -> Dict[str, Any]:
        try:
            if not self.api_url:
                return {"success": False, "error": "API URL kiritilmagan"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.api_url)
                if response.status_code < 500:
                    return {
                        "success": True,
                        "message": f"✓ CRM ulanish muvaffaqiyatli (HTTP {response.status_code})",
                        "status_code": response.status_code,
                    }
                else:
                    return {"success": False, "error": f"CRM server xatolik: {response.status_code}"}
        except httpx.TimeoutException:
            return {"success": False, "error": "⏱️ Ulanish vaqti tugadi"}
        except Exception as e:
            return {"success": False, "error": f"❌ Xatolik: {str(e)}"}
