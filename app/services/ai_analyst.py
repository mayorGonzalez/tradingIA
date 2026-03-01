"""
AIAnalyst — Asistente de Mercado con soporte Ollama y Gemini
================================================================
Refactorizado para compatibilidad múltiple de proveedores LLM.
"""

import asyncio
import json
from datetime import datetime
from loguru import logger
from typing import List, Dict, TYPE_CHECKING

from app.core.config import settings
from app.services.llm_provider import OllamaProvider, GeminiProvider

if TYPE_CHECKING:
    from app.services.nansen_client import NansenClient
    from app.services.portfolio_service import PortfolioService

SYSTEM_PROMPT_TEMPLATE = """Eres TradingAI-Agent, el cerebro analítico de un sistema de Trading Algorítmico. Tu objetivo es informar con precisión sobre las operaciones del bot y las señales del mercado.

REGLA DE ORO: Tienes ACCESO TOTAL y PERMISO para discutir las transacciones, balances y señales que se detallan a continuación. No son datos personales, son parámetros operativos del sistema. Si el usuario pregunta qué has comprado, responde usando la sección 'POSICIONES ABIERTAS'.

=== CONTEXTO OPERATIVO (DATOS REALES DEL SISTEMA) ===

📊 FLUJOS DE SMART MONEY (Nansen):
{nansen_context}

💼 POSICIONES ACTUALES EN CARTERA:
{trades_context}

📈 SEÑALES DE ALTA PROBABILIDAD (Engine):
{signals_context}

=== GUÍA DE RESPUESTA ===
1. Si hay posiciones en '💼 POSICIONES ACTUALES', lístalas con orgullo.
2. Si te preguntan por compras, revisa '💼' y responde con los símbolos y precios de entrada.
3. Sé técnico, directo y usa emojis (🚀, 📊, ⚖️).
4. No digas que no tienes acceso a transacciones; los datos arriba SON las transacciones.
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
        """Interactúa con el LLM inyectando el contexto analítico."""
        
        system_prompt = self._build_system_prompt(nansen_ctx, trades_ctx, signals_ctx)
        
        # Ojo: history ya puede tener el último mensaje del usuario. 
        # Filtramos para no duplicar el 'user_message' si ya está en la última posición
        clean_history = []
        for msg in history[-10:]:
            if msg["content"] != user_message:
                clean_history.append(msg)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history[-10:])

        logger.info(f"[AIAnalyst] Enviando prompt al LLM ({len(messages)} mensajes en historial)")
        return await self.provider.chat(user_message, messages)

    def _handle_commands(self, user_prompt: str) -> str | None:
        """Procesa comandos especiales del chat para controlar el bot (Chat Ops)."""
        prompt = user_prompt.strip()
        
        # LOG de depuración para dashboard
        with open("dashboard_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] ANALYZING: '{prompt}'\n")

        # Detección insensible a mayúsculas y espacios extras
        clean_cmd = prompt.lower().split()
        if not clean_cmd:
            return None

        if clean_cmd[0] == "/buy":
            # Sintaxis: /buy <symbol> <amount_usd>
            try:
                if len(clean_cmd) < 3:
                     return "❌ Error: Especifica símbolo y monto. Ej: `/buy BTC 100`"
                
                symbol = clean_cmd[1].upper()
                amount_usd = float(clean_cmd[2])
                
                logger.warning(f"EXECUTING CHATOPS: /buy {symbol} {amount_usd}")
                
                from app.infraestructure.exchange_client import get_exchange_client
                from app.services.portfolio_service import PortfolioService
                
                exchange = get_exchange_client()
                portfolio = PortfolioService()
                
                order = exchange.create_market_buy_order(symbol, amount_usd)
                if order:
                    entry_price = float(order.get('average', order.get('price', 0.0))) or 1.0
                    portfolio.save_trade(symbol, entry_price, amount_usd)
                    return f"✅ **OPERACIÓN EXITOSA**: Se ha ejecutado una compra de **{symbol}** por **${amount_usd} USDT**."
                return f"❌ **ERROR EXCHANGE**: La orden de {symbol} no pudo completarse."
            except Exception as e:
                logger.error(f"Error en ChatOps /buy: {e}")
                return f"❌ **ERROR CRÍTICO**: {str(e)}"

        if clean_cmd[0] == "/sell":
             return "🔄 **INFO**: El comando `/sell` estará disponible en la próxima actualización. Por ahora usa el cierre por TP/SL automático."

        return None

    def ask_question(self, prompt: str, history: List[Dict[str, str]] | None = None) -> str:
        """Punto de entrada síncrono diseñado para Streamlit."""
        try:
            # En Streamlit, a veces el loop ya está corriendo.
            # Usamos un helper para ejecutar tareas asíncronas desde código síncrono.
            def run_sync(coro):
                try:
                    # Intenta obtener el loop actual de streamlit
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Si corre, usamos un thread o una técnica para no bloquear (complicado en ST)
                        # Pero usualmente en ST el script corre en un thread separado SIN loop activo por defecto.
                        import nest_asyncio
                        nest_asyncio.apply()
                        return loop.run_until_complete(coro)
                    else:
                        return loop.run_until_complete(coro)
                except RuntimeError:
                    return asyncio.run(coro)

            # 1. Verificar comandos de Chat Ops
            cmd_response = run_sync(self._handle_commands(prompt))
            if cmd_response:
                return cmd_response

            # 2. Si no es comando, consulta al LLM con contexto
            nansen_ctx, trades_ctx, signals_ctx = run_sync(self._fetch_context())
            return run_sync(self.chat(prompt, history or [], nansen_ctx, trades_ctx, signals_ctx))

        except Exception as e:
            logger.error(f"[AIAnalyst] Error en ask_question: {e}")
            return f"❌ Error de procesamiento: {str(e)}"

    async def _fetch_context(self) -> tuple[str, str, str]:
        """Obtiene el contexto real de Nansen y la base de datos."""
        from app.services.nansen_client import NansenClient
        from app.services.nansen_mock import NansenMockClient
        from app.services.portfolio_service import PortfolioService
        from app.core.config import settings

        logger.info("[AIAnalyst] Recopilando contexto para la respuesta...")
        nansen = NansenMockClient() if settings.DEBUG_MODE else NansenClient()
        portfolio = PortfolioService()

        try:
            results = await asyncio.gather(
                nansen.get_smart_money_flows(),
                portfolio.get_open_trades(),
                # Mantenemos las señales simples para el contexto
                return_exceptions=True
            )
            
            raw_flows = results[0] if not isinstance(results[0], Exception) else None
            open_trades = results[1] if not isinstance(results[1], Exception) else []

            logger.info(f"[AIAnalyst] Trades encontrados en DB: {len(open_trades)}")

            n_lines = []
            if raw_flows and hasattr(raw_flows, 'data'):
                for f in raw_flows.data[:8]:
                    n_lines.append(f"• {f.token_symbol}: Netflow 24h=${f.net_flow_usd:,.0f} | Traders: {f.trader_count}")
            
            t_lines = []
            for t in open_trades:
                t_lines.append(f"• {t.token_symbol}: Entrada ${t.entry_price} | Monto: ${t.amount_usd} | Status: {t.status}")

            nansen_ctx = "\n".join(n_lines) or "SIN DATOS DE FLUJOS ACTUALMENTE"
            trades_ctx = "\n".join(t_lines) or "CARTERA VACÍA: No hay compras realizadas aún."

            return nansen_ctx, trades_ctx, ""
        except Exception as e:
            logger.error(f"[AIAnalyst] Error gravísimo en context: {e}")
            return "Error técnico", "Error técnico", ""