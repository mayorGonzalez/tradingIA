# 📋 GUÍA: Usar NansenMockClient Mejorado para Testing en Dashboard

**Fecha:** Marzo 2, 2025  
**Versión:** 2.0 - Mejorada para DEBUG_MODE  
**Propósito:** Facilitar testing del dashboard con datos realistas sin depender de API real

---

## 🎯 RESUMEN DE CAMBIOS

### ¿Qué cambió?

**ANTES:**
```python
class NansenMockClient:
    async def get_smart_money_flows(self):
        # Datos muy genéricos, sin patrones realistas
        # No diferenciaban entre bullish/bearish
        # Difícil debuggear
```

**AHORA:**
```python
class NansenMockClient:
    async def get_smart_money_flows(self):
        # 8 tokens con patrones diferenciados:
        # ✅ BTC: Bullish (+ $5.2M)
        # ✅ ETH: Accumulation (+ $3.1M)
        # ⚠️  SOL: Distribution (- $2.1M)
        # ❌ XRP: Bearish (- $4.3M)
        # ... más patrones
```

---

## 📦 INSTALACIÓN

### 1. Reemplazar archivo
```bash
# Copiar el archivo mejorado al repositorio
cp nansen_mock_improved.py \
   /ruta/a/tradingIA/app/services/nansen_mock.py
```

### 2. Verificar que tests pasan
```bash
cd /ruta/a/tradingIA

# Copiar test file
cp test_nansen_mock_dashboard.py tests/

# Ejecutar tests
pytest tests/test_nansen_mock_dashboard.py -v

# Test rápido (sin pytest)
python tests/test_nansen_mock_dashboard.py
```

---

## 🎮 USO EN DEBUG_MODE

### Automático (Por defecto)

En `app/core/config.py`:
```python
DEBUG_MODE: bool = True  # ← Ya está configurado
```

Cuando `DEBUG_MODE=True`, `main.py` automáticamente usa:
```python
# app/main.py línea ~20
client: Union[NansenMockClient, NansenClient] = (
    NansenMockClient() if settings.DEBUG_MODE else NansenClient()
)
```

### Ejecutar el bot en DEBUG_MODE

```bash
cd /ruta/a/tradingIA

# Con DEBUG_MODE=True (por defecto)
python app/main.py

# Output esperado:
# 🛠️ NansenMockClient inicializado (seed=42)
# 📊 Mock: 8 flujos generados
# 💼 Mock: 4 holdings generados
# 🔄 Mock: 6 DEX trades generados
# ✅ Ciclo de trading completado
```

---

## 📊 PATRONES DE DATOS DISPONIBLES

### Tabla de Test Scenarios

Cada moneda tiene un patrón diferente para testing:

| Token | Patrón | Flow USD | Signal | Acción Esperada |
|-------|--------|----------|--------|-----------------|
| **BTC** | Bullish | +5.2M | ✅ STRONG BUY | Entrar con tamaño máximo |
| **ETH** | Accumulation | +3.1M | ✅ BUY | Entrar con tamaño medio |
| **SOL** | Distribution | -2.1M | ⚠️ AVOID | No entrar, salir si tengo |
| **XRP** | Bearish | -4.3M | ❌ REJECT | Ignorar totalmente |
| **DOGE** | Volatile FOMO | +1.8M | ⚠️ RISKY | Entrar pequeño si score alto |
| **AVAX** | Consolidation | +0.45M | ⏸️ WAIT | Esperar más información |
| **LINK** | Quiet Accum. | +2.75M | ✅ BUY | Entrada discreta, bajo radar |
| **MATIC** | Micro Accum. | +0.95M | ⏸️ CAUTION | Entrar con cuidado |

### Cómo leer los patrones

```
PATRÓN: Bullish
├─ net_flow_usd: +5_200_000  (Smart Money COMPRANDO)
├─ net_flow_7d: +28_400_000  (Tendencia confirmada)
├─ trader_count: 47          (Muchas wallets comprando)
├─ exchange_netflow: -1.2M   (Sacando dinero de exchanges = BULLISH)
└─ Interpretación: "Smart Money está acumulando, sin sacarlo del mercado"

PATRÓN: Distribution
├─ net_flow_usd: -2_100_000  (Smart Money VENDIENDO)
├─ exchange_netflow: +1.5M   (Metiendo en exchanges = BEARISH)
└─ Interpretación: "Smart Money está saliendo, preparando dumping"

PATRÓN: Consolidation
├─ net_flow_usd: +0.45M      (Inflow bajo)
├─ net_flow_7d: +1.2M        (No confirmado en 7 días)
└─ Interpretación: "Señal débil, esperar más claridad"
```

---

## 🖥️ VISUALIZAR EN DASHBOARD

### Dashboard JSON Response

Cuando el bot está corriendo en DEBUG_MODE y se conecta al dashboard:

```json
{
  "status": "success",
  "timestamp": "2025-03-02T15:30:00Z",
  "debug_mode": true,
  "data": {
    "market_flows": [
      {
        "token_symbol": "BTC",
        "net_flow_usd": 5200000.0,
        "net_flow_7d_usd": 28400000.0,
        "trader_count": 47,
        "metadata": {
          "pattern": "bullish_accumulation",
          "confidence": 0.92,
          "risk_factors": []
        }
      },
      // ... 7 más
    ],
    "smart_money_holdings": [
      {
        "token_symbol": "BTC",
        "total_value_usd": 450000000.0,
        "current_pnl_percent": 9.2,
        "conviction": "long_term_hold"
      },
      // ... 3 más
    ],
    "recent_trades": [
      {
        "dex_name": "Uniswap V3",
        "token_sold_symbol": "USDC",
        "token_bought_symbol": "BTC",
        "timestamp": 1709403000
      },
      // ... 5 más
    ],
    "summary": {
      "mode": "DEBUG_MOCK",
      "total_flows": 8,
      "test_scenarios": {
        "BTC": "✅ Bullish - Strong buy signal",
        "ETH": "✅ Accumulation - Good entry",
        // ...
      }
    }
  }
}
```

