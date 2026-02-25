from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field

class Settings(BaseSettings):
    # Usamos None como valor por defecto para que Mypy no pida argumentos
    # pero mantenemos el tipo SecretStr para seguridad.
    NANSEN_API_KEY: SecretStr = SecretStr("dummy_key")
    NANSEN_BASE_URL: str = "https://api.nansen.ai/api/v1"
    
    BINANCE_API_KEY: SecretStr | None = None
    BINANCE_SECRET: SecretStr | None = None

    # Google Gemini — OpenAI-compatible endpoint
    GEMINI_API_KEY: SecretStr = SecretStr("dummy_gemini_key")
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    GEMINI_MODEL: str = "gemini-2.0-flash"  # Cambiar a 'gemini-1.5-pro' para más capacidad
    
    POLLING_INTERVAL_MINUTES: int = 15
    DEBUG_MODE: bool = False

    MIN_INFLOW_LIMIT: float = Field(default=100000.0)
    
    TAKE_PROFIT_PCT: float = 5.0
    STOP_LOSS_PCT: float = -2.0
    
    # Scoring Weights
    SCORE_WEIGHT_FLOW: float = 0.4
    SCORE_WEIGHT_CONCENTRATION: float = 0.3
    SCORE_WEIGHT_PERSISTENCE: float = 0.3
    
    # Decision Thresholds
    MIN_SCORE_THRESHOLD: float = 75.0
    MAX_PRICE_CHANGE_1H_PCT: float = 15.0
    
    TELEGRAM_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    model_config = SettingsConfigDict(env_file=".env")

# Ahora Mypy no se quejará aquí
settings = Settings()