import os
import secrets
import warnings
from uuid import UUID, uuid4

import pytest
import requests


BASE_URL = os.getenv("BASE_URL", "https://qa-internship.avito.com").rstrip("/")
REGISTER = "/api/1/register"
LOGIN = "/api/1/autorize"
ITEMS = "/api/1/item"


def credentials():
    return {"username": f"qa_{uuid4().hex[:16]}", "password": secrets.token_hex(16)}


def expect(response, *codes):
    # Тело ответа может содержать токен, поэтому в отчёт идут только метод и статус.
    assert response.status_code in codes, (
        f"{response.request.method} {response.request.path_url}: "
        f"HTTP {response.status_code}, ожидалось {codes}"
    )


def read_json(response):
    assert response.headers.get("Content-Type", "").split(";")[0] == "application/json"
    return response.json()


@pytest.fixture
def request_api():
    with requests.Session() as session:
        def send(method, path, *, body=None, token=None):
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            return session.request(
                method,
                BASE_URL + path,
                json=body,
                headers=headers,
                timeout=(5, 15),
                allow_redirects=False,
            )

        yield send


def register(send, account):
    response = send("POST", REGISTER, body=account)
    expect(response, 201)
    user = read_json(response)
    assert user["username"] == account["username"]
    assert type(user["id"]) is int and user["id"] > 0
    assert "password" not in user
    return user["id"]


def authorize(send, account):
    response = send("POST", LOGIN, body=account)
    expect(response, 200)
    auth = read_json(response)
    assert auth["tokenType"].lower() == "bearer"
    assert isinstance(auth["accessToken"], str) and auth["accessToken"].strip()
    return auth["accessToken"]


@pytest.fixture
def seller(request_api):
    account = credentials()
    return register(request_api, account), authorize(request_api, account)


@pytest.fixture
def payload(seller):
    return {
        "sellerID": seller[0],
        "name": f"QA диван {uuid4().hex[:8]}",
        "price": 9900,
        "statistics": {"likes": 21, "viewCount": 11, "contacts": 43},
    }


@pytest.fixture
def create_item(request_api, seller):
    created = set()

    def create(payload, issue=None):
        response = request_api("POST", ITEMS, body=payload, token=seller[1])
        if issue is not None:
            assert response.status_code == 200, (
                f"{issue}: POST {ITEMS} вернул HTTP {response.status_code} вместо 200"
            )
        expect(response, 200)
        item_id = read_json(response)["status"].rsplit(" - ", 1)[-1]
        assert str(UUID(item_id)) == item_id
        created.add(item_id)
        return item_id

    yield create

    for item_id in created:
        try:
            response = request_api("DELETE", f"/api/2/item/{item_id}", token=seller[1])
            if response.status_code not in (200, 204, 404):
                warnings.warn(f"Очистка {item_id}: HTTP {response.status_code}", stacklevel=1)
        except requests.RequestException as exc:
            warnings.warn(f"Очистка {item_id}: {type(exc).__name__}", stacklevel=1)


def assert_item(actual, item_id, payload):
    assert actual["id"] == item_id
    assert actual["sellerId"] == payload["sellerID"]
    for key in ("name", "price", "statistics"):
        assert actual[key] == payload[key], f"Поле {key}"
    assert isinstance(actual["createdAt"], str) and actual["createdAt"].strip()


def test_api01_lifecycle(request_api, seller, payload, create_item):
    token = seller[1]
    item_id = create_item(payload)
    response = request_api("GET", f"{ITEMS}/{item_id}", token=token)
    expect(response, 200)
    rows = read_json(response)
    assert len(rows) == 1
    assert_item(rows[0], item_id, payload)

    for version in (1, 2):
        response = request_api("GET", f"/api/{version}/statistic/{item_id}", token=token)
        expect(response, 200)
        assert read_json(response) == [payload["statistics"]]

    response = request_api("DELETE", f"/api/2/item/{item_id}", token=token)
    expect(response, 200, 204)
    expect(request_api("GET", f"{ITEMS}/{item_id}", token=token), 404)
    response = request_api("GET", f"/api/1/{seller[0]}/item", token=token)
    expect(response, 200)
    assert read_json(response) == []


def test_api02_duplicate_registration(request_api):
    account = credentials()
    register(request_api, account)
    expect(request_api("POST", REGISTER, body=account), 409)
    authorize(request_api, account)


