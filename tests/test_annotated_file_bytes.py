from typing import Annotated

import pytest
from fastapi import FastAPI, File
from fastapi.testclient import TestClient
from pydantic import Field

ConstrainedBytes = Annotated[bytes, Field(min_length=3)]

app = FastAPI()


@app.post("/list")
def upload_list(files: Annotated[list[ConstrainedBytes], File()]):
    return {"sizes": [len(file) for file in files]}


@app.post("/nullable-items")
def upload_nullable_items(files: Annotated[list[ConstrainedBytes | None], File()]):
    return {"sizes": [len(file) if file is not None else None for file in files]}


@app.post("/optional")
def upload_optional(file: Annotated[ConstrainedBytes | None, File()] = None):
    return {"size": len(file) if file is not None else None}


client = TestClient(app)


@pytest.fixture(params=["/list", "/nullable-items"])
def path(request: pytest.FixtureRequest):
    return request.param


def test_constrained_bytes_sequence(path: str):
    response = client.post(
        path,
        files=[
            ("files", ("first.txt", b"hello")),
            ("files", ("second.txt", b"world!")),
        ],
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"sizes": [5, 6]}


def test_constrained_bytes_sequence_too_short(path: str):
    response = client.post(path, files={"files": ("short.txt", b"hi")})
    assert response.status_code == 422, response.text
    assert response.json() == {
        "detail": [
            {
                "type": "bytes_too_short",
                "loc": ["body", "files", 0],
                "msg": "Data should have at least 3 bytes",
                "input": "hi",
                "ctx": {"min_length": 3},
            }
        ]
    }


def test_constrained_bytes_sequence_missing(path: str):
    response = client.post(path)
    assert response.status_code == 422, response.text
    assert response.json()["detail"][0]["type"] == "missing"
    assert response.json()["detail"][0]["loc"] == ["body", "files"]


def test_optional_constrained_bytes():
    response = client.post("/optional", files={"file": ("file.txt", b"hello")})
    assert response.status_code == 200, response.text
    assert response.json() == {"size": 5}


def test_optional_constrained_bytes_too_short():
    response = client.post("/optional", files={"file": ("short.txt", b"hi")})
    assert response.status_code == 422, response.text
    assert response.json() == {
        "detail": [
            {
                "type": "bytes_too_short",
                "loc": ["body", "file"],
                "msg": "Data should have at least 3 bytes",
                "input": "hi",
                "ctx": {"min_length": 3},
            }
        ]
    }


def test_optional_constrained_bytes_missing():
    response = client.post("/optional")
    assert response.status_code == 200, response.text
    assert response.json() == {"size": None}
