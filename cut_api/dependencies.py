from fastapi import Request

from cut_api.auth.tokens import ApiUser, AuthErrorMissingToken, TokenManager
from cut_api.config import settings
from cut_api.rate_limiter.limiter import RateLimitMiddleware

LIMITER = RateLimitMiddleware(
    storage_url=settings.cache.broker_url,
    default_rate_per_minute=settings.limiter.default_limit,
)


def authorise_request(request: Request) -> ApiUser:
    if auth_header := request.headers.get("authorization"):
        token = auth_header.replace("Bearer ", "")
        _ = TokenManager(settings.auth.token_signing_key).verify_access_token(token)
        return token
    raise AuthErrorMissingToken
