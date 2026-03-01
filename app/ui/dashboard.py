"""
Dashboard TradingIA - Interfaz Streamlit
==========================================
Panel de control principal del bot de trading.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
import asyncio

from app.services.ai_analyst import AIAnalyst
from app.services.portfolio_service import PortfolioService
from app.services.nansen_mock import NansenMockClient
from app.core.config import settings

# Configuración Streamlit
st.set_page_config(
    page_title="TradingIA Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos
st.markdown("""
<style>
    .main { padding: 0rem 1rem; }
    h1 { color: #1f77b4; text-align: center; }
    .metric-card { 
        background-color: #f0f2f6; 
        padding: 20px; 
        border-radius: 10px;
        margin: 10px 0;
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
    st.title("⚙️ Configuración")
    
    st.markdown("### 📊 Estado del Sistema")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("LLM Provider", settings.LLM_PROVIDER.upper(), delta="Active")
    with col2:
        st.metric("Debug Mode", "ON" if settings.DEBUG_MODE else "OFF", 
                 delta_color="normal" if settings.DEBUG_MODE else "inverse")
    
    st.markdown("---")
    
    st.markdown("### 🤖 LLM Info")
    if settings.LLM_PROVIDER == "local":
        st.info(f"🟢 **Modelo Local**: {settings.LLM_MODEL}\n\n"
               f"📍 **URL**: {settings.LLM_BASE_URL}")
    else:
        st.info(f"🔴 **Gemini API**: {settings.GEMINI_MODEL}")
    
    st.markdown("---")
    
    st.markdown("### 📈 Parámetros de Riesgo")
    st.write(f"**Take Profit**: {settings.TAKE_PROFIT_PCT}%")
    st.write(f"**Stop Loss**: {settings.STOP_LOSS_PCT}%")
    st.write(f"**Max Trades**: {settings.MAX_OPEN_TRADES}")
    
    st.markdown("---")
    
    if st.button("🔄 Limpiar Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

# ==================== MAIN CONTENT ====================
st.markdown("# 📈 TradingIA Dashboard")
st.markdown("Sistema de Trading Autónomo con AI Smart Money Analysis")

# Crear tabs
tab1, tab2, tab3, tab4 = st.tabs(["🤖 Chat AI", "📊 Smart Money", "💼 Portfolio", "📋 Información"])

# ==================== TAB 1: CHAT AI ====================
with tab1:
    st.markdown("### 🤖 Análisis de Mercado con AI")
    st.markdown("Haz preguntas sobre los movimientos de Smart Money, posiciones abiertas y señales del bot.")
    
    # Chat display
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f"**Tú**: {message['content']}")
            else:
                st.markdown(f"**AI**: {message['content']}")
    
    # Input
    st.markdown("---")
    user_input = st.text_input(
        "Pregunta al agente:",
        placeholder="Ej: ¿Cuál es el netflow de BTC? o /buy BTC 100",
        key="user_input"
    )
    
    if user_input and st.session_state.analyst:
        try:
            # Guardar pregunta en historial
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            # Obtener respuesta
            response = st.session_state.analyst.ask_question(
                user_input, 
                st.session_state.chat_history[:-1]  # Sin el último (que acabamos de añadir)
            )
            
            # Guardar respuesta
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error: {e}")
            logger.error(f"[Dashboard] Error en chat: {e}")

# ==================== TAB 2: SMART MONEY ====================
with tab2:
    st.markdown("### 📊 Smart Money Flows (Nansen)")
    
    try:
        nansen = NansenMockClient()
        flows = nansen.get_smart_money_flows()
        
        if flows and hasattr(flows, 'data'):
            data = []
            for flow in flows.data[:10]:
                data.append({
                    "Token": flow.token_symbol,
                    "Netflow 24h ($)": f"${flow.net_flow_usd:,.0f}",
                    "Traders": flow.trader_count,
                    "Token Age (days)": flow.token_age_days,
                    "Market Cap ($)": f"${flow.market_cap_usd:,.0f}"
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("📭 Sin datos de Smart Money disponibles")
    except Exception as e:
        st.error(f"❌ Error cargando Smart Money: {e}")

# ==================== TAB 3: PORTFOLIO ====================
with tab3:
    st.markdown("### 💼 Portfolio Actual")
    
    try:
        portfolio = PortfolioService()
        trades = asyncio.run(portfolio.get_open_trades())

        if trades:
            data = []
            for trade in trades:
                data.append({
                    "Token": trade.token_symbol,
                    "Entry Price ($)": f"${trade.entry_price:.2f}",
                    "Amount ($)": f"${trade.amount_usd:,.2f}",
                    "Status": trade.status,
                    "Entry Date": trade.entry_date.strftime("%Y-%m-%d %H:%M") if hasattr(trade.entry_date, 'strftime') else str(trade.entry_date)
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Resumen
            total_invested = sum(t.amount_usd for t in trades)
            st.metric("Total Invertido", f"${total_invested:,.2f}", delta=f"{len(trades)} posiciones")
        else:
            st.info("💼 Cartera vacía - No hay posiciones abiertas")
    except Exception as e:
        st.error(f"❌ Error cargando portfolio: {e}")

# ==================== TAB 4: INFO ====================
with tab4:
    st.markdown("### 📋 Información del Sistema")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔧 Configuración Técnica")
        st.write(f"**LLM Provider**: {settings.LLM_PROVIDER}")
        st.write(f"**LLM Model**: {settings.LLM_MODEL}")
        st.write(f"**LLM Base URL**: {settings.LLM_BASE_URL}")
        st.write(f"**Debug Mode**: {settings.DEBUG_MODE}")
    
    with col2:
        st.markdown("#### 📊 Parámetros de Trading")
        st.write(f"**TP**: {settings.TAKE_PROFIT_PCT}%")
        st.write(f"**SL**: {settings.STOP_LOSS_PCT}%")
        st.write(f"**Max Trades**: {settings.MAX_OPEN_TRADES}")
        st.write(f"**Max Drawdown**: {settings.MAX_DAILY_DRAWDOWN_PCT}%")
    
    st.markdown("---")
    
    st.markdown("#### 📖 Instrucciones")
    st.markdown("""
    **Chat AI**:
    - Pregunta sobre Smart Money flows
    - Pregunta sobre tu portfolio
    - Usa comandos: `/buy BTC 100` para compras simuladas
    
    **Smart Money**:
    - Ve los movimientos de smart money en tiempo real
    - Filtra por netflow y cantidad de traders
    
    **Portfolio**:
    - Monitor de posiciones abiertas
    - Track de entry prices y amounts
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 12px;'>
    <p>TradingIA © 2026 | Smart Money AI Agent with Ollama & Gemini Support</p>
    <p>Status: ✅ Running | Model: Qwen2.5-Coder:3b | DB: PostgreSQL</p>
</div>
""", unsafe_allow_html=True)