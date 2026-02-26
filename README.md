# 📈 TradingIA — Smart Money AI Agent

Agente autónomo de trading que cruza datos on-chain de **Nansen (Smart Money)** con modelos de **IA (Google Gemini)** para detectar y ejecutar oportunidades de alta probabilidad en criptoactivos.

## 🚀 Características Principales

- **Scoring Multidimensional**: Cruza `Netflow`, `Holdings` y `DEX Trades` de Nansen para filtrar el ruido.
- **AI Analyst**: Dashboard integrado con Streamlit y Gemini 2.0 para consultar el porqué de cada movimiento.
- **Riesgo Controlado**: Gestión automática de órdenes con `Stop Loss` y `Take Profit` parametrizables.
- **Arquitectura Async**: Construido sobre `Python 3.12` con `httpx`, `ccxt` y `SQLAlchemy` asíncronos.

## 🛠️ Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/mayorGonzalez/tradingIA.git
   cd tradingIA
   ```

2. **Crear entorno virtual e instalar dependencias:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # En Windows: .venv\Scripts\activate
   pip install -r requirements.txt  # O usa uv: uv sync
   ```

3. **Configurar variables de entorno:**
   Crea un archivo `.env` basado en la siguiente plantilla:
   ```env
   NANSEN_API_KEY="tu_api_key_de_nansen"
   GEMINI_API_KEY="tu_api_key_de_google_ai"
   BINANCE_API_KEY="tu_key"
   BINANCE_SECRET="tu_secret"
   DEBUG_MODE=True  # Usa el mock de Nansen para desarrollo
   MIN_INFLOW_LIMIT=25000.0
   ```

## 🖥️ Uso

### Ejecutar el Dashboard (Streamlit)
```bash
streamlit run app/ui/dashboard.py
```

### Ejecutar el Bot Principal (Core Loop)
```bash
python -m app.main
```

## 🏗️ Estructura del Proyecto

- `app/core/`: Configuración global y utilidades de reintento.
- `app/services/`: Lógica de negocio (Client Nansen, Signal Engine, AI Analyst).
- `app/infraestructure/`: Adaptadores para Exchange (Binance) y Base de Datos.
- `app/models/`: Contratos de datos con Pydantic y esquemas de DB.
- `app/ui/`: Interfaz de usuario con Streamlit.

## 📝 Documentación de Resiliencia

El sistema utiliza un decorador `@retry_async` personalizado que gestiona:
- `httpx.TimeoutException`
- `httpx.HTTPStatusError` (Rate limits automáticos)
- `ccxt.NetworkError`

---
*Disclaimer: Este software es para fines educativos. El trading de criptoactivos conlleva un alto riesgo de pérdida de capital.*
