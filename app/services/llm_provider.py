"""
LLM Provider Abstraction — Soporte para múltiples backends (Ollama, Gemini)
"""

import httpx
from abc import ABC, abstractmethod
from typing import List, Dict
from loguru import logger
from pydantic import SecretStr


class LLMProvider(ABC):
    """Interfaz base para proveedores de LLM."""
    
    @abstractmethod
    async def chat(self, user_message: str, messages: List[Dict[str, str]]) -> str:
        pass


class OllamaProvider(LLMProvider):
    """Proveedor Ollama para LLM local (Qwen, Llama, etc)."""
    
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip('/')
        self.model = model
    
    async def chat(self, user_message: str, messages: List[Dict[str, str]]) -> str:
        """Llamada a Ollama local sin autenticación."""
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages + [{"role": "user", "content": user_message}],
            "stream": False,
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    logger.error(f"Ollama error ({response.status_code}): {response.text}")
                    return "❌ Error conectando con LLM local. ¿Ollama está corriendo?"
                
                return response.json()["message"]["content"]
        except httpx.ConnectError:
            logger.error("No se puede conectar a Ollama en localhost:11434")
            return "❌ Error: No se puede conectar a Ollama. Ejecuta: ollama serve"
        except Exception as e:
            logger.error(f"Ollama error inesperado: {e}")
            return f"❌ Error en LLM local: {str(e)}"


class GeminiProvider(LLMProvider):
    """Proveedor Google Gemini (requiere API key)."""
    
    def __init__(self, api_key: SecretStr, base_url: str, model: str):
        self.api_key = api_key.get_secret_value()
        self.base_url = base_url.rstrip('/')
        model_name = model
        self.model = f"models/{model_name}" if not model_name.startswith("models/") else model_name
    
    async def chat(self, user_message: str, messages: List[Dict[str, str]]) -> str:
        """Llamada a Google Gemini API."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages + [{"role": "user", "content": user_message}],
            "temperature": 0.4,
            "max_tokens": 1024,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code != 200:
                    logger.error(f"Gemini error ({response.status_code}): {response.text}")
                    return f"❌ Error de API Gemini ({response.status_code}). Verifica key y cuota."
                
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return f"❌ Error en Gemini: {str(e)}"