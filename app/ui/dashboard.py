"""
Dashboard TradingIA — Rediseño UX/UI Moderno
=============================================
Panel de control principal del bot de trading.
Versión: 2.0 — Dark Pro Theme + Glassmorphism
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from loguru import logger
import asyncio
import numpy as np

from app.services.ai_analyst import AIAnalyst
from app.services.portfolio_service import PortfolioService
from app.services.nansen_mock import NansenMockClient
from app.services.nansen_client import NansenClient
from app.core.config import settings
from app.infraestructure.exchange_client import get_exchange_client

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="TradingIA Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "TradingIA — Smart Money AI Agent"}
)

# ==================== DESIGN SYSTEM CSS ====================
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

  /* ── Base ── */
  html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', sans-serif;
  }
  .stApp {
    background: #080C17;
    color: #F1F5F9;
  }

  /* ── Sidebar ── */
  section[data-testid="stSidebar"] {
    background: #0C1221 !important;
    border-right: 1px solid rgba(0,212,255,0.15) !important;
  }
  section[data-testid="stSidebar"] > div {
    background: #0C1221 !important;
  }
  
  /* ── Header & Titles ── */
  .header-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 24px 32px;
    background: linear-gradient(90deg, rgba(0,212,255,0.05) 0%, rgba(124,58,237,0.05) 100%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    margin-bottom: 28px;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
  }
  .header-title {
    font-size: 28px;
    font-weight: 800;
    background: linear-gradient(90deg, #FFFFFF, #00D4FF);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -1px;
    margin: 0;
  }

  /* ── Glass Cards ── */
  .glass-card {
    background: rgba(13, 22, 41, 0.7);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 18px;
    padding: 24px;
    backdrop-filter: blur(16px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    margin-bottom: 20px;
  }
  
  /* ── KPI Grid ── */
  .kpi-container {
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
  }
  .stMetric {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
    padding: 16px !important;
  }

  /* ── Trading Visuals ── */
  .trading-chart-container {
    background: #0D1629;
    border: 1px solid rgba(0,212,255,0.2);
    border-radius: 16px;
    padding: 5px;
    margin-top: 10px;
  }

  /* ── Status Indicator ── */
  .status-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(16,185,129,0.1);
    border: 1px solid rgba(16,185,129,0.3);
    border-radius: 100px;
    padding: 6px 16px;
    font-size: 13px;
    font-weight: 700;
    color: #10B981;
    box-shadow: 0 0 15px rgba(16,185,129,0.1);
  }
  .status-pill.debug {
    color: #F59E0B;
    background: rgba(245,158,11,0.1);
    border-color: rgba(245,158,11,0.3);
  }

  /* ── Custom Scrollbar ── */
  ::-webkit-scrollbar {
    width: 8px;
  }
  ::-webkit-scrollbar-track {
    background: #080C17;
  }
  ::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.1);
    border-radius: 4px;
  }
  ::-webkit-scrollbar-thumb:hover {
    background: rgba(0,212,255,0.2);
  }

  /* Tabs styling enhancement */
  .stTabs [data-baseweb="tab-list"] {
    background-color: transparent !important;
  }
  .stTabs [data-baseweb="tab"] {
    height: 45px !important;
    background: rgba(255,255,255,0.03) !important;
    border-radius: 10px 10px 0 0 !important;
    margin-right: 4px !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    border-bottom: none !important;
    color: #64748B !important;
  }
  .stTabs [aria-selected="true"] {
    background: rgba(0,212,255,0.08) !important;
    color: #00D4FF !important;
    border-top: 2px solid #00D4FF !important;
  }
</style>
""", unsafe_allow_html=True)


# ==================== VISUAL HELPERS ====================

def create_gauge_chart(value, title, color="#00D4FF"):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        title = {'text': title, 'font': {'size': 18, 'color': '#94A3B8'}},
        number = {'font': {'color': '#F1F5F9'}},
        gauge = {
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#334155"},
            'bar': {'color': color},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 2,
            'bordercolor': "rgba(255,255,255,0.1)",
            'steps': [
                {'range': [0, 30], 'color': 'rgba(16,185,129,0.1)'},
                {'range': [30, 70], 'color': 'rgba(245,158,11,0.1)'},
                {'range': [70, 100], 'color': 'rgba(239,68,68,0.1)'}
            ],
        }
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=20),
        height=200
    )
    return fig

