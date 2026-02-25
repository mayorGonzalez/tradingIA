"""
AIAnalyst — Asistente de Mercado con GEMINI (v1beta OpenAI Compatible)
====================================================================
Refactorizado para compatibilidad con Google Cloud y estabilidad en Windows.
"""

import asyncio
import httpx
import json
from loguru import logger
from typing import List, Dict, AsyncIterator, TYPE_CHECKING

from app.core.config import settings

# Imports lazy para evitar ciclos y mejorar tiempo de arranque
if TYPE_CHECKING:
    from app.services.nansen_client import NansenClient
    from app.services.portfolio_service import PortfolioService

SYSTEM_PROMPT_TEMPLATE = """Eres TradingAI-Agent, un experto en Finanzas Cuantitativas y Análisis On-Chain. Tu misión es asistir al usuario analizando los datos capturados en tiempo real de Smart Money de Nansen y al historial de trading del bot. Respondes en español, de forma directa, estructurada y con datos concretos.

=== CONTEXTO ACTUAL DEL MERCADO (datos reales) ===

📊 ÚLTIMOS MOVIMIENTOS DE SMART MONEY (Nansen Netflow 24h):
{nansen_context}

💼 POSICIONES ABIERTAS DEL BOT:
{trades_context}

📈 SEÑALES ACTIVAS (última ejecución del motor):
{signals_context}

=== INSTRUCCIONES ===
- Usa los datos anteriores como base de tu análisis.
- Si te preguntan sobre un token específico, busca si aparece en los datos.
- Sé conciso pero completo. Usa emojis para hacer la respuesta más legible.
- NUNCA inventes precios o datos que no estén en el contexto.
- Si un usuario pregunta por un token ausente: 'No tengo datos on-chain suficientes para emitir un juicio institucional'.
- Prioriza siempre la preservación del capital sobre las ganancias rápidas.
"""

class AIAnalyst:
    """Servicio de análisis de mercado powered by GEMINI via Google Cloud."""

    def __init__(self) -> None:
        self.api_key = settings.GEMINI_API_KEY.get_secret_value()
        self.base_url = settings.GEMINI_BASE_URL.rstrip('/')
        # FIX: Google requiere prefijo 'models/' para el endpoint de OpenAI
        model_name = settings.GEMINI_MODEL
        self.model = f"models/{model_name}" if not model_name.startswith("models/") else model_name

    def _build_system_prompt(self, nansen_ctx: str, trades_ctx: str, signals_ctx: str) -> str:
        return SYSTEM_PROMPT_TEMPLATE.format(
            nansen_context=nansen_ctx or "Sin datos disponibles.",
            trades_context=trades_ctx or "No hay posiciones abiertas.",
            signals_context=signals_ctx or "No se han generado señales aún.",
        )

    async def chat(self, user_message: str, history: List[Dict[str, str]], 
                   nansen_ctx: str = "", trades_ctx: str = "", signals_ctx: str = "") -> str:
        
        system_prompt = self._build_system_prompt(nansen_ctx, trades_ctx, signals_ctx)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history[-10:])
        messages.append({"role": "user", "content": user_message})

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": 1024,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                logger.error(f"[AIAnalyst] Error {response.status_code}: {response.text}")
                return f"❌ Error de API ({response.status_code}). Verifica el saldo y el nombre del modelo."
            
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def ask_question(self, prompt: str, history: List[Dict[str, str]] | None = None) -> str:
        """Punto de entrada síncrono para Streamlit con gestión de loop segura."""
        try:
            # FIX para Windows: Gestionar el loop de asyncio correctamente
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            nansen_ctx, trades_ctx = loop.run_until_complete(self._fetch_context())
            return loop.run_until_complete(
                self.chat(prompt, history or [], nansen_ctx, trades_ctx)
            )
        except Exception as e:
            logger.error(f"[AIAnalyst] Error crítico en ask_question: {e}")
            return f"❌ Error interno al procesar la consulta: {str(e)}"

    async def _fetch_context(self) -> tuple[str, str]:
        """Obtiene el contexto real de Nansen y la base de datos."""
        from app.services.nansen_client import NansenClient
        from app.services.nansen_mock import NansenMockClient
        from app.services.portfolio_service import PortfolioService

        nansen = NansenMockClient() if settings.DEBUG_MODE else NansenClient()
        portfolio = PortfolioService()

        try:
            # Ejecución paralela para minimizar latencia
            results = await asyncio.gather(
                nansen.get_smart_money_flows(),
                portfolio.get_open_trades(),
                return_exceptions=True
            )
            
            raw_flows = results[0] if not isinstance(results[0], Exception) else None
            open_trades = results[1] if not isinstance(results[1], Exception) else []

            # Formatear Nansen
            n_lines = []
            if raw_flows and hasattr(raw_flows, 'data'):
                for f in raw_flows.data[:8]:
                    n_lines.append(f"• {f.token_symbol}: Netflow 24h=${f.net_flow_usd:,.0f} | Traders: {f.trader_count}")
            
            # Formatear Trades
            t_lines = [f"• {t.token_symbol}: Entrada ${t.entry_price} | ROI actual: {getattr(t, 'pnl_pct', 0)}%" for t in open_trades]

            return "\n".join(n_lines) or "Sin datos", "\n".join(t_lines) or "Sin posiciones"
        except Exception as e:
            return f"Error de datos: {e}", "Error de datos"