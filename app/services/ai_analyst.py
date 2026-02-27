"""
AIAnalyst — Asistente de Mercado con soporte Ollama y Gemini
================================================================
Refactorizado para compatibilidad múltiple de proveedores LLM.
"""

import asyncio
import json
from loguru import logger
from typing import List, Dict, TYPE_CHECKING

from app.core.config import settings
from app.services.llm_provider import OllamaProvider, GeminiProvider

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
    """Servicio de análisis de mercado con soporte múltiple de LLM."""

    def __init__(self) -> None:
        provider_type = settings.LLM_PROVIDER
        
        if provider_type == "local":
            self.provider = OllamaProvider(
                settings.LLM_BASE_URL,
                settings.LLM_MODEL
            )
            logger.info(f"✓ LLM Local: {settings.LLM_MODEL} en {settings.LLM_BASE_URL}")
        elif provider_type == "gemini":
            self.provider = GeminiProvider(
                settings.GEMINI_API_KEY,
                settings.GEMINI_BASE_URL,
                settings.GEMINI_MODEL
            )
            logger.info(f"✓ Gemini: {settings.GEMINI_MODEL}")
        else:
            raise ValueError(f"LLM_PROVIDER desconocido: {provider_type}. Usa 'local' o 'gemini'")

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

        return await self.provider.chat(user_message, messages)

    def ask_question(self, prompt: str, history: List[Dict[str, str]] | None = None) -> str:
        """Punto de entrada síncrono para Streamlit con gestión de loop segura."""
        try:
            try:
                loop = asyncio.get_running_loop()
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
            results = await asyncio.gather(
                nansen.get_smart_money_flows(),
                portfolio.get_open_trades(),
                return_exceptions=True
            )
            
            raw_flows = results[0] if not isinstance(results[0], Exception) else None
            open_trades = results[1] if not isinstance(results[1], Exception) else []

            n_lines = []
            if raw_flows and hasattr(raw_flows, 'data'):
                for f in raw_flows.data[:8]:
                    n_lines.append(f"• {f.token_symbol}: Netflow 24h=${f.net_flow_usd:,.0f} | Traders: {f.trader_count}")
            
            t_lines = [f"• {t.token_symbol}: Entrada ${t.entry_price} | ROI actual: {getattr(t, 'pnl_pct', 0)}%" for t in open_trades]

            return "\n".join(n_lines) or "Sin datos", "\n".join(t_lines) or "Sin posiciones"
        except Exception as e:
            logger.error(f"Error fetching context: {e}")
            return f"Error de datos: {e}", "Error de datos"