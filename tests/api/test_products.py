"""Product catalogue tests (CR-1): created via purchase, read-only selling price,
no direct create/delete, tenant isolation."""

from tests.conftest import auth_headers, register, seed_product


def _owner(client):
    return auth_headers(register(client).json()["access_token"])


def _make_cashier(client, owner):
    client.post("/api/users", headers=owner,
                json={"name": "Asha", "email": "asha@shop.in", "password": "cashierpass1"})
    return auth_headers(
        client.post("/api/auth/login", json={"email": "asha@shop.in", "password": "cashierpass1"}).json()["access_token"]
    )


def test_product_created_via_purchase_appears_in_catalogue(client):
    h = _owner(client)
    p = seed_product(client, h, code="TS-001", name="Cotton Saree")
    got = client.get(f"/api/products/{p['id']}", headers=h)
    assert got.status_code == 200
    assert got.json()["product_code"] == "TS-001"
    assert got.json()["unit"] == "NOS"


def test_direct_create_and_delete_are_gone(client):
    h = _owner(client)
    assert client.post("/api/products", headers=h, json={"name": "X"}).status_code in (404, 405)
    p = seed_product(client, h, code="TS-002")
    assert client.delete(f"/api/products/{p['id']}", headers=h).status_code in (404, 405)


def test_edit_recomputes_selling_price(client):
    h = _owner(client)
    p = seed_product(client, h, code="TS-003", purchase_price=100, margin_type="amount", margin_value=20)
    assert p["selling_price"] == 120.0
    upd = client.put(f"/api/products/{p['id']}", headers=h,
                     json={"margin_type": "percentage", "margin_value": 25})
    assert upd.status_code == 200
    assert upd.json()["selling_price"] == 125.0  # 100 * 1.25


def test_deactivate_via_edit(client):
    h = _owner(client)
    p = seed_product(client, h, code="TS-004")
    upd = client.put(f"/api/products/{p['id']}", headers=h, json={"is_active": False})
    assert upd.status_code == 200 and upd.json()["is_active"] is False


def test_search_and_pagination(client):
    h = _owner(client)
    for i in range(5):
        seed_product(client, h, code=f"P-{i}", name=f"Item {i}", qty=1)
    seed_product(client, h, code="ZZ", name="Zebra Towel", qty=1)
    page1 = client.get("/api/products?page=1&limit=2", headers=h).json()
    assert page1["total"] == 6 and len(page1["items"]) == 2
    found = client.get("/api/products?search=zebra", headers=h).json()
    assert found["total"] == 1 and found["items"][0]["name"] == "Zebra Towel"


def test_cashier_can_read_but_not_edit(client):
    owner = _owner(client)
    p = seed_product(client, owner, code="TS-005")
    cashier = _make_cashier(client, owner)
    assert client.get("/api/products", headers=cashier).status_code == 200
    assert client.put(f"/api/products/{p['id']}", headers=cashier, json={"is_active": False}).status_code == 403


def test_products_are_tenant_isolated(client):
    a = _owner(client)
    pa = seed_product(client, a, code="A-1", name="A Product")
    b = auth_headers(register(client, business_name="B Store", email="b@b.in").json()["access_token"])
    b_list = client.get("/api/products", headers=b).json()
    assert b_list["total"] == 0
    assert client.get(f"/api/products/{pa['id']}", headers=b).status_code == 404
