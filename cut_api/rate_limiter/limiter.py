from typing import Awaitable, Callable

from limits import RateLimitItem, RateLimitItemPerMinute, storage, strategies
from starlette.requests import Request


# Default limiter limits requets by IP, if requests need to be
# limited by user_id, the identifier callback func needs to be altered
async def _default_identifier(request: Request) -> str:
    return request.client.host


class RateLimitMiddleware:
    def __init__(
        self,
        storage_url: str,
        default_rate_per_minute: int,
        identifier: Callable[[Request], Awaitable[str]] = _default_identifier,
    ):
        self.identifier = identifier
        self.limiter_storage = storage.RedisStorage(storage_url)
        self.throttler = strategies.MovingWindowRateLimiter(self.limiter_storage)
        self.default_rate_per_minute = default_rate_per_minute

    async def can_pass_request(
        self, request: Request, rate_per_minute: int = None
    ) -> bool:
        if not rate_per_minute:
            rate_per_minute = self.default_rate_per_minute
        key = await self.identifier(request)
        return self._hit(key=key, rate_per_minute=rate_per_minute)

    def _rate_limit_item_for(self, rate_per_minute: int) -> RateLimitItem:
        """
        Returns the rate of requests for a specific model

        :param rate_per_minute: the number of request per minute to allow
        :return: `RateLimitItem` object initiated with a rate limit that matched the model
        """
        return RateLimitItemPerMinute(rate_per_minute)

    def _hit(self, key: str, rate_per_minute: int, cost: int = 1) -> bool:
        """
        Hits the throttler and returns `true` if a request can be passed and `false` if it needs to be blocked
        :param key: the key that identifies the client that needs to be throttled
        :param rate_per_minute: the number of request per minute to allow
        :param cost: the cost of the request in the time window.
        :return: returns `true` if a request can be passed and `false` if it needs to be blocked
        """
        item = self._rate_limit_item_for(rate_per_minute=rate_per_minute)
        return self.throttler.hit(item, key, cost=cost)
