from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

'''Este archivo es el "Traductor" o "Adaptador" de tu sistema.

Imagina que tu cerebro (Core) habla español y el mercado (Exchange) habla chino.
Este archivo se encarga de traducir las órdenes de "Compra" a los comandos exactos
que Binance o MEXC entienden, y también de traducir las respuestas del mercado
a información que tu cerebro pueda procesar (como el balance o los precios).

Además, aquí está la lógica de "Seguridad": si el mercado está cerrado (noche),
este módulo se asegura de que el bot no intente comprar y se duerma tranquilamente
(modo DEBUG) o espere (modo PROD).'''

class SmartMoneyFlow(BaseModel):
    """Flujo de entrada/salida de Smart Money (netflow endpoint)"""
    model_config = ConfigDict(populate_by_name=True)
    chain: str
    token_address: str
    token_symbol: str
    # La API devuelve los flujos en múltiples marcos temporales
    net_flow_usd: float = Field(..., alias="net_flow_24h_usd")
    net_flow_1h_usd: float = 0.0
    net_flow_7d_usd: float = 0.0
    net_flow_30d_usd: float = 0.0
    trader_count: int = 0
    token_age_days: Optional[int] = None
    market_cap_usd: Optional[float] = None
    token_sectors: List[str] = Field(default_factory=list)
    # Campo enriquecido por el cliente (etiquetas tipo "Funds", "Whale")
    labels: List[str] = Field(default_factory=list)


class SmartMoneyHolding(BaseModel):
    """Token que Smart Money está acumulando (holdings endpoint)"""
    chain: str
    token_address: str
    token_symbol: str
    value_usd: float
    holders_count: int = 0
    balance_24h_percent_change: float = 0.0
    share_of_holdings_percent: float = 0.0
    token_age_days: Optional[int] = None
    market_cap_usd: Optional[float] = None
    token_sectors: List[str] = Field(default_factory=list)


class DexTrade(BaseModel):
    """Operación en DEX realizada por una wallet de Smart Money"""
    chain: str
    block_timestamp: datetime
    transaction_hash: str
    trader_address: str
    trader_address_label: Optional[str] = None
    token_bought_symbol: str
    token_sold_symbol: str
    token_bought_address: str
    token_sold_address: str
    trade_value_usd: float
    token_bought_age_days: Optional[int] = None
    token_bought_market_cap: Optional[float] = None


class SignalResult(BaseModel):
    """Resultado del motor de señales con scoring multidimensional"""
    token_symbol: str
    score: float
    net_flow_usd: float
    # Datos de enriquecimiento multifuente
    holders_count: int = 0
    dex_buy_count: int = 0
    trend_confirmed_7d: bool = False
    price_change_1h: Optional[float] = None
    risk_factors: List[str] = Field(default_factory=list)
    is_valid: bool = False


class NansenPaginatedResponse(BaseModel):
    """Respuesta paginada genérica de Nansen"""
    data: List[Any]
    pagination: Optional[Dict[str, Any]] = None


class NansenResponse(BaseModel):
    """Modelo para la respuesta principal del endpoint netflow"""
    data: List[SmartMoneyFlow]
    total_records: Optional[int] = None
    pagination: Optional[Dict[str, Any]] = None

    
    