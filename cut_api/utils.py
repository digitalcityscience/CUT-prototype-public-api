import base64
import logging
import random
import string
from enum import Enum
from io import BytesIO

import bcrypt
import geopandas as gpd
import matplotlib.pyplot as plt
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


def geojson_to_rasterized_png(geojson):
    # Convert GeoJSON to GeoDataFrame
    gdf = gpd.GeoDataFrame.from_features(geojson["features"])

    # Create a figure for the plot
    fig, ax = plt.subplots(figsize=(10, 10))

    # Plot GeoDataFrame
    gdf.plot(ax=ax)

    # Remove axes for a clean image
    ax.set_axis_off()

    # Save the figure to a BytesIO object
    img_data = BytesIO()
    plt.savefig(img_data, format="png", bbox_inches="tight", pad_inches=0)
    plt.close(fig)

    # Read the image data back in as a raster
    img_data.seek(0)

    # Base64 encode the PNG
    base64_string = base64.b64encode(img_data.read()).decode()

    # Extract image size
    img_width, img_height = fig.canvas.get_width_height()

    # Extract bounding box coordinates
    bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
    south_west_corner_coords = (bounds[1], bounds[0])
    bounds_coordinates = {
        "minx": bounds[0],
        "miny": bounds[1],
        "maxx": bounds[2],
        "maxy": bounds[3],
    }

    return {
        "bbox_sw_corner": south_west_corner_coords,
        "img_width": img_width,
        "img_height": img_height,
        "bbox_coordinates": bounds_coordinates,
        "image_base64_string": base64_string,
    }


def to_camel_case(snake_str):
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def convert_keys_to_camel_case(input_dict):
    camel_case_dict = {}
    for key, value in input_dict.items():
        camel_case_key = to_camel_case(key)
        camel_case_dict[camel_case_key] = value
    return camel_case_dict
