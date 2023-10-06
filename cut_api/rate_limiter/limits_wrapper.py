# # limits_wrapper.py

# from limits import RateLimitItem, RateLimitItemPerMinute, storage, strategies

# from cut_api.config import settings

# REDIS_URL: str = "redis://localhost:6379/0"
# storage = storage.RedisStorage(REDIS_URL)
# throttler = strategies.MovingWindowRateLimiter(storage)

# """
#     This component is used as a wrapper for `limits` so we won't use its api directly in the throttler class.
# """


# def hit(key: str, rate_per_minute: int, cost: int = 1) -> bool:
#     """
#     Hits the throttler and returns `true` if a request can be passed and `false` if it needs to be blocked
#     :param key: the key that identifies the client that needs to be throttled
#     :param rate_per_minute: the number of request per minute to allow
#     :param cost: the cost of the request in the time window.
#     :return: returns `true` if a request can be passed and `false` if it needs to be blocked
#     """
#     item = rate_limit_item_for(rate_per_minute=rate_per_minute)
#     return throttler.hit(item, key, cost=cost)


# def rate_limit_item_for(rate_per_minute: int) -> RateLimitItem:
#     """
#     Returns the rate of requests for a specific model

#     :param rate_per_minute: the number of request per minute to allow
#     :return: `RateLimitItem` object initiated with a rate limit that matched the model
#     """
#     return RateLimitItemPerMinute(rate_per_minute)
