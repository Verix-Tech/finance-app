import logging

from config.config import SQLDBConfig
from bot.core.cache import user_cache

logger = logging.getLogger(__name__)

def check_user_exists(user_id: int) -> bool:
    """Verifica se o usuário existe, usando cache para evitar chamadas repetidas à API."""
    user_id_str = str(user_id)
    cached_result = user_cache.get(user_id_str)
    if cached_result is not None:
        logger.info(f"User {user_id} existence status found in cache: {cached_result}")
        return cached_result

    logger.info(f"User {user_id} not in cache, checking API")
    response = SQLDBConfig().send_request(
        endpoint="/users/exists",
        endpoint_var="",
        method="post",
        params={"platform_id": user_id_str}
    )
    exists = response.status_code not in (502, 404)
    user_cache.set(user_id_str, exists)
    logger.info(f"Cached user {user_id} existence status: {exists}")
    return exists 