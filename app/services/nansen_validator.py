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
    STABLECOIN_BLACKLIST = {"USDT", "USDC", "DAI", "BUSD", "TUSD", "FDUSD", "USDE", 
        "WETH", "WBNB", "WBTC", "WSOL", "WAVAX"}

    def validate_flows(self, raw: NansenResponse) -> List[SmartMoneyFlow]:
        """Sanitiza y filtra los flujos antes de entrar al SignalEngine."""
        if not raw or not hasattr(raw, 'data') or raw.data is None:
            logger.warning("[Validator] NansenResponse vacío o inválido.")
            return []

        validated = []
        for flow in raw.data:
            try:
                symbol = flow.token_symbol.upper() if flow.token_symbol else "???"
                # 1. Filtro de Estables
                if symbol in self.STABLECOIN_BLACKLIST:
                    continue
                
               # 2. Sanitización de PnL y Netflow
                # Si no hay dato de USD, usamos el alias de 24h
                net_usd = flow.net_flow_usd if flow.net_flow_usd is not None else getattr(flow, 'net_flow_24h_usd', 0.0)
                
                # Solo nos interesan INFLOWS (compras de Smart Money)
                if net_usd <= 0:
                    continue
                
               # 3. Lógica de 'Caza de Lanzamientos' (Ajustada)
                # En lanzamientos, 1-3 días es aceptable SI el Smart Money es alto.
                token_age = flow.token_age_days if flow.token_age_days is not None else 999
                if token_age < 1:
                    logger.debug(f"[Validator] {symbol} descartado: Recién nacido (<24h).")
                    continue
                
                # 4. Filtro de Concentración (Mínimo de carteras SM)
                # Si el flujo viene de una sola wallet, es ruido o manipulación.
                sm_wallets = getattr(flow, 'smart_money_wallet_count', 0)
                if sm_wallets < 3: 
                    # Exigimos al menos 3 entidades Smart Money distintas
                    continue

                # 5. Formateo de Log según directiva Vicente (Miles/Millones)
                flow_display = f"{int(net_usd / 1000)}K" if net_usd < 1000000 else f"{int(net_usd / 1000000)}M"
                
                # 6. Verificación de Campos Críticos
                if not flow.token_address:
                    continue

                validated.append(flow)
                logger.debug(f"[Validator] ✅ {symbol} validado. Flow: ${flow_display} | Edad: {token_age}d")

            except Exception as e:
                
                logger.error(f"[Validator] Error procesando token {getattr(flow, 'token_symbol', '???')}: {e}")
                continue

        logger.info(f"[Validator] Sanitización completa: {len(validated)}/{len(raw.data)} tokens válidos.")
        return validated
