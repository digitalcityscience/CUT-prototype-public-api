import logging
import random
import string
from enum import Enum
from io import BytesIO

import bcrypt
import geopandas as gpd
from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)


def enum_to_list(enum_class: Enum) -> list[str]:
    return [member.value for member in enum_class]


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def generate_safe_password(length=15):
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


async def validate_geojson(file: UploadFile) -> gpd.GeoDataFrame:
    if file.filename.split(".")[-1] != "json":
        logger.error("File extension must be JSON.")
        raise HTTPException(status_code=422, detail="File extension must be JSON.")
    contents = await file.read()
    try:
        gdf = gpd.read_file(BytesIO(contents))
        return gdf.to_json()
    except Exception as e:
        logger.error("File is not a valid GeoJSON.", exc_info=True)
        raise HTTPException(
            status_code=422, detail="File is not a valid GeoJSON."
        ) from e