def create_market_heatmap(df):
    if df.empty: return None
    
    fig = px.treemap(
        df, 
        path=[px.Constant("Cryptos"), 'Token'], 
        values='Netflow 24h Absolute',
        color='Netflow 24h',
        color_continuous_scale='RdYlGn',
        color_continuous_midpoint=0,
        hover_data=['Traders', 'Market Cap']
    )
    fig.update_layout(
        margin=dict(t=0, l=0, r=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color="#F1F5F9")
    )
    fig.update_traces(
        textinfo="label+value",
        texttemplate="<b>%{label}</b><br>$%{value:,.0s}",
        marker=dict(cornerradius=5)
    )
    return fig

async def fetch_ohlcv_data(symbol):
    try:
        exchange = await get_exchange_client()
        # Mocking for debug mode to ensure a pretty chart
        if settings.DEBUG_MODE:
            dates = [datetime.now() - timedelta(hours=i) for i in range(24)]
            prices = np.random.normal(60000, 500, 24)
            data = []
            for i, p in enumerate(prices):
                data.append([
                    int(dates[i].timestamp() * 1000), # ts
                    p * 0.99, # o
                    p * 1.02, # h
                    p * 0.98, # l
                    p * 1.01, # c
                    np.random.randint(10, 100) # v
                ])
            return data
            
        formatted_symbol = f"{symbol}/USDT" if "/" not in symbol else symbol
        return await exchange.exchange.fetch_ohlcv(formatted_symbol, timeframe='1h', limit=24)
    except Exception as e:
        logger.error(f"Error fetching OHLCV for chart: {e}")
        return None

def create_candlestick_fig(data, symbol):
    if not data: return None
    df = pd.DataFrame(data, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['ts'],
        open=df['o'], high=df['h'],
        low=df['l'], close=df['c'],
        increasing_line_color='#10B981', decreasing_line_color='#EF4444'
    )])
    
    fig.add_trace(go.Bar(
        x=df['ts'], y=df['v'], 
        name="Volume", 
        marker_color='rgba(0,212,255,0.2)',
        yaxis='y2'
    ))
    
    fig.update_layout(
        template='plotly_dark',
        title=f"Acción del Precio: {symbol}",
        xaxis_rangeslider_visible=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(title="Precio (USDT)", side="left"),
        yaxis2=dict(title="Volumen", overlaying='y', side='right', showgrid=False),
        margin=dict(l=0, r=0, t=50, b=0),
        height=350,
        hovermode='x unified'
    )
    return fig

# ==================== SESSION STATE ====================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "analyst" not in st.session_state:
    try:
        st.session_state.analyst = AIAnalyst()
    except Exception as e:
        st.error(f"❌ Error inicializando AIAnalyst: {e}")
        st.session_state.analyst = None


