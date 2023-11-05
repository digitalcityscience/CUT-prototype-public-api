import json
import logging

import httpx
import requests
import uvicorn
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cut_api.api.converter import convert_geojson_to_png
from cut_api.api.responses import CutApiErrorResponse
from cut_api.auth.tokens import AuthError
from cut_api.config import settings
from cut_api.dependencies import LIMITER, authorise_request
from cut_api.logs import setup_logging

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
REQUEST_EVENTS_URL = "http://localhost:8001/request_events"

# If target server is not present in this routing table
# the API will return a 404 - Not Found
ROUTING_TABLE = {
    "resources": "http://localhost:8001",
    "noise": "http://localhost:8002",
    "water": "http://localhost:8003",
    # "wind": "http://localhost:8001",
    # "pedestrians": "http://localhost:8001",
}


# TODO jobs/{job_id}/results
# TODO validate endpoint
# TODO pygeo api
# TODO: implement OCG standards: https://app.swaggerhub.com/apis/OGC/ogcapi-processes-1-example-1/1.0.0#/
# TODO remove user from here and investigate how to implement clipping
# cityPyo_user = ""

# noise_result_geojson = clip_gdf_to_project_area(noise_result_geojson, cityPyo_user)
# print("Result geojson save in ", noise_result_geojson)


async def register_request_event(token: str, endpoint: str) -> None:
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        logger.info("Sending request to register request_event...")
        response = requests.post(
            REQUEST_EVENTS_URL, json={"endpoint_called": endpoint}, headers=headers
        )
        if response.status_code == 200:
            logger.info("Request was successful!")
        else:
            logger.warning(f"Request failed with status code {response.status_code}")
    except Exception as e:
        logger.warning(f"An error occurred: {str(e)}")


async def convert_output(geojson, to_format):
    if to_format == "png":
        return convert_geojson_to_png(geojson)
    raise Exception("Format not allowed.")


async def forward_request(request: Request, target_url: str):
    if not await LIMITER.can_pass_request(request):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=CutApiErrorResponse(message="Request limit reached.").dict(),
        )

    async with httpx.AsyncClient() as client:
        # TODO if token - here all requests must have a token though - but handle errors
        token = request.headers.get("authorization").replace("Bearer ", "")
        await register_request_event(token, target_url)
        try:
            _ = authorise_request(token)
        except AuthError as exc:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=CutApiErrorResponse(message=exc.message).dict(),
            )

        request_body = await request.body()
        request_json = json.loads(request_body.decode())

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

        response = await client.request(request.method, target_url, json=request_json)

        if (
            request.method == "GET"
            and "status" not in request.url.path
            and response.status_code == 200
        ):
            if result := response.json().get("result"):
                desired_output_format = result["result_format"]
                if desired_output_format != "geojson":
                    converted_result = await convert_output(
                        result["geojson"], desired_output_format
                    )

                    return Response(
                        content=str(converted_result).encode(),
                        status_code=response.status_code,
                    )

        return Response(
            content=response.content,
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
