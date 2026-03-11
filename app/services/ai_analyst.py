import asyncio
import json
from datetime import datetime
from loguru import logger
from typing import List, Dict, TYPE_CHECKING
from dataclasses import dataclass
from app.core.config import settings
from app.services.llm_provider import OllamaProvider, GeminiProvider

if TYPE_CHECKING:
    from app.services.nansen_client import NansenClient
    from app.services.portfolio_service import PortfolioService

'''Este archivo es el "Cerebro" o el "Asistente de Dirección" de tu bot.

Imagina que tu bot es un piloto de avión. Este archivo es el copiloto inteligente.
No controla los motores (eso lo hace el ExchangeClient), pero toma las decisiones críticas:
- ¿Entramos en esta moneda? (Señales)
- ¿Cuánto invertimos? (Cartera)
- ¿Qué está pasando en el mercado? (Nansen)
- ¿Cómo respondemos al usuario? (Chat)

Es el componente que "piensa" y se comunica contigo.'''

SYSTEM_PROMPT_TEMPLATE = """Eres TradingAI-Agent, el cerebro analítico de un sistema de Trading 
Algorítmico. Tu objetivo es informar con precisión sobre las operaciones del bot y las señales 
del mercado.

REGLA DE ORO: Tienes ACCESO TOTAL y PERMISO para discutir las transacciones, balances y señales 
que se detallan a continuación. No son datos personales, son parámetros operativos del sistema.

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
3. Sé técnico, directo y usa un lenguaje sencillo de entender.
4. No digas que no tienes acceso a transacciones; los datos arriba SON las transacciones.
"""

