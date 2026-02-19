from app.models.nansen import NansenResponse, SmartMoneyFlow

class NansenMockClient:
    """Simulador de Nansen para testeos sin coste."""
    
    async def get_smart_money_flows(self, chain: str = "ethereum") -> NansenResponse:
        # Simulamos una entrada masiva en un token ficticio
        mock_data = [
            SmartMoneyFlow(
                chain=chain,
                token_address="0x123...abc",
                token_symbol="GOLD_TOKEN",
                net_flow=500000.0  # $500k inflow (activará señal)
            ),
            SmartMoneyFlow(
                chain=chain,
                token_address="0x456...def",
                token_symbol="DUMP_COIN",
                net_flow=-100000.0 # Salida de dinero
            )
        ]
        return NansenResponse(data=mock_data, total_records=2)