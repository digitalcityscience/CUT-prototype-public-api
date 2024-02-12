from cut_api.config import settings

# If target server is not present in this routing table
# the API will return a 404 - Not Found
ROUTING_TABLE = {
    "noise": settings.external_apis.noise,
    "stormwater": settings.external_apis.water,
    "infrared": settings.external_apis.infrared,
    # "pedestrians": settings.external_apis.pedestrians,
}