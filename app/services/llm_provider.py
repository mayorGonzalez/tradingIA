"""
LLM Provider Abstraction — Soporte para múltiples backends (Ollama, Gemini)
"""

import httpx
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from loguru import logger
from pydantic import SecretStr

class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, user_message: str, history: List[Dict[str, str]], image_data: Optional[bytes] = None) -> str:
        """
        Ahora soporta image_data para que Gemini 1.5 Pro pueda 'ver' 
        los gráficos de Nansen y velas.
        """
        pass

class GeminiProvider(LLMProvider):
    """
    Proveedor optimizado para Gemini 1.5 Pro (Paid Tier).
    Configurado para análisis de alta capacidad y visión.
    """
    def __init__(self, api_key: SecretStr, model: str = "gemini-1.5-pro"):
        self.api_key = api_key.get_secret_value()
        # Usamos la API nativa de Google para mayor estabilidad en Paid Tier
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"

    async def chat(self, user_message: str, history: List[Dict[str, str]], image_data: Optional[bytes] = None) -> str:
        # Convertir historial al formato de Google
        contents = []
        for msg in history:
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        # Añadir mensaje actual y posible imagen (Nansen/Gráficos)
        current_parts = [{"text": user_message}]
        if image_data:
            import base64
            current_parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": base64.b64encode(image_data).decode("utf-8")
                }
            })
        
        contents.append({"role": "user", "parts": current_parts})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2, # Más bajo = Más objetivo (Directiva Vicente)
                "maxOutputTokens": 2048,
                "topP": 0.8,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(self.url, json=payload)
                if response.status_code != 200:
                    logger.error(f"Error Gemini {response.status_code}: {response.text}")
                    return "❌ Error en análisis de Gemini 1.5 Pro."
                
                result = response.json()
                return result["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.error(f"Fallo crítico conexión LLM: {e}")
            return f"❌ Error de conexión: {str(e)}"

class OllamaProvider(LLMProvider):
    """Fallback local para análisis rápidos de texto."""
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip('/')
        self.model = model

    async def chat(self, user_message: str, history: List[Dict[str, str]], image_data: Optional[bytes] = None) -> str:
        if image_data:
            logger.warning("[Ollama] El modelo local actual no soporta visión de la misma forma que Gemini 1.5 Pro.")
        
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": history + [{"role": "user", "content": user_message}],
            "stream": False,
            "options": {"temperature": 0.2}
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload)
                return response.json()["message"]["content"]
        except Exception as e:
            return f"❌ Error Ollama: {str(e)}"