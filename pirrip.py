from pathlib import Path
from typing import Optional

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
    FAUNADB_KEY: Optional[SecretStr]

    class Config:
        env_prefix = "PIRRIP_"


console = Console()


async def get_pypi_data(package_name: str, release: str = "") -> dict:
    settings = PirripSettings()

    package_string = Path(package_name) / release

    console.log(f"Requesting PyPi data for {package_string}.")
    request_url = f"https://pypi.org/pypi/{package_string}/json"
    response = requests.get(request_url).json()

    if settings.FAUNADB_KEY is not None:
        console.log(f"Logging PyPi data for {package_string} to FaunaDB.")

        client = FaunaClient(secret=settings.FAUNADB_KEY.get_secret_value())
        client.query(
            q.create(
                q.collection("packages"),
                {"data": response},
            )
        )

    return response


@app.get("/pypi/{package_name}/json")
async def package_info(package_name: str):
    return await get_pypi_data(package_name)


@app.get("/pypi/{package_name}/{release}/json")
async def release_info(package_name: str, release: str):
    return await get_pypi_data(package_name, release)


@app.get("/simple/", response_class=HTMLResponse)
async def list_packages(request: Request):
    settings = PirripSettings()
    package_dir = settings.PACKAGE_DIR
    packages = [obj for obj in package_dir.iterdir() if obj.is_dir() is True]

    return templates.TemplateResponse(
        "package_list.html", {"request": request, "packages": packages}
    )


@app.get("/simple/{package_name}/", response_class=HTMLResponse)
async def package_detail(request: Request, package_name: str):
    settings = PirripSettings()
    package_dir = settings.PACKAGE_DIR
    package = package_dir / package_name

    if package.exists() is False:
        raise HTTPException(status_code=404, detail="Package not found.")

    files = [obj for obj in package.iterdir() if obj.is_file() is True]

    return templates.TemplateResponse(
        "package_detail.html",
        {"request": request, "package_name": package_name, "files": files},
    )
