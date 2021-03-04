from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseSettings, DirectoryPath

app = FastAPI()

templates = Jinja2Templates(directory="templates")


class PirripSettings(BaseSettings):
    PACKAGE_DIR: Optional[DirectoryPath]
    PYPI_FALLBACK: Optional[bool] = True

    class Config:
        env_prefix = "PIRRIP_"


async def get_pypi_data(package_name: str, release: Optional[str] = "") -> dict:
    package_string = Path(package_name) / release
    request_url = f"https://pypi.org/pypi/{package_string}/json"
    return requests.get(request_url).json()


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
        "package_detail.html", {"request": request, "files": files}
    )
