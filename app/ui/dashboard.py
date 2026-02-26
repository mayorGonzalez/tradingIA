import streamlit as st
import asyncio
from loguru import logger
from app.services.ai_analyst import AIAnalyst
from app.core.config import settings

# Configuración de página con estética Premium
st.set_page_config(
    page_title="TradingAI Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo personalizado (CSS Inyectado)
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .stChatFloatingInputContainer {
        bottom: 20px;
    }
    .reportview-container .main .block-container {
        padding-top: 2rem;
    }
    h1 {
        color: #00d4ff;
        font-family: 'Inter', sans-serif;
        font-weight: 800;
    }
    .stMetric {
        background: rgba(255, 255, 255, 0.05);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.title("🚀 TradingAI Intelligence")
    
    # Sidebar con estado del bot
    with st.sidebar:
        st.header("⚙️ Configuración")
        st.status("Bot Online", state="running" if not settings.DEBUG_MODE else "error")
        st.divider()
        st.metric("Min Inflow Limit", f"${settings.MIN_INFLOW_LIMIT:,.0f}")
        st.metric("Target ROI", f"{settings.TAKE_PROFIT_PCT}%")
        st.metric("Stop Loss", f"{settings.STOP_LOSS_PCT}%")
        
        if st.button("🔄 Refrescar Datos"):
            st.rerun()

    # Layout Principal: Chat y Monitor
    col_chat, col_monitor = st.columns([2, 1])

    with col_chat:
        st.subheader("💬 AI Market Analyst")
        
        # Inicializar historial de chat
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Mostrar mensajes previos
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Input de chat
        if prompt := st.chat_input("Pregúntame sobre el mercado o Smart Money..."):
            # Mostrar mensaje del usuario
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Generar respuesta de la IA
            with st.chat_message("assistant"):
                with st.spinner("Analizando datos on-chain..."):
                    analyst = AIAnalyst()
                    # Usamos el método ask_question que ya maneja el loop de asyncio para Streamlit
                    response = analyst.ask_question(prompt, st.session_state.messages)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

    with col_monitor:
        st.subheader("📊 Live Monitor")
        # Aquí podrían ir tablas de Nansen o posiciones abiertas
        st.info("Conectando con Nansen API...")
        
        # Simulación de monitor (en v2.0 traeremos datos reales aquí)
        st.markdown("### 🔍 Top Smart Money Inflows")
        st.code("Cargando flujos de Ethereum...", language="text")

if __name__ == "__main__":
    main()