# ==================== SIDEBAR ====================
with st.sidebar:
    # Logo + Nombre
    st.markdown("""
    <div style='padding: 8px 0 20px 0;'>
      <div style='font-size:22px; font-weight:700; color:#F1F5F9; letter-spacing:-0.4px;'>
        📈 TradingIA
      </div>
      <div style='font-size:12px; color:#64748B; margin-top:3px;'>Smart Money AI Agent</div>
    </div>
    """, unsafe_allow_html=True)

    # Bot Status
    llm_label = settings.LLM_PROVIDER.upper()
    debug_badge = "🟡 DEBUG" if settings.DEBUG_MODE else "🟢 LIVE"
    st.markdown(f"""
    <div class='status-pill {"debug" if settings.DEBUG_MODE else ""}'>
      <div style='width:8px;height:8px;border-radius:50%;background:currentColor;box-shadow:0 0 8px currentColor;'></div>
      {debug_badge} · {llm_label}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Risk Parameters
    st.markdown("<div class='section-title' style='font-size:11px;color:#64748B;text-transform:uppercase;letter-spacing:.08em;font-weight:600;'>Parámetros de Riesgo</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='risk-grid'>
      <div class='risk-item'>
        <div class='risk-label'>Take Profit</div>
        <div class='risk-value green'>{settings.TAKE_PROFIT_PCT}%</div>
      </div>
      <div class='risk-item'>
        <div class='risk-label'>Stop Loss</div>
        <div class='risk-value red'>{settings.STOP_LOSS_PCT}%</div>
      </div>
      <div class='risk-item'>
        <div class='risk-label'>Max Trades</div>
        <div class='risk-value'>{settings.MAX_OPEN_TRADES}</div>
      </div>
      <div class='risk-item'>
        <div class='risk-label'>Max Drawdown</div>
        <div class='risk-value red'>{settings.MAX_DAILY_DRAWDOWN_PCT}%</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Botón limpiar chat
    if st.button("🗑️ Limpiar Chat", use_container_width=True, key="btn_clear_chat"):
        st.session_state.chat_history = []
        st.rerun()


# ==================== HEADER ====================
now_str = datetime.now().strftime("%Y-%m-%d  %H:%M")
debug_mode_text = "DEBUG" if settings.DEBUG_MODE else "RUNNING"
status_color = "#F59E0B" if settings.DEBUG_MODE else "#10B981"

st.markdown(f"""
<div class='header-bar'>
  <div>
    <div class='header-title'>📈 TradingIA Dashboard</div>
    <div class='header-subtitle'>Sistema de Trading Autónomo · Smart Money AI Analysis</div>
  </div>
  <div style='text-align:right;'>
    <div style='
      display:inline-flex; align-items:center; gap:7px;
      background: rgba(16,185,129,0.08);
      border: 1px solid {status_color}44;
      border-radius: 999px;
      padding: 6px 14px;
      font-size: 13px; font-weight: 600; color: {status_color};
    '>
      <div style='width:8px;height:8px;border-radius:50%;background:{status_color};
                  animation:pulse-dot 2s ease-in-out infinite;'></div>
      {debug_mode_text}
    </div>
    <div class='status-ts'>{now_str}</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ==================== KPI BAR ====================
kpi1, kpi2, kpi3 = st.columns(3)
with kpi1:
    st.metric(
        label="🎯 Take Profit",
        value=f"{settings.TAKE_PROFIT_PCT}%",
        delta="Objetivo activo"
    )
with kpi2:
    st.metric(
        label="🛡️ Stop Loss",
        value=f"{settings.STOP_LOSS_PCT}%",
        delta="Protección"
    )
with kpi3:
    st.metric(
        label="📊 Max Operaciones",
        value=settings.MAX_OPEN_TRADES,
        delta="Posiciones permitidas"
    )

st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)


# ==================== ASYNC HELPER ====================

