import datetime as dt
import logging
from datetime import timezone
from functools import cache

import niquests
import typer
import uvicorn
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from packaging.utils import (
    InvalidSdistFilename,
    InvalidWheelFilename,
    parse_sdist_filename,
    parse_wheel_filename,
)
from werkzeug.datastructures import Accept
from werkzeug.http import parse_accept_header
from whenever import Instant

# Global Apps
logger = logging.getLogger(__name__)
app = FastAPI()

# Global Vars
UNICORN_SERVER: uvicorn.Server | None = None
MOMENT: Instant = Instant.now()
INDEX: str = "https://pypi.org/simple"
REQUIRED_API_VERSION = (1, 1)


@cache
def parse_version_from_filename(file_name: str) -> str | None:
    try:
        _name, version, _build_tag, _tags = parse_wheel_filename(file_name)
    except InvalidWheelFilename:
        try:
            _name, version = parse_sdist_filename(file_name)
        except InvalidSdistFilename:
            logger.debug("%s is an invalid package file name", file_name)
            return None
    return str(version)


@cache
def api_version_check(version_str: str) -> None:
    current_version = tuple(map(int, version_str.split(".")))
    if current_version >= REQUIRED_API_VERSION:
        return
    raise RuntimeError(f"Received API version {version_str} but require 1.1+")


@cache
def filter_accept_header(accept_header: str) -> Accept:
    """Parse the Accept header and filter for the required JSON response."""
    accepts = parse_accept_header(accept_header)
    json_accept = []
    for accept_type, accept_quality in accepts.copy():
        if accept_type == "application/vnd.pypi.simple.v1+json":
            json_accept.append((accept_type, accept_quality))
            break
    if not json_accept:
        raise RuntimeError("Client did not send a JSON accept header")
    return Accept(json_accept)


def filter_files_by_moment(files: list[dict]) -> tuple[list, dict]:
    """Filter files based on the MOMENT and parse versions."""
    modified_files = []
    modified_versions: dict[str, None] = {}
    for file in files:
        if not Instant.parse_iso(file["upload-time"]) <= MOMENT:
            continue
        file_name = file["filename"]
        version = parse_version_from_filename(file_name)
        if version is None:
            continue
        modified_files.append(file)
        modified_versions[version] = None
    return modified_files, modified_versions


def initiate_shutdown():
    logger.info("Gracefully shutting down")
    if UNICORN_SERVER:
        UNICORN_SERVER.should_exit = True


@app.get("/shutdown-pip-timemachine-server")
async def shutdown_pip_timemachine_server(background_tasks: BackgroundTasks):
    """
    Endpoint to gracefully shut down the FastAPI server.
    """
    # Run the shutdown in a separate thread to allow the response to return first
    background_tasks.add_task(initiate_shutdown)
    return JSONResponse({"message": "Server is shutting down."})


@app.get("/simple/{package_name}")
async def get_pypi_package_info(package_name: str, request: Request) -> Response:
    # Determine content type based on "Accept" header
    accept_header = request.headers.get("Accept")
    if not accept_header:
        raise RuntimeError("Client did not send accept header")

    json_accept = filter_accept_header(accept_header)

    # Strip host out of headers and add modified Accept
    headers = dict(request.headers.items())
    del headers["host"]
    headers["Accept"] = str(json_accept)

    # Forward the request to PyPI
    async with niquests.AsyncSession() as session:  # type: ignore
        pypi_response = await session.get(f"{INDEX}/{package_name}/", headers=headers)

    try:
        pypi_response.raise_for_status()
    except Exception:
        logger.warning(
            "Received invalid status code %d from index", pypi_response.status_code
        )
        return Response(
            content=pypi_response.content, status_code=pypi_response.status_code
        )

    response_json = pypi_response.json()
    api_version_check(response_json["meta"]["api-version"])

    if "files" not in response_json or not response_json["files"]:
        return JSONResponse(content=response_json)

    modified_files, modified_versions = filter_files_by_moment(response_json["files"])

    response_json["files"] = modified_files
    response_json["versions"] = modified_versions

    return JSONResponse(
        content=response_json, media_type="application/vnd.pypi.simple.v1+json"
    )


def run_server(moment: dt.datetime, index: str = INDEX, port: int = 8040):
    global MOMENT
    global INDEX
    global UNICORN_SERVER
    MOMENT = Instant.from_py_datetime(moment.replace(tzinfo=timezone.utc))
    INDEX = index.rstrip("/")

    UNICORN_SERVER = uvicorn.Server(
        uvicorn.Config(
            "pip_timemachine.main:app", port=port, workers=4, timeout_keep_alive=15
        )
    )
    UNICORN_SERVER.run()


def main():
    typer.run(run_server)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