@dataclass
class AIVerdict:
    """
    FIX: Clase que faltaba. main.py llama a ai_analyst.analyze_opportunity(signal)
    y espera .is_bullish, .reason y .summary. Sin esto → AttributeError en producción.
    """
    is_bullish: bool
    reason: str
    summary: str

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
        
        # FIX: No filtrar historia, simplemente tomar los últimos 10 mensajes
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history[-10:] if history else [])

        logger.info(f"[AIAnalyst] Enviando prompt al LLM ({len(messages)} mensajes en historial)")
        return await self.provider.chat(user_message, messages)

    def _handle_commands(self, user_prompt: str) -> str | None:
        """FIX: Hacer función SÍNCRONA (no async) para procesar comandos especiales del chat."""
        prompt = user_prompt.strip()
        
        # LOG de depuración para dashboard
        if settings.DEBUG_MODE:
            try:
                with open("dashboard_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] ANALYZING: '{prompt}'\n")
            except Exception as e:
                logger.error(f"Error escribiendo debug log: {e}")

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
                
                # TODO: Integrar con exchange cuando esté implementado
                return f"✅ **OPERACIÓN SIMULADA**: Compra de **{symbol}** por **${amount_usd} USDT** registrada (modo DEBUG)."
            except Exception as e:
                logger.error(f"Error en ChatOps /buy: {e}")
                return f"❌ **ERROR CRÍTICO**: {str(e)}"

        if clean_cmd[0] == "/sell":
            return "🔄 **INFO**: El comando `/sell` estará disponible en la próxima actualización. Por ahora usa el cierre por TP/SL automático."

        return None

    def ask_question(self, prompt: str, history: List[Dict[str, str]] | None = None) -> str:
        """Punto de entrada síncrono diseñado para Streamlit."""
        try:
            # En Streamlit, a veces el loop ya está corriendo
            def run_sync(coro):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Si el loop corre, usar nest_asyncio
                        import nest_asyncio
                        nest_asyncio.apply()
                        return loop.run_until_complete(coro)
                    else:
                        return loop.run_until_complete(coro)
                except RuntimeError:
                    return asyncio.run(coro)

            # 1. FIX: Verificar comandos de Chat Ops (ya no es async)
            cmd_response = self._handle_commands(prompt)
            if cmd_response:
                return cmd_response

            # 2. Si no es comando, consulta al LLM con contexto
            # FIX: Ahora _fetch_context devuelve 3 valores
            nansen_ctx, trades_ctx, signals_ctx = run_sync(self._fetch_context())
            return run_sync(self.chat(prompt, history or [], nansen_ctx, trades_ctx, signals_ctx))

        except Exception as e:
            logger.error(f"[AIAnalyst] Error en ask_question: {e}")
            return f"❌ Error de procesamiento: {str(e)}"

    async def _fetch_context(self) -> tuple[str, str, str]:
        """Recopila datos de Nansen y Portfolio para el prompt."""
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
                return_exceptions=True
            )
            
            raw_flows = results[0] if not isinstance(results[0], Exception) else None
            open_trades = results[1] if not isinstance(results[1], Exception) else []

            logger.info(f"[AIAnalyst] Trades encontrados en DB: {len(open_trades)}")

            def format_currency(value: float) -> str:
                """Ajuste al estilo Vicente: Millones o Miles sin decimales."""
                if value >= 1_000_000:
                    return f"{value / 1_000_000:.1f}M"
                if value >= 1_000:
                    return f"{value / 1_000:.0f}K"
                return f"{value:.0f}"

            n_lines = []
            if raw_flows and hasattr(raw_flows, 'data'):
                for f in raw_flows.data[:8]:
                    n_lines.append(f"• {f.token_symbol}: Netflow 24h=${format_currency(f.net_flow_usd)} | Traders: {f.trader_count}")
            
            t_lines = []
            for t in open_trades:
                t_lines.append(f"• {t.token_symbol}: Entrada ${t.entry_price} | Monto: ${t.amount_usd} | Status: {t.status}")

            nansen_ctx = "\n".join(n_lines) or "SIN DATOS DE FLUJOS ACTUALMENTE"
            trades_ctx = "\n".join(t_lines) or "CARTERA VACÍA: No hay compras realizadas aún."
            signals_ctx = "Sistema de señales en desarrollo"

            return nansen_ctx, trades_ctx, signals_ctx
        except Exception as e:
            logger.error(f"[AIAnalyst] Error en _fetch_context: {e}")
            return "Error técnico", "Error técnico", "Error técnico"

    async def analyze_opportunity(self, signal: "SignalResult") -> AIVerdict:
        """Analiza una oportunidad de trading con el LLM."""
        if settings.DEBUG_MODE or settings.PAPER_TRADING:
            logger.debug(f"[AIAnalyst] DEBUG: aprobando automáticamente {signal.token_symbol}")
            return AIVerdict(
                is_bullish=True,
                reason="Modo DEBUG/PAPER: análisis IA omitido",
                summary=f"Score={signal.score:.0f} | Flujo=${signal.net_flow_usd:,.0f}"
            )

        prompt = (
            f"Analiza esta oportunidad y responde SOLO con JSON:\n"
            f"Token: {signal.token_symbol}\nScore: {signal.score:.1f}/100\n"
            f"Netflow 24h: ${signal.net_flow_usd:,.0f}\nTraders: {signal.trader_count}\n"
            f"Riesgos: {', '.join(signal.risk_factors) or 'ninguno'}\n"
            f"Cambio 1h: {signal.price_change_1h or 0:.1f}%\n"
            f'{{"is_bullish": true/false, "reason": "...", "summary": "..."}}'
        )

        try:
            response = await self.provider.chat(prompt, [])
            import json
            data = json.loads(response.strip().strip("```json").strip("```").strip())
            return AIVerdict(
                is_bullish=bool(data.get("is_bullish", False)),
                reason=str(data.get("reason", "Sin razón")),
                summary=str(data.get("summary", ""))
            )
        except Exception as e:
            logger.warning(f"[AIAnalyst] Error parseando veredicto para {signal.token_symbol}: {e}")
            return AIVerdict(is_bullish=False, reason=f"Error LLM: {e}", summary="")