@pytest.mark.parametrize("endpoint", [REGISTER, LOGIN])
@pytest.mark.parametrize("field", ["username", "password"])
def test_api03_missing_credential(request_api, endpoint, field):
    account = credentials()
    del account[field]
    expect(request_api("POST", endpoint, body=account), 400)


@pytest.mark.parametrize("registered", [True, False], ids=["wrong-password", "unknown-user"])
def test_api04_invalid_credentials(request_api, registered):
    account = credentials()
    if registered:
        register(request_api, account)
        account["password"] = secrets.token_hex(16)
    expect(request_api("POST", LOGIN, body=account), 401, 403)


def test_api05_seller_list_and_equal_items(request_api, seller, payload, create_item):
    token = seller[1]
    path = f"/api/1/{seller[0]}/item"
    response = request_api("GET", path, token=token)
    expect(response, 200)
    assert read_json(response) == []

    first_id = create_item(payload)
    second_id = create_item(payload)
    assert first_id != second_id

    response = request_api("GET", path, token=token)
    expect(response, 200)
    items = read_json(response)
    assert sorted(item["id"] for item in items) == sorted((first_id, second_id))
    for item in items:
        assert_item(item, item["id"], payload)


@pytest.mark.parametrize("method, path", [
    ("GET", "/api/1/item/{id}"),
    ("GET", "/api/1/statistic/{id}"),
    ("GET", "/api/2/statistic/{id}"),
    ("DELETE", "/api/2/item/{id}"),
])
@pytest.mark.parametrize("valid_uuid", [False, True], ids=["bad-format", "absent"])
def test_api06_lookup_errors(request_api, seller, method, path, valid_uuid):
    item_id = str(uuid4()) if valid_uuid else "invalid-uuid"
    response = request_api(method, path.format(id=item_id), token=seller[1])
    if path.startswith("/api/2/statistic") and not valid_uuid:
        assert response.status_code == 400, (
            f"API-BUG-02: статистика v2 для неверного формата UUID "
            f"вернула HTTP {response.status_code} вместо 400"
        )
    else:
        expect(response, 404 if valid_uuid else 400)


@pytest.mark.parametrize("method, path", [
    ("POST", "/api/1/item"),
    ("GET", "/api/1/item/{id}"),
    ("GET", "/api/1/1/item"),
    ("GET", "/api/1/statistic/{id}"),
    ("GET", "/api/2/statistic/{id}"),
    ("DELETE", "/api/2/item/{id}"),
])
def test_api07_requires_sign_in(request_api, method, path):
    response = request_api(method, path.format(id=uuid4()))
    expect(response, 401, 403)


@pytest.mark.parametrize("price", [1, 2])
def test_api08_small_positive_price(request_api, seller, payload, create_item, price):
    payload["price"] = price
    item_id = create_item(payload)
    response = request_api("GET", f"{ITEMS}/{item_id}", token=seller[1])
    expect(response, 200)
    rows = read_json(response)
    assert len(rows) == 1
    assert_item(rows[0], item_id, payload)


@pytest.mark.parametrize("version", [1, 2])
def test_api09_deleted_item_statistics(request_api, seller, payload, create_item, version):
    token = seller[1]
    item_id = create_item(payload)
    path = f"/api/{version}/statistic/{item_id}"

    response = request_api("GET", path, token=token)
    expect(response, 200)
    assert read_json(response) == [payload["statistics"]]

    expect(request_api("DELETE", f"/api/2/item/{item_id}", token=token), 200, 204)
    expect(request_api("GET", f"{ITEMS}/{item_id}", token=token), 404)
    response = request_api("GET", path, token=token)
    assert response.status_code == 404, (
        f"API-BUG-01: статистика v{version} удалённого объявления "
        f"возвращает HTTP {response.status_code} вместо 404"
    )


@pytest.mark.parametrize("field", ["likes", "viewCount", "contacts"])
def test_api10_zero_counter(request_api, seller, payload, create_item, field):
    payload["statistics"][field] = 0
    item_id = create_item(payload, issue=f"API-BUG-03 ({field}=0)")
    response = request_api("GET", f"{ITEMS}/{item_id}", token=seller[1])
    expect(response, 200)
    rows = read_json(response)
    assert len(rows) == 1
    assert_item(rows[0], item_id, payload)
