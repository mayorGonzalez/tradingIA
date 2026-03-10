# 📺 VISUALIZACIONES DASHBOARD CON DATOS MOCK

---

## 🗺️ HEATMAP DE MERCADO (Market Heatmap)

### Estado Visual Esperado

```
┌──────────────────────────────────────────────────────────────┐
│  MARKET HEATMAP - Smart Money Flows                     ✨    │
│  Mode: DEBUG 🛠️                                              │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────┬────────────────┐                │
│  │       BTC ✅            │   ETH ✅       │   (Grande)     │
│  │    +5.2M             │  +3.1M         │   (Bullish)    │
│  │   +7.66% 24h         │  +5.2% 24h     │                 │
│  └─────────────────────────┴────────────────┘                │
│                                                               │
│  ┌──────────┬──────────┬─────────┬──────────┐                │
│  │  SOL ⚠️  │ XRP ❌   │DOGE ⚠️ │ AVAX ⏸️ │  (Medianos)   │
│  │-2.1M     │-4.3M    │+1.8M   │+450K    │                 │
│  │-3.2% 24h │-8.9%24h │+12% 24h│+2.1% 24h│                 │
│  └──────────┴──────────┴─────────┴──────────┘                │
│                                                               │
│  ┌─────────┬─────────┐                                        │
│  │ LINK ✅ │ MATIC ⏸│  (Pequeños)                            │
│  │ +2.75M  │ +950K  │                                        │
│  │+4.1% 24h│+3% 24h │                                        │
│  └─────────┴─────────┘                                        │
│                                                               │
├─ Leyenda: ───────────────────────────────────────────────────┤
│  🟩 Verde    = Inflow Bullish (Comprar)                      │
│  🟨 Amarillo = Neutral / Consolidation                       │
│  🟥 Rojo     = Outflow Bearish (Vender)                      │
│  ✅ Check    = Señal válida para trading                     │
│  ⚠️ Warning  = Señal ambigua / riesgosa                      │
│  ❌ Cross    = Rechazada                                     │
│  ⏸️ Pausa    = Esperar más información                       │
└──────────────────────────────────────────────────────────────┘
```

COLORES EXACTOS (RGB):
├─ BTC: #00ff88  (Verde neón fuerte)
├─ ETH: #00cc66  (Verde suave)
├─ SOL: #ffaa00  (Naranja - distribución)
├─ XRP: #ff3366  (Rojo neón - bearish)
├─ DOGE: #ffaa00 (Naranja - volatile)
├─ AVAX: #a0a0d0 (Gris azulado - neutral)
├─ LINK: #00ff88 (Verde - acumulación)
└─ MATIC: #a0a0d0 (Gris - caution)

---

## 📊 SMART MONEY FLOWS TABLE (Tabla Detallada)

### Vista de Datos Crudos

```
╔════════════════════════════════════════════════════════════════════════════╗
║  SMART MONEY FLOWS - 24h Analysis                          [Debug Mode] 🛠 ║
╠═════════╦══════════╦═════════════╦═════════════╦═══════════╦══════════════╣
║ Token   ║ 24h Flow ║ 7d Flow     ║ Traders     ║ Exchange  ║ Signal       ║
║         ║ (USD)    ║ (USD)       ║ Count       ║ NetFlow   ║              ║
╠═════════╬══════════╬═════════════╬═════════════╬═══════════╬══════════════╣
║ BTC     ║ +5.2M    ║ +28.4M      ║ 47          ║ -1.2M     ║ ✅ STRONG BUY ║
║ ETH     ║ +3.1M    ║ +18.9M      ║ 35          ║ -850K     ║ ✅ BUY       ║
║ SOL     ║ -2.1M    ║ -8.4M       ║ 22          ║ +1.5M     ║ ⚠️ AVOID      ║
║ XRP     ║ -4.3M    ║ -22.1M      ║ 8           ║ +2.8M     ║ ❌ REJECT    ║
║ DOGE    ║ +1.8M    ║ -3.2M       ║ 18          ║ +600K     ║ ⚠️ RISKY     ║
║ AVAX    ║ +450K    ║ +1.2M       ║ 12          ║ -200K     ║ ⏸️ WAIT       ║
║ LINK    ║ +2.75M   ║ +14.5M      ║ 29          ║ -1.1M     ║ ✅ BUY       ║
║ MATIC   ║ +950K    ║ +2.1M       ║ 15          ║ -500K     ║ ⏸️ CAUTION   ║
╚═════════╩══════════╩═════════════╩═════════════╩═══════════╩══════════════╝
```

---

## 🏆 SMART MONEY HOLDINGS (Posiciones Acumuladas)

```
╔════════════════════════════════════════════════════════════════════════════╗
║  SMART MONEY HOLDINGS - Accumulated Positions                             ║
╠═════════╦══════════════╦═════════════╦═══════════════╦════════════════════╣
║ Token   ║ Total Value  ║ Wallet Qty  ║ Avg Entry     ║ Current PnL        ║
║         ║ (USD)        ║             ║ Price         ║ %                  ║
╠═════════╬══════════════╬═════════════╬═══════════════╬════════════════════╣
║ BTC     ║ $450.0M      ║ 47 wallets  ║ $62,500       ║ +9.2% ✅ PROFIT    ║
║ ETH     ║ $280.0M      ║ 35 wallets  ║ $2,100        ║ +12.5% ✅ PROFIT   ║
║ LINK    ║ $85.0M       ║ 29 wallets  ║ $18.50        ║ +22.1% ✅ PROFIT   ║
║ AVAX    ║ $45.0M       ║ 12 wallets  ║ $28.00        ║ +42.8% ✅ PROFIT   ║
╚═════════╩══════════════╩═════════════╩═══════════════╩════════════════════╝
```

---

## 🔄 DEX TRADES (Últimos Movimientos)

```
╔════════════════════════════════════════════════════════════════════════════╗
║  RECENT DEX TRADES - Smart Money Activity                                 ║
╠═══════════════════════════════════════════════════════════════════════════╣
║ Trade  │ DEX         │ Pair               │ Amount        │ 2h Ago │ Type  ║
╠═══════════════════════════════════════════════════════════════════════════╣
║ #1     │ Uniswap V3  │ USDC → BTC        │ 500k → 7.25   │ 2h     │ BUY✅ ║
║ #2     │ Uniswap V3  │ USDT → ETH        │ 300k → 142    │ 3h     │ BUY✅ ║
║ #3     │ Curve       │ USDC → LINK       │ 200k → 10.8k  │ 5h     │ BUY✅ ║
║ #4     │ Uniswap V3  │ USDT → AVAX       │ 150k → 5.3k   │ 1h     │ BUY✅ ║
║ #5     │ Balancer    │ SOL → USDC        │ 850 → 180k    │ 4h     │SELL❌║
║ #6     │ Uniswap V3  │ XRP → USDT        │ 15k → 9.3k    │ 6h     │SELL❌║
╚═══════════════════════════════════════════════════════════════════════════╝
```
