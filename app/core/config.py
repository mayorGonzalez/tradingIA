import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field
from dotenv import load_dotenv
load_dotenv()


class Settings(BaseSettings):
    """
    Gestión Centralizada de Configuración.

    Carga variables de entorno y define los parámetros críticos de operación
    del bot, incluyendo límites de riesgo, pesos de scoring y credenciales.

    IMPORTANTE: Ningún secreto debe ser hardcodeado aquí.
    Usar siempre variables de entorno definidas en el archivo .env
    """

    # --- Credenciales de API (Seguridad Postural) ---
    # Se utiliza SecretStr para evitar la exposición accidental en logs o traces.
    # Valor por defecto vacío: DEBE ser sobreescrito por variable de entorno NANSEN_API_KEY
    NANSEN_API_KEY: SecretStr = Field(default=SecretStr(""), description="API Key de Nansen (requiere .env)")
    NANSEN_BASE_URL: str = "https://api.nansen.ai/api/v1"

    BINANCE_API_KEY: SecretStr | None = None
    BINANCE_SECRET: SecretStr | None = None

    MEXC_API_KEY: SecretStr | None = None
    MEXC_SECRET: SecretStr | None = None

    # --- Configuración de IA (Analista de Mercado) ---
    # GEMINI_API_KEY: DEBE ser sobreescrito por variable de entorno GEMINI_API_KEY
    GEMINI_API_KEY: SecretStr = Field(default=SecretStr(""), description="API Key de Gemini (requiere .env)")
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    GEMINI_MODEL: str = "gemini-1.5-pro"

    # --- Configuración de LLM Local ---
    LLM_PROVIDER: str = Field(default="gemini")  # "local" o "gemini"
    LLM_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen2.5-coder:3b"

    # --- Parámetros de Operación (Lifecycle) ---
    # Controla la frecuencia del bucle principal de escaneo de Smart Money.
    POLLING_INTERVAL_MINUTES: int = 1
    DEBUG_MODE: bool = True
    PAPER_TRADING: bool = True

    # --- Filtros de Datos (Calidad de Señal) ---
    # Umbral mínimo de flujo de entrada en USD para considerar un token relevante.
    MIN_INFLOW_LIMIT: float = Field(default=14_000.0)

    # --- Gestión de Riesgo (Risk Management) ---
    # Definición de targets de salida automática para proteger capital.
    TAKE_PROFIT_PCT: float = 5.0
    STOP_LOSS_PCT: float = -2.0

    # Límites absolutos de tamaño de posición (en USD)
    MIN_POSITION_SIZE_USD: float = 10.0    # Mínimo para cubrir fees del exchange
    MAX_POSITION_SIZE_USD: float = 500.0   # Máximo absoluto por trade independiente del balance

    # Trailing stop: activa si ganancias superan este % y luego retrocede TRAIL_STOP_DISTANCE_PCT
    TRAILING_STOP_TRIGGER_PCT: float = 3.0   # Activar trailing cuando PnL >= 3%
    TRAILING_STOP_DISTANCE_PCT: float = 1.5  # Distancia del trailing desde el máximo registrado

    # --- Circuit Breaker (Protección de Cartera) ---
    MAX_DAILY_DRAWDOWN_PCT: float = 5.0   # Parada si la cartera cae un 5% en un día
    MAX_OPEN_TRADES: int = 5              # Máximo de posiciones simultáneas abertas
    CIRCUIT_BREAK_DURATION_MINUTES: int = 60  # Duración del bloqueo tras activar el breaker

    # --- Pesos del Motor de Scoring (Alpha Generation) ---
    # Distribución de relevancia para las tres dimensiones del análisis técnico/on-chain.
    SCORE_WEIGHT_FLOW: float = 0.3           # Importancia del flujo neto (Netflow)
    SCORE_WEIGHT_CONCENTRATION: float = 0.5  # Importancia de la acumulación (Holdings)
    SCORE_WEIGHT_PERSISTENCE: float = 0.2    # Importancia de la actividad reciente (DEX)

    # --- Umbrales de Decisión (Filtro Final) ---
    # Mínimo score requerido para autorizar una ejecución de compra.
    # PRODUCCIÓN: Usar ≥ 50. En desarrollo/debug puede bajar a 30.
    MIN_SCORE_THRESHOLD: float = 50.0
    # Filtro anti-fomo: Evita entrar en activos con crecimientos explosivos inmediatos.
    MAX_PRICE_CHANGE_1H_PCT: float = 50.0

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://trading_user:trading_pass@postgres:5432/tradingia_db"
    )

    # --- Notificaciones (Observabilidad) ---
    TELEGRAM_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()