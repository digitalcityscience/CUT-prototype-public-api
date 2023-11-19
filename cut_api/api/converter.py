import base64
from io import BytesIO

import geopandas as gpd
import matplotlib.pyplot as plt


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
