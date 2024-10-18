# Pip Time Machine API

A simple Python server that forwards requests to PyPI's Simple API,
filters results based on a specific point in time, and returns the
response.

Primary purpose is for testing pip, but may be useful for reliably
installing the same packages from a given date.

## Features

- Filters package files by a specified datetime
- Powered by [PEP 691](https://peps.python.org/pep-0691/) and PEP [PEP 700](https://peps.python.org/pep-0691/) to quickly filter packages after the given time

## Installation

I reccomend install `pip-timemachine` as a tool, e.g. using
[uv](https://github.com/astral-sh/uv?tab=readme-ov-file#uv):

```bash
uv tool install pip-timemachine
```

Or using [pipx](https://github.com/pypa/pipx?tab=readme-ov-file):

```bash
pipx install pip-timemachine
```

```bash
pip-timemachine 2023-10-18T12:00:00
```

## Usage

### CLI Options

- `--moment`: The datetime (in RFC3339 format) up to which package files are returned.
- `--index`: The PyPI index URL (default: `https://pypi.org/simple`).
- `--port`: Server port (default: `8040`).
