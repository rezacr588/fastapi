from typing import Annotated

import pytest
from fastapi import Cookie, FastAPI, Header, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field


@pytest.fixture(params=[Query, Header, Cookie])
def client_and_calls(request: pytest.FixtureRequest):
    parameter = request.param
    calls: list[str] = []

    def factory():
        value = f"default-{len(calls) + 1}"
        calls.append(value)
        return value

    app = FastAPI()

    @app.get("/")
    def read(value: str = parameter(default_factory=factory)):
        return {"value": value}

    return TestClient(app), calls


def test_missing_parameter_calls_factory_once(client_and_calls):
    client, calls = client_and_calls
    response = client.get("/")
    assert response.status_code == 200, response.text
    assert response.json() == {"value": "default-1"}
    assert calls == ["default-1"]


def test_factory_is_called_for_each_request(client_and_calls):
    client, calls = client_and_calls
    first = client.get("/")
    second = client.get("/")
    assert first.status_code == second.status_code == 200
    assert first.json() == {"value": "default-1"}
    assert second.json() == {"value": "default-2"}
    assert calls == ["default-1", "default-2"]


def test_provided_parameter_does_not_call_factory(client_and_calls):
    client, calls = client_and_calls
    client.cookies.set("value", "provided")
    response = client.get(
        "/", params={"value": "provided"}, headers={"value": "provided"}
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"value": "provided"}
    assert calls == []


@pytest.mark.parametrize("parameter", [Query, Header, Cookie])
def test_factory_returning_none_is_not_repeated(parameter):
    calls: list[None] = []

    def factory():
        calls.append(None)
        return None

    app = FastAPI()

    @app.get("/")
    def read(value: str | None = parameter(default_factory=factory)):
        return {"value": value}

    client = TestClient(app)
    for expected_calls in range(1, 3):
        response = client.get("/")
        assert response.status_code == 200, response.text
        assert response.json() == {"value": None}
        assert calls == [None] * expected_calls


def test_factory_value_is_validated():
    calls: list[str] = []

    def factory():
        calls.append("not an integer")
        return calls[-1]

    app = FastAPI()

    @app.get("/")
    def read(value: int = Query(default_factory=factory)):
        return {"value": value}

    response = TestClient(app).get("/")
    assert response.status_code == 422, response.text
    assert response.json()["detail"][0]["type"] == "int_parsing"
    assert response.json()["detail"][0]["loc"] == ["query", "value"]
    assert calls == ["not an integer"]


@pytest.mark.parametrize("provided", [False, True])
def test_multiple_parameters_call_factory_once_per_missing_field(provided: bool):
    calls: list[str] = []

    def factory():
        value = f"default-{len(calls) + 1}"
        calls.append(value)
        return value

    app = FastAPI()

    @app.get("/")
    def read(
        first: str = Query(default_factory=factory),
        second: str = Query(default_factory=factory),
    ):
        return {"first": first, "second": second}

    response = TestClient(app).get(
        "/", params={"first": "provided"} if provided else {}
    )
    assert response.status_code == 200, response.text
    if provided:
        assert response.json() == {"first": "provided", "second": "default-1"}
        assert calls == ["default-1"]
    else:
        assert response.json() == {"first": "default-1", "second": "default-2"}
        assert calls == ["default-1", "default-2"]


def test_parameter_model_default_factory():
    calls: list[str] = []

    def factory():
        value = f"default-{len(calls) + 1}"
        calls.append(value)
        return value

    class QueryModel(BaseModel):
        value: str = Field(default_factory=factory)

    app = FastAPI()

    @app.get("/")
    def read(model: Annotated[QueryModel, Query()]):
        return model

    response = TestClient(app).get("/")
    assert response.status_code == 200, response.text
    assert response.json() == {"value": "default-1"}
    assert calls == ["default-1"]
