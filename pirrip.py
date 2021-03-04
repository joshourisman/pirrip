from typing import Optional
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseSettings, DirectoryPath

app = FastAPI()

templates = Jinja2Templates(directory="templates")


class PirripSettings(BaseSettings):
    PACKAGE_DIR: Optional[DirectoryPath]

    class Config:
        env_prefix = "PIRRIP_"


@app.get("/pypi/{package_name}/json")
async def package_info(package_name: str):
    return requests.get(f"https://pypi.org/pypi/{package_name}/json").json()


@app.get("/pypi/{package_name}/{release}/json")
async def release_info(package_name: str, release: str):
    return requests.get(f"https://pypi.org/pypi/{package_name}/{release}/json").json()


@app.get("/simple", response_class=HTMLResponse)
async def list_packages(request: Request):
    settings = PirripSettings()
    package_dir = settings.PACKAGE_DIR
    packages = [obj for obj in package_dir.iterdir() if obj.is_dir() is True]

    return templates.TemplateResponse(
        "package_list.html", {"request": request, "packages": packages}
    )


@app.get("/simple/{package_name}", response_class=HTMLResponse)
async def read_item(request: Request, package_name: str):
    return templates.TemplateResponse(
        "package.html", {"request": request, "package_name": package_name}
    )
