from fastapi import APIRouter
import httpx

from routing_table import ROUTING_TABLE


router = APIRouter(tags=["ogc"])


@router.get("/processes")
async def get_processes_json() -> dict:
    processes = []

    for service in ROUTING_TABLE:
        try:
            async with httpx.AsyncClient() as client:
                target_url = f"{ROUTING_TABLE.get(service)}/{service}/processes"
                service_processes = await client.request("GET", target_url)
                processes.extend(service_processes.json().get("processes"))
        except Exception as e:
            print(f"could not get processes description for {service} service. Exception: {e} \n"
                  f"when trying to access {target_url}")

    return {"processes": processes}


@router.get("/conformance")
async def get_conformance() -> dict:
    return {
        "conformsTo": [
            "http://www.opengis.net/spec/ogcapi-processes/1.0/conf/core",
            "http://www.opengis.net/spec/ogcapi-processes/1.0/conf/json",
        ]
    }


@router.get("/")
async def get_landing_page() -> dict:
    return {
        "title": "CUT-PROTOTYPE SIMULATION SERVICES",
        "description": "Simulate urban traffic noise, wind comfort and more to come for given roads and buildings.",
        "links": [
            {
                "rel": "service-desc",
                "type": "application/vnd.oai.openapi+json;version=3.0",
                "title": "The OpenAPI definition as JSON",
                "href": "/openapi.json"
            },
            {
                "rel": "conformance",
                "type": "application/json",
                "title": "Conformance",
                "href": "/conformance"
            },
            {
                "rel": "http://www.opengis.net/def/rel/ogc/1.0/processes",
                "type": "application/json",
                "title": "Processes",
                "href": "/processes"
            },
        ]
    }
