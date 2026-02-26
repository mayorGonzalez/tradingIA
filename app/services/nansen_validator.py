# app/services/nansen_validator.py
from app.models.nansen import NansenResponse, SmartMoneyFlow
from loguru import logger
from typing import List

class NansenSignalValidator:
    """
    Middleware de Salud de Datos.
    
    Sanitiza y normaliza los datos crudos de Nansen antes de que entren al motor de señales.
    Previene errores por nulos, tipos incorrectos o tokens no deseados.
    """
    STABLECOIN_BLACKLIST = {"USDT", "USDC", "DAI", "BUSD", "TUSD", "FDUSD", "USDE"}

    def validate_flows(self, raw: NansenResponse) -> List[SmartMoneyFlow]:
        """Sanitiza y filtra los flujos antes de entrar al SignalEngine."""
        if not raw or not hasattr(raw, 'data') or raw.data is None:
            logger.warning("[Validator] NansenResponse vacío o inválido.")
            return []

        validated = []
        for flow in raw.data:
            try:
                # 1. Filtro de Estables
                if flow.token_symbol.upper() in self.STABLECOIN_BLACKLIST:
                    continue
                
                # 2. Sanitización de Nulos críticos
                if flow.net_flow_usd is None:
                    # Intentar usar el alias si net_flow_usd falló en Pydantic
                    flow.net_flow_usd = getattr(flow, 'net_flow_24h_usd', 0.0)
                
                if flow.net_flow_usd <= 0:
                    continue
                
                # 3. Reglas de Calidad (Higiene)
                # No operamos tokens con menos de 3 días (muy alto riesgo de rugpull)
                if flow.token_age_days and flow.token_age_days < 7:
                    logger.debug(f"[Validator] Descartando {flow.token_symbol}: Muy joven ({flow.token_age_days}d)")
                    continue
                
                # 4. Asegurar campos mínimos para scoring
                if not flow.token_symbol or not flow.token_address:
                    continue

                validated.append(flow)
            except Exception as e:
                logger.error(f"[Validator] Error procesando token {getattr(flow, 'token_symbol', '???')}: {e}")
                continue

        logger.info(f"[Validator] Sanitización completa: {len(validated)}/{len(raw.data)} tokens válidos.")
        return validated
