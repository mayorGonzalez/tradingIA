import sys
import os
import streamlit as st
import asyncio

# Añadir el raíz al path para que funcione 'from app...'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

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
            
        st.divider()
        st.subheader("🛠️ Chat Ops")
        st.info("""
        **Comandos disponibles:**
        - `/buy <TKR> <USD>`
        - `/sell <TKR>`
        """)
        
        if st.toggle("Activar Logs en Vivo"):
            try:
                # En Windows, usar powershell para leer el archivo evita bloqueos de lectura
                import subprocess
                cmd = ["powershell", "-Command", "Get-Content -Path 'bot_final_check.log' -Tail 15"]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                if result.stdout:
                    st.code(result.stdout, language="text")
                else:
                    st.warning("El archivo de log existe pero está vacío.")
            except Exception as e:
                st.error(f"Error al leer logs: {str(e)}")

    # Layout Principal: Chat y Monitor
    col_chat, col_monitor = st.columns([2, 1])

    with col_chat:
        st.subheader("💬 AI Market Analyst")
        
        # Inicializar historial de chat
        if "messages" not in st.session_state or not st.session_state.messages:
            st.session_state.messages = [{
                "role": "assistant", 
                "content": "👋 ¡Hola! Soy tu analista de TradingAI. Puedo analizar datos de Nansen o ejecutar órdenes por ti (usa `/buy`). ¿En qué puedo ayudarte?"
            }]

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
