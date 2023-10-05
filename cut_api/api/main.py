import httpx
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from cut_api.config import settings
from cut_api.dependencies import LIMITER

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

# Set Rate Limiter
app.state.limiter = LIMITER
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.get("/health_check", tags=["ROOT"])
async def health_check():
    return "ok"


ROUTING_TABLE = {
    "auth": "http://localhost:8001",
    "resources": "http://localhost:8001",
    "noise": "http://localhost:8002",
    "water": "http://localhost:8003",
    # "wind": "http://localhost:8001",
    # "pedestrians": "http://localhost:8001",
}


@app.middleware("http")
async def custom_reverse_proxy(request: Request, call_next):
    request_path = request.url.path
    print(f"Request path is {request_path}")

    if request_path in ["/openapi.json", "/docs", "/"]:
        return await call_next(request)

    target_server_name = request_path.split("/")[1]
    print(f"target server name is {target_server_name}")

    if target_server_url := ROUTING_TABLE.get(target_server_name):
        print(f"Target server URL is {target_server_url}")

        target_url = f"{target_server_url}{request_path}"
        print(f"Target endpoint is {target_url}")

        async with httpx.AsyncClient() as client:
            response = await client.request(
                request.method, target_url, data=await request.body()
            )

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response.headers,
            )
    return await call_next(request)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
