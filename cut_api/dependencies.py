from cut_api.auth.tokens import ApiUser, AuthErrorMissingToken, TokenManager
from cut_api.config import settings
from cut_api.rate_limiter.limiter import RateLimitMiddleware

LIMITER = RateLimitMiddleware(
    storage_url=settings.cache.broker_url,
    default_rate_per_minute=settings.limiter.default_limit,
)


def authorise_request(
    token: str,
) -> ApiUser:
    # TODO remove this condition, use only during development
    # from datetime import datetime
    # if settings.environment == "LOCALDEV":
    #     return ApiUserInToken(
    #         id="local_dev_user",
    #         email="local_dev@user.de",
    #         restricted=False,
    #         created_at=datetime.now(),
    #     )

    if not token:
        raise AuthErrorMissingToken
    if user_in_token := TokenManager(
        settings.auth.token_signing_key
    ).verify_access_token(token):
        return user_in_token
