import requests
from fastapi import FastAPI

app = FastAPI()


@app.get("/pypi/{package_name}/json")
async def package_info(package_name: str):
    return requests.get(f"https://pypi.org/pypi/{package_name}/json").json()


@app.get("/pypi/{package_name}/{release}/json")
async def release_info(package_name: str, release: str):
    return requests.get(f"https://pypi.org/pypi/{package_name}/{release}/json").json()
