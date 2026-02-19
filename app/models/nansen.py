from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SmartMoneyFlow(BaseModel):
    """Modelo para un movimiento de smart money en Nansen"""
    
    chain: str
    token_address: str
    token_symbol: str
    net_flow_usd: float = Field(..., alias="net_flow")
    amount: Optional[float] = None
    tx_hash: Optional[str] = None
    timestamp: Optional[datetime] = None

class NansenResponse(BaseModel):
    """Modelo para la respuesta de Nansen"""
    
    data: List[SmartMoneyFlow]
    total_records: int
    

    
    