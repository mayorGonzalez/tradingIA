from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field

class Settings(BaseSettings):
    """
    Gestión Centralizada de Configuración.
    
    Carga variables de entorno y define los parámetros críticos de operación
    del bot, incluyendo límites de riesgo, pesos de scoring y credenciales.
    """

    # --- Credenciales de API (Seguridad Postural) ---
    # Se utiliza SecretStr para evitar la exposición accidental en logs o traces.
    NANSEN_API_KEY: SecretStr = SecretStr("dummy_key")
    NANSEN_BASE_URL: str = "https://api.nansen.ai/api/v1"
    
    BINANCE_API_KEY: SecretStr | None = None
    BINANCE_SECRET: SecretStr | None = None

    MEXC_API_KEY: SecretStr | None = None
    MEXC_SECRET: SecretStr | None = None

    # --- Configuración de IA (Analista de Mercado) ---
    # Point de integración con el modelo de lenguaje para análisis cualitativos.
    GEMINI_API_KEY: SecretStr = SecretStr("dummy_gemini_key")
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    GEMINI_MODEL: str = "gemini-2.0-flash" 
    
    # --- Configuración de LLM Local ---
    LLM_PROVIDER: str = Field(default="local")  # "local" o "gemini"
    LLM_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen2.5-coder:3b"

    # --- Parámetros de Operación (Lifecycle) ---
    # Controla la frecuencia del bucle principal de escaneo de Smart Money.
    POLLING_INTERVAL_MINUTES: int = 15
    DEBUG_MODE: bool = True

    # --- Filtros de Datos (Calidad de Señal) ---
    # Umbral mínimo de flujo de entrada en USD para considerar un token relevante.
    MIN_INFLOW_LIMIT: float = Field(default=100000.0)
    
    # --- Gestión de Riesgo (Risk Management) ---
    # Definición de targets de salida automática para proteger capital.
    TAKE_PROFIT_PCT: float = 5.0
    STOP_LOSS_PCT: float = -2.0
    
    # --- Circuit Breaker (Protección de Cartera) ---
    MAX_DAILY_DRAWDOWN_PCT: float = 5.0  # Parada si la cartera cae un 5% en un día
    MAX_OPEN_TRADES: int = 5            # Máximo de posiciones simultáneas
    
    # --- Pesos del Motor de Scoring (Alpha Generation) ---
    # Distribución de relevancia para las tres dimensiones del análisis técnico/on-chain.
    SCORE_WEIGHT_FLOW: float = 0.4          # Importancia del flujo neto (Netflow)
    SCORE_WEIGHT_CONCENTRATION: float = 0.3 # Importancia de la acumulación (Holdings)
    SCORE_WEIGHT_PERSISTENCE: float = 0.3   # Importancia de la actividad reciente (DEX)
    
    # --- Umbrales de Decisión (Filtro Final) ---
    # Mínimo score requerido para autorizar una ejecución de compra.
    MIN_SCORE_THRESHOLD: float = 20.0
    # Filtro anti-fomo: Evita entrar en activos con crecimientos explosivos inmediatos.
    MAX_PRICE_CHANGE_1H_PCT: float = 50.0
    
    # --- Notificaciones (Observabilidad) ---
    TELEGRAM_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()