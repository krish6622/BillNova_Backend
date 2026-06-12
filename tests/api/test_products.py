"""Product CRUD / search / pagination / RBAC / isolation tests."""

from tests.conftest import auth_headers, register

PRODUCT = {
    "product_code": "TS-001",
    "name": "Cotton Saree",
    "category": "Sarees",
    "unit": "PCS",
    "purchase_price": 600,
    "selling_price": 999,
    "gst_percentage": 5,
    "hsn_code": "5407",
    "current_stock": 50,
    "reorder_level": 5,
}


def _owner(client):
    return register(client).json()["access_token"]


def _make_cashier(client, owner_token):
    client.post(
        "/api/users", headers=auth_headers(owner_token),
        json={"name": "Asha", "email": "asha@shop.in", "password": "cashierpass1"},
    )
    return client.post(
        "/api/auth/login", json={"email": "asha@shop.in", "password": "cashierpass1"}
    ).json()["access_token"]


def test_owner_creates_and_reads_product(client):
    token = _owner(client)
    resp = client.post("/api/products", headers=auth_headers(token), json=PRODUCT)
    assert resp.status_code == 201
    pid = resp.json()["id"]
    assert resp.json()["selling_price"] == 999

    got = client.get(f"/api/products/{pid}", headers=auth_headers(token))
    assert got.status_code == 200
    assert got.json()["product_code"] == "TS-001"


def test_duplicate_code_conflicts(client):
    token = _owner(client)
    client.post("/api/products", headers=auth_headers(token), json=PRODUCT)
    dup = client.post("/api/products", headers=auth_headers(token), json=PRODUCT)
    assert dup.status_code == 409


def test_update_and_delete(client):
    token = _owner(client)
    pid = client.post("/api/products", headers=auth_headers(token), json=PRODUCT).json()["id"]

    upd = client.put(f"/api/products/{pid}", headers=auth_headers(token), json={"selling_price": 1099})
    assert upd.status_code == 200
    assert upd.json()["selling_price"] == 1099

    dele = client.delete(f"/api/products/{pid}", headers=auth_headers(token))
    assert dele.status_code == 204
    assert client.get(f"/api/products/{pid}", headers=auth_headers(token)).status_code == 404


def test_search_and_pagination(client):
    token = _owner(client)
    for i in range(5):
        p = {**PRODUCT, "product_code": f"P-{i}", "name": f"Item {i}"}
        client.post("/api/products", headers=auth_headers(token), json=p)
    client.post(
        "/api/products", headers=auth_headers(token),
        json={**PRODUCT, "product_code": "ZZ", "name": "Zebra Towel"},
    )

    page1 = client.get("/api/products?page=1&limit=2", headers=auth_headers(token)).json()
    assert page1["total"] == 6
    assert len(page1["items"]) == 2

    found = client.get("/api/products?search=zebra", headers=auth_headers(token)).json()
    assert found["total"] == 1
    assert found["items"][0]["name"] == "Zebra Towel"


def test_cashier_can_read_but_not_write(client):
    owner = _owner(client)
    pid = client.post("/api/products", headers=auth_headers(owner), json=PRODUCT).json()["id"]
    cashier = _make_cashier(client, owner)

    assert client.get("/api/products", headers=auth_headers(cashier)).status_code == 200
    create = client.post(
        "/api/products", headers=auth_headers(cashier),
        json={**PRODUCT, "product_code": "NEW"},
    )
    assert create.status_code == 403
    assert client.delete(f"/api/products/{pid}", headers=auth_headers(cashier)).status_code == 403


def test_products_are_tenant_isolated(client):
    a = _owner(client)
    a_pid = client.post("/api/products", headers=auth_headers(a), json=PRODUCT).json()["id"]

    b = register(client, business_name="B Store", email="b@b.in").json()["access_token"]
    # B sees no products and cannot fetch A's product id
    b_list = client.get("/api/products", headers=auth_headers(b)).json()
    assert b_list["total"] == 0
    assert client.get(f"/api/products/{a_pid}", headers=auth_headers(b)).status_code == 404
