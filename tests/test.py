import pytest
from werkzeug.datastructures import Accept

from pip_timemachine.main import (
    api_version_check,
    filter_accept_header,
    filter_files_by_moment,
    parse_version_from_filename,
)


def test_parse_version_from_filename_wheel():
    version = parse_version_from_filename("example_pkg-0.1.0-py3-none-any.whl")
    assert version == "0.1.0"


def test_parse_version_from_filename_sdist():
    version = parse_version_from_filename("example_pkg-0.1.0.tar.gz")
    assert version == "0.1.0"


def test_parse_version_from_invalid_filename():
    version = parse_version_from_filename("invalid_package_name")
    assert version is None


def test_api_version_check_valid():
    # No exception should be raised
    api_version_check("1.1")


def test_api_version_check_invalid():
    with pytest.raises(RuntimeError, match="require 1.1+"):
        api_version_check("1.0")


def test_filter_accept_header_valid():
    accept_header = "application/vnd.pypi.simple.v1+json"
    accept = filter_accept_header(accept_header)
    assert isinstance(accept, Accept)


def test_filter_accept_header_invalid():
    with pytest.raises(RuntimeError, match="Client did not send a JSON accept header"):
        filter_accept_header("text/html")


def test_filter_files_by_moment():
    files = [
        {"filename": "example_pkg-0.1.0.tar.gz", "upload-time": "2023-10-18T12:00:00Z"},
        {"filename": "example_pkg-0.2.0.tar.gz", "upload-time": "2050-10-18T12:00:00Z"},
    ]
    modified_files, modified_versions = filter_files_by_moment(files)
    assert len(modified_files) == 1
    assert "0.1.0" in modified_versions
