# 📈 TradingIA — Smart Money AI Agent

Agente autónomo de trading que cruza datos on-chain de **Nansen (Smart Money)** con modelos de **IA (Google Gemini)** para detectar y ejecutar oportunidades de alta probabilidad en criptoactivos.

## 🚀 Características Principales

- **Scoring Multidimensional**: Cruza `Netflow`, `Holdings` y `DEX Trades` de Nansen para filtrar el ruido.
- **AI Analyst**: Dashboard integrado con Streamlit y Gemini 2.0 para consultar el porqué de cada movimiento.
- **Riesgo Controlado**: Gestión automática de órdenes con `Stop Loss` y `Take Profit` parametrizables.
- **Arquitectura Async**: Construido sobre `Python 3.12` con soporte asíncrono para consumo de APIs y Base de Datos local SQLite.

## 🛠️ Requisitos Previos

- Python 3.12+
- `uv` instalado (Recomendado como gestor de paquetes de Python)

## ⚙️ Instalación y Configuración Inicial

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/mayorGonzalez/tradingIA.git
   cd tradingIA
   ```

2. **Crear el entorno virtual e instalar dependencias:**
   Usamos `uv` para una gestión rápida y robusta del entorno:
   ```bash
   uv sync
   ```
   *Esto creará el directorio `.venv` automáticamente y sincronizará las dependencias marcadas en el `pyproject.toml` y `uv.lock`.*

3. **Activar el entorno virtual:**
   ```bash
   # En Windows:
   .venv\Scripts\activate
   # En macOS/Linux:
   source .venv/bin/activate
   ```

4. **Configurar variables de entorno:**
   Crea un archivo `.env` en la raíz del proyecto (basado en un `.env.example` si existe o usando la siguiente plantilla):
   ```env
   NANSEN_API_KEY="tu_api_key_de_nansen"
   GEMINI_API_KEY="tu_api_key_de_google_ai"
   BINANCE_API_KEY="tu_key"
   BINANCE_SECRET="tu_secret"
   DEBUG_MODE=True  # Usa el mock de Nansen para pruebas locales
   MIN_INFLOW_LIMIT=25000.0
   ```

## 🖥️ Uso

Asegúrate de tener el entorno virtual activo antes de ejecutar cualquier comando.

### Ejecutar el Dashboard (Streamlit UI)
```bash
streamlit run app/ui/dashboard.py
```

### Ejecutar el Bot Principal (Core Loop)
```bash
python -m app.main
```

### Ejecutar Pruebas (Tests)
```bash
pytest
```

## 🏗️ Estructura del Proyecto

El proyecto está organizado en una estructura limpia y orientada a dominios:

- `app/core/`: Configuración global, utilidades transversales (ej. reintentos, logs).
- `app/services/`: Lógica de negocio core (Nansen Client, Signal Engine, AI Analyst).
- `app/infraestructure/`: Adaptadores externos (Exchange (Binance), Database SQLite).
- `app/models/`: Contratos de datos usando Pydantic y modelos ORM de la base de datos.
- `app/ui/`: Interfaz gráfica interactiva desarrollada con Streamlit.
- `tests/`: Baterías de pruebas unitarias y de integración del flujo.

## 📝 Resiliencia y Manejo de Errores

El sistema incorpora utilidades robustas de gestión de red, mediante un decorador `@retry_async` personalizado en `app.core.utils` que administra y reintenta tras:
- `httpx.TimeoutException`
- `httpx.HTTPStatusError` (Ej. Límites de tasa o Rate Limits)
- Errores de red y paradas técnicas del Exchange vía `ccxt`.

---

*Disclaimer: Este software es para fines educativos. El trading de criptoactivos conlleva un alto riesgo de pérdida de capital.*
