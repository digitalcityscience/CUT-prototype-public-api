from cut_api.config import settings
from cut_api.rate_limiter.limiter import RateLimitMiddleware

# from slowapi.util import get_remote_address


# def key_func(request: Request) -> str:
#     # TODO implement logic to use user_id as key_func
#     # if settings.limiter.limit_by_user:
#     #     return get_user_id(request)
#     return get_remote_address(request)


LIMITER = RateLimitMiddleware(
    storage_url=settings.cache.broker_url,
    default_rate_per_minute=settings.limiter.default_limit,
)
