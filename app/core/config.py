from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field

class Settings(BaseSettings):
    # Usamos None como valor por defecto para que Mypy no pida argumentos
    # pero mantenemos el tipo SecretStr para seguridad.
    NANSEN_API_KEY: SecretStr = SecretStr("dummy_key")
    NANSEN_BASE_URL: str = "https://api.nansen.ai/api/v1"
    
    BINANCE_API_KEY: SecretStr | None = None
    BINANCE_SECRET: SecretStr | None = None  
    
    POLLING_INTERVAL_MINUTES: int = 15
    DEBUG_MODE: bool = False

    MIN_INFLOW_LIMIT: float = Field(default=100000.0)
    
    TELEGRAM_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    model_config = SettingsConfigDict(env_file=".env")

# Ahora Mypy no se quejará aquí
settings = Settings()