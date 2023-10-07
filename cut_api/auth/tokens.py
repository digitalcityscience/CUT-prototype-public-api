import logging
from datetime import datetime

import jwt

from cut_api.common.models import BaseModelStrict

logger = logging.getLogger(__name__)


class AuthError(Exception):
    def __init__(self):
        super().__init__()
        self.message = ""


class AuthErrorInvalidToken(AuthError):
    def __init__(self):
        super().__init__()
        self.message = "Invalid token"


class AuthErrorExpiredToken(AuthError):
    def __init__(self):
        super().__init__()
        self.message = "Token is expired"


class AuthErrorMissingToken(AuthError):
    def __init__(self):
        super().__init__()
        self.message = "Header missing bearer token"


class AuthErrorNotAnAccessToken(AuthError):
    def __init__(self):
        super().__init__()
        self.message = "Refresh tokens cannot be used to authenticate."


class ApiUser(BaseModelStrict):
    id: str
    email: str
    restricted: bool
    created_at: datetime


class VerifiedTokenPayload(BaseModelStrict):
    user: ApiUser
    iat: int  # Issued At
    exp: int  # Expiration
    type: str


class TokenManager:
    def __init__(
        self,
        signing_key: str,
    ):
        self.signing_algorithm = "HS256"
        self.signing_key = signing_key

    def _verify_token(self, token: str) -> VerifiedTokenPayload:
        try:
            return VerifiedTokenPayload(
                **jwt.decode(
                    token,
                    self.signing_key,
                    algorithms=[self.signing_algorithm],
                )
            )
        except jwt.ExpiredSignatureError as error:
            logger.error("Token verification failed: Token expired.")
            raise AuthErrorExpiredToken from error
        except Exception as error:
            logger.error("Token verification failed: Invalid token.")
            raise AuthErrorInvalidToken from error

    def verify_access_token(self, token: str) -> ApiUser:
        verified_token = self._verify_token(token)
        if verified_token.type != "access":
            logger.error("Token verification failed: Not an access token.")
            raise AuthErrorNotAnAccessToken
        return verified_token.user
