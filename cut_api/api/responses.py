from typing import Optional

from fastapi import status
from pydantic import BaseModel


class UserApiErrorResponse(BaseModel):
    message: str
    details: Optional[dict]

    @classmethod
    def internal_error(cls):
        # don't provide internal error details to external clients
        return cls(message="internal error")


def make_responses_dict(update_dict: dict) -> dict:
    return {
        status.HTTP_400_BAD_REQUEST: {
            "model": UserApiErrorResponse,
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": UserApiErrorResponse,
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": UserApiErrorResponse,
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": UserApiErrorResponse,
        },
    } | update_dict