### Cómo verificar en el dashboard

1. **Terminal:** Corre el bot
   ```bash
   python app/main.py
   # Verás outputs como:
   # 📊 Mock: 8 flujos generados
   # ✅ Ciclo de trading completado
   ```

2. **Browser:** Abre dashboard (si existe)
   ```
   http://localhost:3000/dashboard
   
   Deberías ver:
   • Heatmap con 8 monedas (BTC verde, XRP roja, etc.)
   • Smart Money Flows con patrones diferenciados
   • DEX Trades listados por timestamp
   • Debug mode badge: "DEBUG_MODE 🛠️"
   ```

3. **DevTools (Network):** Inspecciona WebSocket
   ```
   // Cada 15 segundos (POLLING_INTERVAL_MINUTES)
   Frame: {
     type: "MARKET_UPDATE",
     timestamp: "2025-03-02T15:32:45Z",
     flows: [ ... ]
   }
   ```

---

## 🔧 PERSONALIZAR DATOS MOCK

### Cambiar seed para diferentes datos
```python
# app/main.py
client = NansenMockClient(seed=99)  # ← Diferente seed = diferentes datos

# Resultado:
# Mismo BTC (siempre bullish)
# Pero otros tokens pueden variar
# Reproducible: seed=99 siempre genera lo mismo
```

### Modificar un patrón específico
```python
# app/services/nansen_mock.py línea ~45
SmartMoneyFlow(
    token_symbol="BTC",
    net_flow_usd=10_000_000.0,  # ← CAMBIAR aquí
    # ... resto sin cambios
)
```

### Añadir nuevo token a testing
```python
# Agregar antes del último item en get_smart_money_flows()
SmartMoneyFlow(
    token_symbol="CUSTOM",
    net_flow_usd=1_500_000.0,
    net_flow_7d_usd=7_500_000.0,
    trader_count=25,
    exchange_netflow=-600_000.0,
    whales_accumulating=5,
    metadata={
        "pattern": "custom_test",
        "confidence": 0.75,
        "risk_factors": [],
    }
),
```

---

## ✅ CHECKLIST DE VERIFICACIÓN

- [ ] **Archivo copiado:** `nansen_mock_improved.py` → `app/services/nansen_mock.py`
- [ ] **Tests pasan:** `pytest tests/test_nansen_mock_dashboard.py -v`
- [ ] **Bot ejecuta:** `python app/main.py` sin errores
- [ ] **Debug output visible:** Ver "Mock: 8 flujos generados" en consola
- [ ] **Patrones reconocibles:** BTC bullish, XRP bearish, etc.
- [ ] **Dashboard conecta:** WebSocket recibe datos mock
- [ ] **Heatmap renderiza:** 8 monedas con colores diferenciados

---

## 📈 CÓMO USAR PARA TESTING

### Scenario 1: Verificar que RiskManager rechaza XRP
```bash
# Terminal 1: Ejecutar bot
python app/main.py

# Terminal 2: Monitorear logs
tail -f bot_final_check.log | grep XRP

# Esperado:
# [Risk] XRP rechazado: <razón>
# ✅ Significa que el RiskManager está filtrando correctamente
```

### Scenario 2: Verificar que ExitManager cierra SOL (Distribution)
```bash
# 1. Agregar SOL a DB manualmente (si es necesario)
# 2. Ejecutar bot
# 3. Monitorear logs para "SOL" + "Exit"

tail -f bot_final_check.log | grep "SOL"

# Esperado:
# [Exit] POSICIÓN CERRADA: SOL @ precio
# ✅ Significa que el exit manager está funcionando
```

### Scenario 3: Verificar que SignalEngine da score correcto
```bash
# Buscar en logs
tail -f bot_final_check.log | grep "Score="

# Esperado output:
# [BTC] Score=85.0 (vol=95 conc=70 dex=80) held=True valid=True
# [ETH] Score=72.0 (vol=70 conc=65 dex=75) held=True valid=True
# [SOL] Score=15.0 (vol=20 conc=10 dex=8) held=False valid=False ✓

# ✅ Significa que el scoring está diferenciando correctamente
```

---

## 🐛 TROUBLESHOOTING

### Problema: "No module named 'app.services.nansen_mock'"
**Solución:**
```bash
# Verificar que el archivo existe
ls -la app/services/nansen_mock.py
# Asegurarse que __init__.py existe
touch app/services/__init__.py
# Reinstalar paquete
pip install -e .
```

---

## 📚 REFERENCIAS
- **Archivo mejorado:** `nansen_mock_improved.py`
- **Tests:** `test_nansen_mock_dashboard.py`
- **Config:** `app/core/config.py` (DEBUG_MODE)
- **Punto de entrada:** `app/main.py` (línea ~20)
- **SignalEngine:** `app/services/signal_engine.py`

---

## 🎬 PRÓXIMOS PASOS
1. ✅ Copiar `nansen_mock_improved.py` al repo
2. ✅ Ejecutar tests para verificar
3. ✅ Ejecutar bot en DEBUG_MODE
4. ✅ Conectar dashboard y visualizar
5. ✅ Monitorear logs para verificar lógica
6. 🔄 Iterar: Cambiar patrones según necesidad
7. 📤 Cuando esté listo: Cambiar a NansenClient real
