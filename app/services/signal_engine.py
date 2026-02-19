import pandas as pd
from typing import List
from app.models.nansen import SmartMoneyFlow
from loguru import logger

class SignalEngine:
    def __init__(self, min_inflow_usd: float = 50000.0):
        self.min_inflow_usd = min_inflow_usd

    def analyze_flows(self, flows: List[SmartMoneyFlow]) -> List[SmartMoneyFlow]:
        """
        Analiza flujos netos buscando anomalías de acumulación.
        """
        if not flows:
            logger.warning("No se recibieron flujos para analizar.")
            return []

        # Convertimos a DataFrame para manipulación avanzada
        df = pd.DataFrame([f.model_dump() for f in flows])

        # 1. Filtro de volumen mínimo (evitar ruido)
        signals_df = df[df['net_flow_usd'] >= self.min_inflow_usd]

        # 2. Ordenar por mayor entrada de Smart Money
        signals_df = signals_df.sort_values(by='net_flow_usd', ascending=False)

        logger.info(f"Análisis completado. {len(signals_df)} señales detectadas.")
        
        # Convertimos de vuelta a objetos de dominio
        return [SmartMoneyFlow(**row) for _, row in signals_df.iterrows()]