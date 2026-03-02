"""
Dashboard TradingIA — Rediseño UX/UI Moderno
=============================================
Panel de control principal del bot de trading.
Versión: 2.0 — Dark Pro Theme + Glassmorphism
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from loguru import logger
import asyncio

from app.services.ai_analyst import AIAnalyst
from app.services.portfolio_service import PortfolioService
from app.services.nansen_mock import NansenMockClient
from app.core.config import settings

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
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  /* ── Base ── */
  html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', sans-serif;
  }
  .stApp {
    background: #0A0E1A;
    color: #F1F5F9;
  }

  /* ── Sidebar ── */
  section[data-testid="stSidebar"] {
    background: #0B1A2C !important;
    border-right: 2px solid rgba(0,212,255,0.12) !important;
  }
  section[data-testid="stSidebar"] > div {
    background: #0B1A2C !important;
  }
  section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #94A3B8;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 8px;
  }

  /* ── Cards ── */
  .glass-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 20px 24px;
    backdrop-filter: blur(12px);
    box-shadow: 0 4px 24px rgba(0,0,0,0.3);
    margin-bottom: 16px;
  }
  .kpi-card {
    background: rgba(0,212,255,0.04);
    border: 1px solid rgba(0,212,255,0.15);
    border-radius: 14px;
    padding: 16px 20px;
    box-shadow: 0 0 20px rgba(0,212,255,0.06), inset 0 1px 0 rgba(255,255,255,0.06);
  }

  /* ── Header ── */
  .header-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 28px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 18px;
    margin-bottom: 24px;
  }
  .header-title {
    font-size: 26px;
    font-weight: 700;
    color: #F1F5F9;
    letter-spacing: -0.5px;
    margin: 0;
    line-height: 1.2;
  }
  .header-subtitle {
    font-size: 13px;
    color: #64748B;
    margin: 3px 0 0 0;
  }
  .status-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: rgba(16,185,129,0.1);
    border: 1px solid rgba(16,185,129,0.3);
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 600;
    color: #10B981;
  }
  .status-dot {
    width: 8px;
    height: 8px;
    background: #10B981;
    border-radius: 50%;
    animation: pulse-dot 2s ease-in-out infinite;
  }
  .status-ts {
    font-size: 11px;
    color: #94A3B8;
    margin-top: 6px;
    text-align: right;
  }
  @keyframes pulse-dot {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(16,185,129,0.4); }
    50% { opacity: 0.7; box-shadow: 0 0 0 5px rgba(16,185,129,0); }
  }

  /* ── Risk param grid ── */
  .risk-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-top: 8px;
  }
  .risk-item {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 10px 12px;
  }
  .risk-label {
    font-size: 10px;
    color: #64748B;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .risk-value {
    font-size: 18px;
    font-weight: 700;
    color: #F1F5F9;
    margin-top: 2px;
  }
  .risk-value.green { color: #10B981; }
  .risk-value.red   { color: #EF4444; }

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: rgba(255,255,255,0.04);
    border-radius: 12px;
    padding: 4px;
    border: 1px solid rgba(255,255,255,0.06);
  }
  .stTabs [data-baseweb="tab"] {
    border-radius: 9px;
    font-size: 14px;
    font-weight: 500;
    color: #64748B;
    padding: 8px 18px;
  }
  .stTabs [aria-selected="true"] {
    background: rgba(0,212,255,0.1) !important;
    color: #00D4FF !important;
    border: 1px solid rgba(0,212,255,0.2) !important;
  }
  .stTabs [data-baseweb="tab-panel"] {
    padding-top: 20px;
  }

  /* ── Chat ── */
  .stChatInput textarea,
  .stChatInput input {
    background: #1A2744 !important;
    border: 1px solid rgba(0,212,255,0.25) !important;
    border-radius: 12px !important;
    color: #F1F5F9 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
  }
  .stChatInput textarea::placeholder,
  .stChatInput input::placeholder {
    color: #64748B !important;
  }
  /* Contenedor del input de chat */
  .stChatInput > div {
    background: #1A2744 !important;
    border: 1px solid rgba(0,212,255,0.25) !important;
    border-radius: 14px !important;
  }
  /* Burbujas de chat — fondo sólido con buen contraste */
  .stChatMessage {
    background: #111D33 !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    border-radius: 14px !important;
    padding: 14px 16px !important;
  }
  /* Texto dentro de los mensajes — blanco puro */
  .stChatMessage p,
  .stChatMessage span,
  .stChatMessage div,
  .stChatMessage li {
    color: #E8EDF5 !important;
    font-size: 14px !important;
    line-height: 1.65 !important;
  }
  /* Burbuja del usuario ligeramente diferente */
  [data-testid="stChatMessageContent"] {
    color: #E8EDF5 !important;
  }

  /* ── Buttons ── */
  .stButton > button {
    background: linear-gradient(135deg, rgba(0,212,255,0.12), rgba(124,58,237,0.12));
    border: 1px solid rgba(0,212,255,0.2);
    border-radius: 10px;
    color: #00D4FF;
    font-weight: 600;
    font-size: 13px;
    transition: all 0.2s ease;
  }
  .stButton > button:hover {
    background: linear-gradient(135deg, rgba(0,212,255,0.22), rgba(124,58,237,0.22));
    border-color: rgba(0,212,255,0.5);
    box-shadow: 0 4px 15px rgba(0,212,255,0.2);
    transform: translateY(-1px);
  }
  .stButton > button.clear-btn {
    border-color: rgba(239,68,68,0.3);
    color: #EF4444;
    background: rgba(239,68,68,0.06);
  }

  /* ── Metrics ── */
  [data-testid="metric-container"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 14px 18px !important;
  }
  [data-testid="metric-container"] label {
    color: #64748B !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em;
  }
  [data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 22px !important;
    font-weight: 700 !important;
    color: #F1F5F9 !important;
  }

  /* ── DataFrames ── */
  .stDataFrame {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.07) !important;
  }

  /* ── Divider ── */
  hr {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.07);
    margin: 16px 0;
  }

  /* ── Footer ── */
  .footer-bar {
    text-align: center;
    color: #334155;
    font-size: 12px;
    padding: 16px 0 8px 0;
    border-top: 1px solid rgba(255,255,255,0.05);
    margin-top: 32px;
  }

  /* ── Section titles ── */
  .section-title {
    font-size: 15px;
    font-weight: 600;
    color: #E2E8F0;
    letter-spacing: -0.2px;
    margin-bottom: 14px;
  }
  .section-subtitle {
    font-size: 13px;
    color: #64748B;
    margin-top: -10px;
    margin-bottom: 16px;
  }
</style>
""", unsafe_allow_html=True)


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

    # Status
    llm_label = settings.LLM_PROVIDER.upper()
    debug_badge = "🟡 DEBUG" if settings.DEBUG_MODE else "🟢 LIVE"
    st.markdown(f"""
    <div class='status-pill'>
      <div class='status-dot'></div>
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


# ==================== TABS ====================
tab1, tab2, tab3 = st.tabs(["🤖  Asistente IA", "📊  Smart Money", "💼  Cartera"])


# ──────────────────────────────────────────────
# TAB 1 — CHAT AI (patrón nativo Streamlit)
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
            st.warning("⚠️ El asistente de IA no está disponible. Revisa la configuración del proveedor LLM.")


# ──────────────────────────────────────────────
# TAB 2 — SMART MONEY FLOWS
# ──────────────────────────────────────────────
with tab2:
    st.markdown("<div class='section-title'>Smart Money Flows · Nansen</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-subtitle'>Movimientos de capital institucional en las últimas 24 horas.</div>", unsafe_allow_html=True)

    try:
        nansen = NansenMockClient()
        flows = nansen.get_smart_money_flows()

        if flows and hasattr(flows, "data") and flows.data:
            rows = []
            for flow in flows.data[:10]:
                net = flow.net_flow_usd
                rows.append({
                    "Token":        flow.token_symbol,
                    "Netflow 24h":  net,
                    "Señal":        "🟢 INFLOW" if net >= 0 else "🔴 OUTFLOW",
                    "Traders":      flow.trader_count,
                    "Edad (días)":  flow.token_age_days,
                    "Market Cap":   flow.market_cap_usd,
                })

            df = pd.DataFrame(rows)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Netflow 24h": st.column_config.NumberColumn(
                        "Flujo Neto 24h ($)", format="$%.0f"
                    ),
                    "Market Cap": st.column_config.NumberColumn(
                        "Cap. de Mercado ($)", format="$%.0f"
                    ),
                    "Traders": st.column_config.NumberColumn("Nº Traders"),
                    "Señal": st.column_config.TextColumn("Señal", width="small"),
                    "Edad (días)": st.column_config.NumberColumn("Edad (días)"),
                }
            )

            # Mini-resumen
            inflows  = [r for r in rows if r["Netflow 24h"] >= 0]
            outflows = [r for r in rows if r["Netflow 24h"] < 0]
            c1, c2 = st.columns(2)
            with c1:
                st.metric("🟢 Tokens con Entrada de Capital", len(inflows))
            with c2:
                st.metric("🔴 Tokens con Salida de Capital", len(outflows))
        else:
            st.info("📭 Sin datos de Smart Money disponibles en este momento. Refresca la página.")

    except Exception as e:
        st.error(f"❌ Error cargando Smart Money: {e}")
        logger.error(f"[Dashboard] Error Smart Money: {e}")


# ──────────────────────────────────────────────
# TAB 3 — PORTFOLIO
# ──────────────────────────────────────────────
with tab3:
    st.markdown("<div class='section-title'>Portfolio Actual</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-subtitle'>Posiciones abiertas y estado de la cartera.</div>", unsafe_allow_html=True)

    try:
        portfolio = PortfolioService()
        trades = asyncio.run(portfolio.get_open_trades())

        if trades:
            total_invested = sum(t.amount_usd for t in trades)
            max_pos        = max(t.amount_usd for t in trades)

            # KPIs
            pm1, pm2, pm3 = st.columns(3)
            with pm1:
                st.metric("💰 Total Invertido", f"${total_invested:,.2f}")
            with pm2:
                st.metric("📂 Posiciones Abiertas", len(trades),
                          delta=f"de {settings.MAX_OPEN_TRADES} permitidas")
            with pm3:
                st.metric("🏆 Posición Mayor", f"${max_pos:,.2f}")

            st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

            # Tabla
            data = []
            for trade in trades:
                data.append({
                    "Token":        trade.token_symbol,
                    "Entry Price":  trade.entry_price,
                    "Amount (USD)": trade.amount_usd,
                    "Status":       trade.status,
                    "Entry Date":   (
                        trade.entry_date.strftime("%Y-%m-%d %H:%M")
                        if hasattr(trade.entry_date, "strftime")
                        else str(trade.entry_date)
                    ),
                })

            df = pd.DataFrame(data)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Entry Price":  st.column_config.NumberColumn("Precio de Entrada ($)", format="$%.4f"),
                    "Amount (USD)": st.column_config.NumberColumn("Importe ($)", format="$%.2f"),
                    "Status":       st.column_config.TextColumn("Estado", width="small"),
                    "Entry Date":   st.column_config.TextColumn("Fecha de Entrada"),
                    "Token":        st.column_config.TextColumn("Token"),
                }
            )
        else:
            st.info("💼 Cartera vacía — No hay posiciones abiertas actualmente.")
            st.markdown(
                "💡 Usa el **Asistente IA** para analizar señales y ejecutar operaciones simuladas con `/buy TOKEN IMPORTE`.",
                unsafe_allow_html=False
            )

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
  DB: PostgreSQL &nbsp;·&nbsp;
  Status: <strong style='color:#10B981'>✅ Online</strong>
</div>
""", unsafe_allow_html=True)