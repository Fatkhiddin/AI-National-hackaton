"""
AI Service - OpenAI, Anthropic (Claude) va boshqa AI providerlar bilan ishlash
"""
import json
import logging
from typing import Dict, List, Optional, Any
import httpx
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class AIService:
    """AI provider bilan muloqot qilish uchun service"""
    
    def __init__(self, provider_type: str, api_key: str, model: str, api_endpoint: Optional[str] = None):
        self.provider_type = provider_type
        self.api_key = api_key
        self.model = model
        self.api_endpoint = api_endpoint
    
    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """
        AI dan javob olish
        
        Args:
            system_prompt: System prompt
            user_message: Foydalanuvchi xabari
            conversation_history: Oldingi xabarlar tarixi [{"role": "user", "content": "..."}, ...]
            max_tokens: Maksimal token soni
            
        Returns:
            {"success": True, "response": "...", "tokens_used": 123}
        """
        try:
            if self.provider_type == 'openai':
                return await self._generate_openai(system_prompt, user_message, conversation_history, max_tokens)
            elif self.provider_type == 'anthropic':
                return await self._generate_anthropic(system_prompt, user_message, conversation_history, max_tokens)
            elif self.provider_type == 'google':
                return await self._generate_google(system_prompt, user_message, conversation_history, max_tokens)
            else:
                return {"success": False, "error": f"Unsupported provider: {self.provider_type}"}
        except Exception as e:
            logger.error(f"AI generation error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def _generate_openai(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict]],
        max_tokens: int
    ) -> Dict[str, Any]:
        """OpenAI API orqali javob olish"""
        try:
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    data=json.dumps({
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": 0.9  # More human-like responses
                    })
                )
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"OpenAI API error: {response.status_code} - {response.text}"
                    }
                
                data = response.json()
                return {
                    "success": True,
                    "response": data["choices"][0]["message"]["content"],
                    "tokens_used": data.get("usage", {}).get("total_tokens", 0),
                    "model": data.get("model")
                }
                
        except Exception as e:
            logger.error(f"OpenAI error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def _generate_anthropic(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict]],
        max_tokens: int
    ) -> Dict[str, Any]:
        """Anthropic (Claude) API orqali javob olish"""
        try:
            messages = []
            
            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "system": system_prompt,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": 0.9
                    }
                )
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Anthropic API error: {response.status_code} - {response.text}"
                    }
                
                data = response.json()
                return {
                    "success": True,
                    "response": data["content"][0]["text"],
                    "tokens_used": data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0),
                    "model": data.get("model")
                }
                
        except Exception as e:
            logger.error(f"Anthropic error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def _generate_google(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict]],
        max_tokens: int
    ) -> Dict[str, Any]:
        """Google Gemini API orqali javob olish"""
        try:
            # Gemini uses different message format
            contents = []
            
            # Add system instruction as first user message
            if system_prompt:
                contents.append({
                    "role": "user",
                    "parts": [{"text": f"System: {system_prompt}"}]
                })
                contents.append({
                    "role": "model",
                    "parts": [{"text": "Understood. I will follow these instructions."}]
                })
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history:
                    role = "user" if msg["role"] == "user" else "model"
                    contents.append({
                        "role": role,
                        "parts": [{"text": msg["content"]}]
                    })
            
            # Add current user message
            contents.append({
                "role": "user",
                "parts": [{"text": user_message}]
            })
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": contents,
                        "generationConfig": {
                            "maxOutputTokens": max_tokens,
                            "temperature": 0.9
                        }
                    }
                )
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Google API error: {response.status_code} - {response.text}"
                    }
                
                data = response.json()
                return {
                    "success": True,
                    "response": data["candidates"][0]["content"]["parts"][0]["text"],
                    "tokens_used": data.get("usageMetadata", {}).get("totalTokenCount", 0),
                    "model": self.model
                }
                
        except Exception as e:
            logger.error(f"Google Gemini error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def generate_summary(
        self,
        conversation_messages: List[Dict[str, str]],
        current_summary: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Suhbat xulosasini yaratish yoki yangilash
        
        Args:
            conversation_messages: Xabarlar ro'yxati [{"role": "user/assistant", "content": "..."}]
            current_summary: Joriy xulosa (agar mavjud bo'lsa)
            
        Returns:
            {"success": True, "summary": {...}}
        """
        try:
            summary_prompt = """Sen ko'chmas mulk agentligi uchun suhbat tahlilchisisiz. Bu mijoz bilan bo'lgan suhbatni tahlil qilib, JSON formatda xulosa ber.

TAHLIL QILISH KERAK:
1. Mijoz kim va nima qilmoqchi?
2. U qaysi bosqichda turubdi? (shunchaki so'rayapti, jiddiy qiziqyapti, yaqinda olmoqchi, kutib turgan, e'tibor yo'q)
3. Uning imkoniyatlari qanday? (puli, vaqti, joy tanlovi)
4. Kayfiyati qanday? (issiq/sovuq/chalkash/xafa)
5. Keyingi qadamlar nima bo'lishi kerak?

JSON STRUKTURA:
{
  "mijoz_tipi": "shunchaki_sorayapti / jiddiy_qiziqyapti / tez_olmoqchi / kutmoqda / etibor_yoq",
  "mijoz_holati": "Qisqa 1-2 gap bilan mijoz haqida xulosa",
  "imkoniyatlari": {
    "byudjet": "noma'lum / past / o'rta / yuqori / juda yuqori",
    "joy_tanlovi": "shahar/hudud nomi yoki noma'lum",
    "vaqt_rejasi": "shoshilmayapti / bir necha oy / tez kerak / noaniq"
  },
  "qiziqishi": ["kvartira", "hovli", "ofis", "noma'lum"],
  "muhim_faktlar": ["masalan: 3 xonali kerak", "1-2 million budget", "Chilonzor tumani"],
  "kayfiyat": "issiq / sovuq / neyтral / chalkash / xafa",
  "keyingi_qadam": "Nima qilish kerak? (masalan: narx yuborish, aloqada qolish, tinch qoldirish)"
}

Oldingi xulosa (agar bor bo'lsa):
""" + (json.dumps(current_summary, ensure_ascii=False) if current_summary else "Yo'q")
            
            # Prepare conversation text
            conversation_text = "\n".join([
                f"{'MIJOZ' if msg['role'] == 'user' else 'AGENT'}: {msg['content']}"
                for msg in conversation_messages[-20:]  # Last 20 messages only
            ])
            
            result = await self.generate_response(
                system_prompt=summary_prompt,
                user_message=f"SUHBAT:\n{conversation_text}\n\nYangilangan JSON xulosani ber (faqat JSON, boshqa gap yo'q):",
                max_tokens=600
            )
            
            if result["success"]:
                try:
                    # Extract JSON from response
                    response_text = result["response"]
                    # Try to parse JSON
                    if "```json" in response_text:
                        json_start = response_text.find("```json") + 7
                        json_end = response_text.find("```", json_start)
                        response_text = response_text[json_start:json_end].strip()
                    elif "```" in response_text:
                        json_start = response_text.find("```") + 3
                        json_end = response_text.find("```", json_start)
                        response_text = response_text[json_start:json_end].strip()
                    
                    summary_data = json.loads(response_text)
                    return {"success": True, "summary": summary_data}
                except json.JSONDecodeError:
                    # Fallback: return as text
                    return {
                        "success": True,
                        "summary": {
                            "last_context": result["response"],
                            "message_count": len(conversation_messages)
                        }
                    }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Summary generation error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
