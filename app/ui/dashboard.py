import sys
from pathlib import Path

# Añadimos la raíz del proyecto al PATH de Python
root_path = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root_path))

import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import plotly.express as px  # type: ignore
import asyncio
from datetime import datetime
from typing import List, Union, Any

from app.core.config import settings
from app.services.portfolio_service import PortfolioService
from app.infraestructure.exchange_client import ExchangeClient
from app.services.nansen_client import NansenClient
from app.services.nansen_mock import NansenMockClient
from app.services.ai_analyst import AIAnalyst
from app.models.db_models import Trade, TradeStatus

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="tradingAI Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0a0d14; }

    /* Chat container */
    .chat-wrapper {
        background: linear-gradient(135deg, #0e1421 0%, #121828 100%);
        border: 1px solid #1e2d45;
        border-radius: 16px;
        padding: 20px;
        margin-top: 8px;
    }

    /* Burbujas de mensaje */
    .msg-user {
        background: linear-gradient(135deg, #1a3a5c, #1e4976);
        border-radius: 12px 12px 2px 12px;
        padding: 12px 16px;
        margin: 8px 0 8px 50px;
        color: #ffffff;
        font-size: 0.92rem;
        border-left: 3px solid #00aaff;
    }
    .msg-assistant {
        background: linear-gradient(135deg, #111827, #1a2235);
        border-radius: 12px 12px 12px 2px;
        padding: 12px 16px;
        margin: 8px 50px 8px 0;
        color: #d1d5db;
        font-size: 0.92rem;
        border-left: 3px solid #00ff9d;
    }
    .msg-label-user {
        font-size: 0.7rem; color: #4a90d9; font-weight: 600;
        margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.05em;
    }
    .msg-label-bot {
        font-size: 0.7rem; color: #00cc7a; font-weight: 600;
        margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.05em;
    }

    /* Métricas */
    [data-testid="metric-container"] {
        background: #0f1724;
        border: 1px solid #1e2d45;
        border-radius: 10px;
        padding: 12px;
    }

    .status-online { color: #00ff9d; font-weight: bold; font-size: 0.9rem; }
    .status-offline { color: #ff4b6e; font-weight: bold; font-size: 0.9rem; }
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def run_async(coro: Any) -> Any:
    return asyncio.run(coro)

@st.cache_resource
def get_services() -> tuple:
    portfolio = PortfolioService()
    exchange = ExchangeClient()
    nansen = NansenMockClient() if settings.DEBUG_MODE else NansenClient()
    analyst = AIAnalyst()
    return portfolio, exchange, nansen, analyst

portfolio_service, exchange_client, nansen_client, ai_analyst = get_services()


# ─────────────────────────────────────────────
# DATOS DE TABS
# ─────────────────────────────────────────────
async def load_nansen_data() -> pd.DataFrame:
    raw = await nansen_client.get_smart_money_flows()
    rows = []
    for f in raw.data:
        rows.append({
            "Token": f.token_symbol,
            "Netflow 24h ($)": f.net_flow_usd,
            "Netflow 7d ($)": f.net_flow_7d_usd,
            "Traders": f.trader_count,
            "Mcap ($)": f.market_cap_usd or 0,
            "Edad (días)": f.token_age_days or 0,
            "Sectores": ", ".join(f.token_sectors) if f.token_sectors else "-",
        })
    df = pd.DataFrame(rows)
    return df.sort_values("Netflow 24h ($)", ascending=False)


async def load_history() -> pd.DataFrame:
    trades = await portfolio_service.get_all_trades()
    return pd.DataFrame([{
        "Fecha": t.created_at.strftime("%Y-%m-%d %H:%M"),
        "Symbol": t.token_symbol,
        "Entry": f"${t.entry_price:,.4f}",
        "Exit": f"${t.exit_price:,.4f}" if t.exit_price else "-",
        "Status": "🟢 OPEN" if t.status == "OPEN" else "🔴 CLOSED",
        "Capital": f"${t.amount_usd:,.2f}"
    } for t in trades])


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.title("🤖 tradingAI Control")
    st.markdown(
        f"Estado: <span class='status-online'>● ONLINE</span>" if not settings.DEBUG_MODE
        else "Estado: <span class='status-offline'>● DEBUG MODE</span>",
        unsafe_allow_html=True
    )
    st.markdown(f"Modelo IA: `{settings.GEMINI_MODEL}`")
    st.divider()

    st.subheader("🏦 Wallet")
    try:
        balance = run_async(exchange_client.get_balance())
        usdt_val = balance.get('USDT', 0.0) if balance else 0.0
        st.metric("Balance USDT", f"${usdt_val:,.2f}")
    except Exception:
        st.metric("Balance USDT", "N/A")

    st.divider()
    st.subheader("⚙️ Config")
    st.caption(f"Min inflow: ${settings.MIN_INFLOW_LIMIT:,.0f}")
    st.caption(f"Score umbral: {settings.MIN_SCORE_THRESHOLD}")
    st.caption(f"Take Profit: +{settings.TAKE_PROFIT_PCT}%")
    st.caption(f"Stop Loss: {settings.STOP_LOSS_PCT}%")

    st.divider()
    if st.button("🔄 Limpiar Chat", width='stretch'):
        st.session_state.chat_history = []
        st.rerun()

# ─────────────────────────────────────────────
# MAIN ─ TABS
# ─────────────────────────────────────────────
tab_nansen, tab_historial = st.tabs(["📊 Smart Money Flows", "📜 Historial Trades"])

with tab_nansen:
    st.subheader("Top Smart Money Flows (Ethereum · 24h)")
    with st.spinner("Cargando datos Nansen..."):
        nansen_df = run_async(load_nansen_data())

    if not nansen_df.empty:
        col1, col2, col3 = st.columns(3)
        positives = nansen_df[nansen_df["Netflow 24h ($)"] > 0]
        col1.metric("🚀 Tokens con inflow", len(positives))
        col2.metric("📉 Con outflow", len(nansen_df) - len(positives))
        col3.metric("💰 Mayor inflow", f"${nansen_df['Netflow 24h ($)'].max():,.0f}")

        fig = px.bar(
            nansen_df.head(12),
            x="Token", y="Netflow 24h ($)",
            color="Netflow 24h ($)",
            color_continuous_scale=["#ff4b6e", "#1a1a2e", "#00ff9d"],
            color_continuous_midpoint=0,
            title="Netflow por Token — Smart Money (24h)",
            template="plotly_dark",
            height=380,
        )
        fig.update_layout(
            paper_bgcolor="#0a0d14",
            plot_bgcolor="#0a0d14",
            showlegend=False,
        )
        st.plotly_chart(fig, width='stretch')
        st.dataframe(nansen_df, width='stretch', hide_index=True)
    else:
        st.warning("Sin datos de Nansen disponibles.")

with tab_historial:
    st.subheader("Historial de Operaciones")
    df_history = run_async(load_history())
    if not df_history.empty:
        st.dataframe(df_history, width='stretch', hide_index=True)
    else:
        st.info("No hay operaciones registradas todavía.")

# ─────────────────────────────────────────────
# SECCIÓN DE CHAT TIPO GEMINI
# ─────────────────────────────────────────────
st.divider()
st.subheader("💬 Consulta a tu Agente IA")
st.caption(
    f"Responde con datos reales de Nansen y tu cartera. "
    f"Modelo: **{settings.GEMINI_MODEL}** (Zhipu AI)"
)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar historial completo con los componentes nativos de Streamlit
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input de chat fijado al fondo de la pantalla
if prompt := st.chat_input("¿Qué quieres saber sobre el mercado o tus trades?"):

    # Mostrar la pregunta del usuario inmediatamente
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Obtener y mostrar la respuesta del analista
    with st.chat_message("assistant"):
        analyst = AIAnalyst()
        with st.spinner("Analizando datos on-chain..."):
            # Pasamos el historial para que gemini mantenga el contexto de la conversación
            response = analyst.ask_question(
                prompt=prompt,
                history=st.session_state.messages[:-1],  # Todo menos el mensaje actual
            )
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# ─────────────────────────────────────────────
# PIE DE PÁGINA
# ─────────────────────────────────────────────
st.caption(
    f"Última actualización: {datetime.now().strftime('%H:%M:%S')} · "
    f"tradingAI v2.0 · Smart Money Engine"
)