def run_sync(coro):
    """Ejecuta una corrutina de forma síncrona dentro del loop de Streamlit."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
        return asyncio.run(coro)
    except Exception as e:
        logger.error(f"Error en run_sync: {e}")
        return None

# ==================== TABS ====================
tab1, tab2, tab3 = st.tabs(["🤖  Asistente IA", "📊  Smart Money", "💼  Cartera"])

# ──────────────────────────────────────────────
# TAB 1 — CHAT AI
# ──────────────────────────────────────────────
with tab1:
    st.markdown("<div class='section-title'>Análisis de Mercado con IA</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-subtitle'>Pregunta sobre movimientos de Smart Money, posiciones abiertas o usa los comandos <code>/buy</code> y <code>/sell</code>.</div>", unsafe_allow_html=True)

    # Historial de mensajes
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input nativo
    if prompt := st.chat_input("Escribe tu pregunta o un comando… ej: /buy ETH 200"):
        if st.session_state.analyst:
            # Mostrar mensaje del usuario inmediatamente
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.chat_history.append({"role": "user", "content": prompt})

            # Obtener respuesta con spinner
            with st.chat_message("assistant"):
                with st.spinner("🧠 Analizando tu consulta…"):
                    try:
                        response = st.session_state.analyst.ask_question(
                            prompt,
                            st.session_state.chat_history[:-1]
                        )
                        st.markdown(response)
                        st.session_state.chat_history.append(
                            {"role": "assistant", "content": response}
                        )
                    except Exception as e:
                        err_msg = f"❌ Error al procesar la consulta: `{e}`"
                        st.error(err_msg)
                        logger.error(f"[Dashboard] Error en chat: {e}")
        else:
            st.warning("⚠️ El asistente de IA no está disponible.")


# ──────────────────────────────────────────────
# TAB 2 — SMART MONEY FLOWS
# ──────────────────────────────────────────────
with tab2:
    st.markdown("<div class='section-title'>Vista de Mercado Multi-Detección</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-subtitle'>Identificación visual de anomalías de flujo y capitalización.</div>", unsafe_allow_html=True)

    try:
        nansen_choice = NansenMockClient() if settings.DEBUG_MODE else NansenClient()
        flows_resp = run_sync(nansen_choice.get_smart_money_flows())

        if flows_resp and hasattr(flows_resp, "data") and flows_resp.data:
            rows = []
            for flow in flows_resp.data:
                rows.append({
                    "Token":        flow.token_symbol,
                    "Netflow 24h":  flow.net_flow_usd,
                    "Netflow 24h Absolute": abs(flow.net_flow_usd) if flow.net_flow_usd else 0,
                    "Traders":      flow.trader_count,
                    "Market Cap":   flow.market_cap_usd,
                })
            
            df_flows = pd.DataFrame(rows)
            
            # --- Visualización 1: Heatmap ---
            heatmap_fig = create_market_heatmap(df_flows)
            if heatmap_fig:
                st.plotly_chart(heatmap_fig, use_container_width=True)
            
            # --- Visualización 2: Tabla de Detalles ---
            st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
            st.dataframe(
                df_flows.drop(columns=['Netflow 24h Absolute']).sort_values('Netflow 24h', ascending=False),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Netflow 24h": st.column_config.NumberColumn("Netflow 24h ($)", format="$%.0f"),
                    "Market Cap": st.column_config.NumberColumn("Cap. Mercado ($)", format="$%.0s"),
                }
            )
        else:
            st.info("🔎 Escaneando mercado... No hay datos de flujo significativos todavía.")
    except Exception as e:
        st.error(f"Error visualizando mercado: {e}")


# ──────────────────────────────────────────────
# TAB 3 — PORTFOLIO
# ──────────────────────────────────────────────
with tab3:
    st.markdown("<div class='section-title'>Portfolio Actual</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-subtitle'>Posiciones abiertas y estado de la cartera.</div>", unsafe_allow_html=True)

    try:
        portfolio = PortfolioService()
        trades = run_sync(portfolio.get_open_trades())
        daily_pnl = run_sync(portfolio.get_daily_pnl()) or 0.0

        pc1, pc2 = st.columns([1, 2])
        
        with pc1:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            # Gauge de riesgo / Drawdown
            drawdown_val = (abs(daily_pnl) / (10000 * (settings.MAX_DAILY_DRAWDOWN_PCT/100))) * 100 if daily_pnl < 0 else 0
            st.plotly_chart(create_gauge_chart(min(drawdown_val, 100), "Riesgo Diario", color="#EF4444" if drawdown_val > 50 else "#00D4FF"), use_container_width=True)
            
            st.metric("💰 PnL Realizado Hoy", f"${daily_pnl:,.2f}", delta_color="normal")
            st.markdown("</div>", unsafe_allow_html=True)

        with pc2:
            if trades:
                selected_symbol = st.selectbox("Analizar Posición:", [t.token_symbol for t in trades])
                ohlcv = run_sync(fetch_ohlcv_data(selected_symbol))
                if ohlcv:
                    st.plotly_chart(create_candlestick_fig(ohlcv, selected_symbol), use_container_width=True)
            else:
                st.info("💼 Cartera vacía — No hay trades activos para graficar.")

        if trades:
            st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
            # Tabla estilizada
            data = []
            for t in trades:
                data.append({
                    "Token": t.token_symbol,
                    "Entrada": t.entry_price,
                    "Inversión": t.amount_usd,
                    "Estado": t.status,
                    "Fecha": t.entry_date.strftime("%H:%M %d/%m") if hasattr(t.entry_date, 'strftime') else str(t.entry_date)
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
        else:
            st.info("💼 Cartera vacía — No hay posiciones abiertas actualmente.")

    except Exception as e:
        st.error(f"❌ Error cargando portfolio: {e}")
        logger.error(f"[Dashboard] Error Portfolio: {e}")


# ==================== FOOTER ====================
model_info = settings.LLM_MODEL if settings.LLM_PROVIDER == "local" else settings.GEMINI_MODEL
st.markdown(f"""
<div class='footer-bar'>
  TradingIA © {datetime.now().year} &nbsp;·&nbsp;
  Smart Money AI Agent &nbsp;·&nbsp;
  Model: <strong style='color:#475569'>{model_info}</strong> &nbsp;·&nbsp;
  Status: <strong style='color:#10B981'>✅ Online</strong>
</div>
""", unsafe_allow_html=True)