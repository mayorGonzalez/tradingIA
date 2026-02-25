import asyncio
import httpx
import ccxt
from tenacity import (  # type: ignore
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from loguru import logger
from typing import Any, Callable, TypeVar

F = TypeVar('F', bound=Callable[..., Any])

def retry_async(
    max_attempts: int = 5,
    min_wait: int = 1,
    max_wait: int = 10
) -> Any:
    """
    Decorador para reintentar funciones asíncronas con Exponential Backoff.
    Especialmente diseñado para errores de red en APIs y Exchanges.
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=min_wait, min=min_wait, max=max_wait),
        retry=retry_if_exception_type((httpx.RequestError, ccxt.NetworkError)),
        before_sleep=before_sleep_log(logger, "WARNING"),  # type: ignore[arg-type]
        reraise=True
    ) # type: ignore
