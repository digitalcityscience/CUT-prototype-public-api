from pydantic import BaseSettings, Field


class RateLimiter(BaseSettings):
    default_limit: int = Field(..., env="RATE_LIMITER_DEFAULT_LIMIT_PER_MINUTE")


class RedisConnectionConfig(BaseSettings):
    host: str = Field(..., env="REDIS_HOST")
    port: int = Field(..., env="REDIS_PORT")
    db: int = Field(..., env="REDIS_DB")
    username: str = Field(..., env="REDIS_USERNAME")
    password: str = Field(..., env="REDIS_PASSWORD")
    ssl: bool = Field(..., env="REDIS_SSL")


class CacheRedis(BaseSettings):
    connection: RedisConnectionConfig = Field(default_factory=RedisConnectionConfig)
    key_prefix: str = "noise_simulations"
    ttl_days: int = Field(30, env="REDIS_CACHE_TTL_DAYS")

    @property
    def redis_url(self) -> str:
        return f"redis://:{self.connection.password}@{self.connection.host}:{self.connection.port}"

    @property
    def broker_url(self) -> str:
        return f"{self.redis_url}/0"

    @property
    def result_backend(self) -> str:
        return f"{self.redis_url}/1"


class Auth(BaseSettings):
    token_signing_key: str = Field(..., env="TOKEN_SIGNING_KEY", min_length=1)


class Settings(BaseSettings):
    title: str = Field(..., env="APP_TITLE")
    description: str = Field(..., env="APP_DESCRIPTION")
    version: str = Field(..., env="APP_VERSION")
    debug: bool = Field(..., env="DEBUG")
    environment: str = Field(..., env="ENV")
    port: int = Field(..., env="APP_PORT")
    limiter: RateLimiter = Field(default_factory=RateLimiter)
    cache: CacheRedis = Field(default_factory=CacheRedis)
    auth: Auth = Field(default_factory=Auth)


settings = Settings()
