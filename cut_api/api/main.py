from typing import Optional

import httpx
import requests
import uvicorn
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from cut_api.auth.tokens import AuthError, authorise_request
from cut_api.config import settings
from cut_api.dependencies import LIMITER


class CutApiErrorResponse(BaseModel):
    message: str
    details: Optional[dict]

    @classmethod
    def internal_error(cls):
        # don't provide internal error details to external clients
        return cls(message="internal error")


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


# Endpoints:

# POST /noise/v2/tasks
# GET  /noise/v2/tasks/{task_id}
# GET  /noise/v2/tasks/{task_id}/status

# POST /water/v2/tasks
# GET  /water/v2/tasks/{task_id}
# GET  /water/v2/tasks/{task_id}/status

# POST /abm/v2/tasks
# GET  /abm/v2/tasks/{task_id}
# GET  /abm/v2/tasks/{task_id}/status

# POST /wind/v2/tasks
# GET  /wind/v2/tasks/{task_id}
# GET  /wind/v2/tasks/{task_id}/status
# POST /wind/v2/grouptasks/{group_task_id}

# TODO jobs/{job_id}/results
# TODO validate endpoint
# TODO pygeo api
# TODO conversion between PNG and GEOJSON


async def register_request_event(token: str, endpoint: str) -> None:
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",  # Set the content type as needed
        }
        response = requests.post(
            REQUEST_EVENTS_URL, json={"endpoint_called": endpoint}, headers=headers
        )
        if response.status_code == 200:
            print("Request was successful!")
            print("Response:")
            print(response.text)
        else:
            print(f"Request failed with status code {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")


async def forward_request(request: Request, target_url: str):
    if not await LIMITER.can_pass_request(request, rate_per_minute=10):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=CutApiErrorResponse(message="Request limit reached.").dict(),
        )

    async with httpx.AsyncClient() as client:
        # TODO if token - here all requests must have a token though - but handle errors
        token = request.headers.get("authorization").replace("Bearer ", "")
        register_request_event(token, target_url)
        try:
            user = authorise_request(token)
            print(user)

            response = await client.request(
                request.method, target_url, data=await request.body()
            )

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response.headers,
            )
        except AuthError as exc:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=CutApiErrorResponse(message=exc.message).dict(),
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
