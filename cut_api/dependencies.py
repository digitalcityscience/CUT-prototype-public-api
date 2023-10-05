from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from cut_api.config import settings


def key_func(request: Request) -> str:
    # TODO implement logic to use user_id as key_func
    # if settings.limiter.limit_by_user:
    #     return get_user_id(request)
    return get_remote_address(request)


LIMITER = Limiter(
    key_func=key_func,
    default_limits=[settings.limiter.default_limit],
    storage_uri=settings.cache.broker_url,
    in_memory_fallback_enabled=True,
)
