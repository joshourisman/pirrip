from fastapi import FastAPI

app = FastAPI()


@app.get("/pypi/{package_name}/json")
async def package_info(package_name: str):
    return {"package": package_name}


@app.get("/pypi/{package_name}/{release}/json")
async def release_info(package_name: str, release: str):
    return {"package": package_name, "release": release}
