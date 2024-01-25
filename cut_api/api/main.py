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
origins = ["*"]

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
    # "pedestrians": settings.external_apis.pedestrians,
}


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


async def prepare_response(desired_output_format, response):
    response_content = response.content

    # TODO standardise response in calculation APIs for when it returns from cache
    # with a post request and from when it returns from get request with task_id
    # as currently in one case (task_id) the root key is "result" and the other case
    # (from cache) it is "result_format" and "geojson"
    if result := response.json().get("result"):
        if desired_output_format != "geojson":
            converted_from_geojson = await convert_output(
                result.pop("geojson"), desired_output_format
            )
            result[desired_output_format.lower()] = converted_from_geojson
            response_content = json.dumps({"result": result}).encode()
            response.headers["content-length"] = str(len(response_content))

    return Response(
        content=response_content,
        status_code=response.status_code,
        headers=response.headers,
    )


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

        # if request is to docs endpoints, auth is skipped
        if all(
            endpoint not in target_url for endpoint in ["docs", "openapi.json", "redoc"]
        ):
            try:
                token = authorise_request(request)
            except AuthError as exc:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content=CutApiErrorResponse(message=exc.message).dict(),
                )

            await register_request_event(token, target_url)

        if request.method == "POST":
            request_body = await request.body()
            request_json = json.loads(request_body.decode())
            response = await client.request(
                request.method, target_url, json=request_json
            )
        elif request.method == "GET":
            response = await client.request(request.method, target_url)

            if "results" in target_url:
                if desired_result_format := request.query_params.get("result_format"):
                    return (
                        JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content=CutApiErrorResponse(
                                message=f"Result format key. Valid options are {VALID_RESULT_FORMATS} "
                            ).dict(),
                        )
                        if desired_result_format.lower() not in VALID_RESULT_FORMATS
                        else await prepare_response(desired_result_format, response)
                    )
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response.headers,
        )


@app.middleware("http")
async def custom_reverse_proxy(request: Request, call_next):
    # TODO this is a temp fix due to the nginx configs, in an ideal scenario
    # cut-public-api should be served at root, but is currently served at /cut-public-api
    request_path = request.url.path.replace("/cut-public-api", "")
    logger.info(f"Request path is {request_path}")

    target_server_name = request_path.split("/")[1]
    logger.info(f"target server name is {target_server_name}")

    if target_server_url := ROUTING_TABLE.get(target_server_name):
        # handle preflight requests.
        if request.method == "OPTIONS":
            return Response(
                status_code=200,
                headers={"Access-Control-Allow-Origin": "*"}
            )

        logger.info(f"Target server URL is {target_server_url}")
        target_url = f"{target_server_url}{request_path}"
        logger.info(f"Target endpoint is {target_url}")
        return await forward_request(request, target_url)

    return await call_next(request)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
