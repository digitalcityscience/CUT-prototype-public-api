import base64
import json
import math
from io import BytesIO

import geopandas
import numpy as np
import rasterio.features
import rasterio.warp
from PIL import Image
from pyproj import Transformer
from shapely.geometry import Point, Polygon
from shapely.ops import transform

transformer_to_wgs = Transformer.from_crs(25832, 4326, always_xy=True).transform


def geojson_to_png(geojson, property_to_burn, resolution):
    geom_value_pairs = [
        (feature["geometry"], feature["properties"][property_to_burn])
        for feature in geojson["features"]
    ]
    png_nan_value = 255
    image_data = rasterio.features.rasterize(
        shapes=geom_value_pairs,
        fill=png_nan_value,
        dtype="float64",
        out_shape=resolution,
    )

    # map image data to ints from 0-1 (for png), idiso value has 8 steps, including 0
    # set NaN as 0
    image_data = [
        [x if x and not math.isnan(x) else png_nan_value for x in image_line]
        for image_line in image_data
    ]
    # create a np array from image data
    np_values = np.array(image_data, dtype="uint8")

    # create a pillow image, save it and convert to base64 string
    im = Image.fromarray(np_values)
    output_buffer = BytesIO()
    im.save(output_buffer, format="PNG")
    byte_data = output_buffer.getvalue()
    base64_bytes = base64.b64encode(byte_data)
    base64_string = base64_bytes.decode("utf-8")
    img_width, img_height = im.size

    return base64_string, img_width, img_height


def make_gdf_from_geojson(geojson, crs) -> geopandas.GeoDataFrame:
    gdf_cols = ["geometry"]

    # add all properties to gdf cols
    for property_key in geojson["features"][0]["properties"].keys():
        gdf_cols.append(property_key)

    return geopandas.GeoDataFrame.from_features(
        geojson["features"], crs=crs, columns=gdf_cols
    )


def reproject_coords(input_coords):
    output_epsg = 4326
    input_epsg = 25832

    # reproject all points in bulk
    transformer = Transformer.from_crs(input_epsg, output_epsg, always_xy=True)
    return transformer.itransform(input_coords)


# gets [x,y] of the south west corner of the bbox.
# might only work for european quadrant of the world
def get_south_west_corner_coords_gdf(gdf_bounds):
    left, bottom, right, top = gdf_bounds

    sw_point = transform(transformer_to_wgs, Point([left, bottom]))

    return list(sw_point.coords)


def get_bounds_coordinates_wgs(gdf_bounds):
    left, bottom, right, top = gdf_bounds
    bounds_utm = Polygon(
        [[left, top], [right, top], [right, bottom], [left, bottom], [left, top]]
    )

    bound_wgs = transform(transformer_to_wgs, bounds_utm)

    return list(bound_wgs.exterior.coords)


def convert_geojson_to_png(geojson):
    gdf = make_gdf_from_geojson(geojson, "EPSG:4326").to_crs("EPSG:25832")

    # get total bounds of original dataset (to position image on cityScope later)
    gdf_total_bounds = gdf.total_bounds

    bounds_coordinates = get_bounds_coordinates_wgs(gdf_total_bounds)
    south_west_corner_coords = get_south_west_corner_coords_gdf(gdf_total_bounds)

    #  Translate geometry to start at 0,0
    gdf.geometry = gdf.translate(-gdf_total_bounds[0], -gdf_total_bounds[1])

    # calculate resolution of picture
    gdf_total_bounds_translated = gdf.total_bounds

    resolution_x = math.ceil(
        gdf_total_bounds_translated[2] - gdf_total_bounds_translated[0]
    )
    resolution_y = math.ceil(
        gdf_total_bounds_translated[3] - gdf_total_bounds_translated[1]
    )

    # rasterize data
    base64_string, img_width, img_height = geojson_to_png(
        json.loads(gdf.to_json()), "idiso", [resolution_x, resolution_y]
    )

    return {
        "bbox_sw_corner": south_west_corner_coords,
        "img_width": img_width,
        "img_height": img_height,
        "bbox_coordinates": bounds_coordinates,
        "image_base64_string": base64_string,
    }