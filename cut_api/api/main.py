import json
import logging

import httpx
import requests
import uvicorn
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cut_api.api.responses import CutApiErrorResponse
from cut_api.auth.tokens import AuthError
from cut_api.config import settings
from cut_api.dependencies import LIMITER, authorise_request
from cut_api.logs import setup_logging
from cut_api.utils import geojson_to_rasterized_png

setup_logging()

logger = logging.getLogger(__name__)


app = FastAPI(
    title=settings.title,
    descriprition=settings.description,
    version=settings.version,
)

# TODO replace origins
origins = [
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health_check", tags=["ROOT"])
async def health_check():
    return "ok"


VALID_RESULT_FORMATS = ["png", "geojson"]


# If target server is not present in this routing table
# the API will return a 404 - Not Found
ROUTING_TABLE = {
    "noise": settings.external_apis.noise,
    "stormwater": settings.external_apis.water,
    "wind": settings.external_apis.wind,
    "pedestrians": settings.external_apis.pedestrians,
}

# REQUEST_EVENTS_URL = f"{settings.external_apis.resources}/request_events"


# TODO jobs/{job_id}/results
# TODO validate endpoint
# TODO pygeo api
# TODO: implement OCG standards: https://app.swaggerhub.com/apis/OGC/ogcapi-processes-1-example-1/1.0.0#/
# TODO remove user from here and investigate how to implement clipping
# cityPyo_user = ""

# noise_result_geojson = clip_gdf_to_project_area(noise_result_geojson, cityPyo_user)
# print("Result geojson save in ", noise_result_geojson)


async def register_request_event(
    token: str,
    endpoint: str,
    request_logging_url: str = settings.request_logging_endpoint,
) -> None:
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        logger.info("Sending request to register request_event...")
        response = requests.post(
            f"{request_logging_url}?endpoint_called={endpoint}", headers=headers
        )
        if response.status_code == 200:
            logger.info("Request was successful!")
        else:
            logger.warning(f"Request failed with status code {response.status_code}")
    except Exception as e:
        logger.warning(f"An error occurred: {str(e)}")


async def convert_output(geojson, to_format):
    if to_format == "png":
        return geojson_to_rasterized_png(geojson)
    raise Exception("Format not allowed.")


async def forward_request(request: Request, target_url: str):
    if not await LIMITER.can_pass_request(request):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=CutApiErrorResponse(message="Request limit reached.").dict(),
        )

    async with httpx.AsyncClient() as client:
        try:
            token = authorise_request(request)
        except AuthError as exc:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=CutApiErrorResponse(message=exc.message).dict(),
            )

        await register_request_event(token, target_url)

        request_body = await request.body()
        request_json = json.loads(request_body.decode())

        # TODO move this to an exception handler
        if request.method == "POST":
            if "result_format" not in request_json:
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content=CutApiErrorResponse(
                        message="Request must include result_format key."
                    ).dict(),
                )
            if request_json["result_format"] not in VALID_RESULT_FORMATS:
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content=CutApiErrorResponse(
                        message=f"Result format key. Valid options are {VALID_RESULT_FORMATS} "
                    ).dict(),
                )
        # the resources API needs the bearer token to be forwarded
        # headers = {'authorization': f'Bearer {token}', 'content-type': 'application/json'}
        response = await client.request(request.method, target_url, json=request_json)

        response_content = response.content

        # TODO standardise response in calculation APIs for when it returns from cache
        # with a post request and from when it returns from get request with task_id
        # as currently in one case (task_id) the root key is "result" and the other case
        # (from cache) it is "result_format" and "geojson"
        if result := response.json().get("result") or response.json().get("geojson"):
            desired_output_format = request_json["result_format"]
            if desired_output_format != "geojson":
                converted_result = await convert_output(
                    result["geojson"], desired_output_format
                )
                response_content = json.dumps(converted_result).encode()
                response.headers["content-length"] = str(len(response_content))

        return Response(
            content=response_content,
            status_code=response.status_code,
            headers=response.headers,
        )


@app.middleware("http")
async def custom_reverse_proxy(request: Request, call_next):
    request_path = request.url.path
    print(f"Request path is {request_path}")

    # TODO deactivate docs redocs etc
    if request_path in ["/openapi.json", "/docs", "/"]:
        return await call_next(request)

    target_server_name = request_path.split("/")[1]
    print(f"target server name is {target_server_name}")

    if target_server_url := ROUTING_TABLE.get(target_server_name):
        print(f"Target server URL is {target_server_url}")
        target_url = f"{target_server_url}{request_path}"
        print(f"Target endpoint is {target_url}")
        return await forward_request(request, target_url)

    return await call_next(request)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
