from typing import List, Optional
from faunadb.errors import BadRequest, NotFound as FaunaPackageNotFound

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from faunadb import query as q
from faunadb.client import FaunaClient
from pydantic import BaseSettings, DirectoryPath
from pydantic.types import SecretStr
from rich.console import Console

app = FastAPI()

templates = Jinja2Templates(directory="templates")


class PirripSettings(BaseSettings):
    PACKAGE_DIR: Optional[DirectoryPath]
    PYPI_FALLBACK: Optional[bool] = True
    FAUNADB_KEY: SecretStr

    class Config:
        env_prefix = "PIRRIP_"


settings = PirripSettings()
console = Console()


class PyPiPackageNotFound(Exception):
    pass


class PyPiReleaseNotFound(Exception):
    pass


class FaunaReleaseNotFound(Exception):
    pass


async def get_package_by_name(package_name: str) -> dict:
    client = FaunaClient(secret=settings.FAUNADB_KEY.get_secret_value())
    return client.query(q.get(q.match(q.index("package_by_name"), package_name)))


async def get_package_names() -> List[str]:
    client = FaunaClient(secret=settings.FAUNADB_KEY.get_secret_value())
    return client.query(q.paginate(q.match(q.index("package_names"))))["data"]


async def get_fauna_data(package_name: str, release: str = "") -> dict:
    console.log(f"Querying FaunaDB for {package_name}.")
    try:
        fauna_package = await get_package_by_name(package_name)
        package = fauna_package["data"]
    except FaunaPackageNotFound as e:
        if settings.PYPI_FALLBACK is True:
            package = await get_pypi_data(package_name)
        else:
            raise e
    else:
        if bool(release) is True and release not in package["releases"].keys():
            if settings.PYPI_FALLBACK is True:
                package = await get_pypi_data(package_name)
                if release not in package["releases"].keys():
                    raise PyPiReleaseNotFound

    if bool(release) is True and release not in package["releases"].keys():
        raise FaunaReleaseNotFound

    return package


async def get_pypi_data(package_name: str) -> dict:
    console.log(f"Requesting PyPi data for {package_name}.")
    request_url = f"https://pypi.org/pypi/{package_name}/json"
    response = requests.get(request_url)

    if response.status_code == 404:
        raise PyPiPackageNotFound

    assert response.status_code == 200
    package_data = response.json()

    console.log(f"Logging PyPi data for {package_name} to FaunaDB.")

    client = FaunaClient(secret=settings.FAUNADB_KEY.get_secret_value())
    try:
        client.query(
            q.create(
                q.collection("packages"),
                {"data": package_data},
            )
        )
    except BadRequest:
        package = await get_package_by_name(package_name)
        ref = package["ref"]
        client.query(q.update(ref, {"data": package_data}))

    return package_data


@app.get("/pypi/{package_name}/json")
async def package_info(package_name: str):
    console.log(f"Attempting to fetch data for {package_name}.")
    try:
        package = await get_fauna_data(package_name)
    except FaunaPackageNotFound:
        raise HTTPException(
            status_code=404, detail=f"{package_name} not found in Pirrip database."
        )
    except PyPiPackageNotFound:
        raise HTTPException(
            status_code=404, detail=f"{package_name} not found in PyPi database."
        )

    return package


@app.get("/pypi/{package_name}/{release}/json")
async def release_info(package_name: str, release: str):
    console.log(f"Attempting to fetch data for {package_name}, release {release}.")
    try:
        package = await get_fauna_data(package_name, release)
    except FaunaPackageNotFound:
        raise HTTPException(
            status_code=404, detail=f"{package_name} not found in Pirrip database."
        )
    except PyPiPackageNotFound:
        raise HTTPException(
            status_code=404, detail=f"{package_name} not found in PyPi database."
        )
    except FaunaReleaseNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"{package_name} {release} not found in Pirrip database.",
        )
    except PyPiReleaseNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"{package_name} {release} not found in PyPi database.",
        )

    return package


@app.get("/simple/", response_class=HTMLResponse)
async def list_packages(request: Request):
    return templates.TemplateResponse(
        "package_list.html", {"request": request, "packages": await get_package_names()}
    )


@app.get("/simple/{package_name}/", response_class=HTMLResponse)
async def package_detail(request: Request, package_name: str):
    package = await get_fauna_data(package_name)

    return templates.TemplateResponse(
        "package_detail.html",
        {
            "request": request,
            "package_name": package_name,
            "releases": package["releases"],
        },
    )
