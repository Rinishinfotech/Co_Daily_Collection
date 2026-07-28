"""Backend API tests for LedgerFlow with authentication + role isolation."""
import os
import time
import uuid

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_PHONE = "9999999999"
ADMIN_PASSWORD = "Admin@123"
EMPLOYEE_PHONE = "+91 98765 42100"
EMPLOYEE_TEMP_PASSWORD = "Welcome@123"


# -- helpers ---------------------------------------------------------------
def _login(phone: str, password: str):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"phone": phone, "password": password})
    assert r.status_code == 200, f"login failed for {phone}: {r.status_code} {r.text}"
    data = r.json()
    token = data["token"]
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s, data


@pytest.fixture(scope="session")
def admin():
    session, data = _login(ADMIN_PHONE, ADMIN_PASSWORD)
    return {"session": session, "user": data["user"]}


@pytest.fixture(scope="session")
def new_employee(admin):
    """Create a fresh employee we can freely mutate/change password on."""
    phone = f"+91 900000{int(time.time()) % 10000:04d}"
    temp_password = "TempPass@123"
    r = admin["session"].post(
        f"{API}/employees",
        json={"name": "TEST_AuthEmp", "phone": phone, "territory": "TEST_Zone",
              "temporary_password": temp_password},
    )
    assert r.status_code == 200, r.text
    emp = r.json()
    return {"employee": emp, "phone": phone, "temp_password": temp_password}


@pytest.fixture(scope="session")
def employee(new_employee):
    session, data = _login(new_employee["phone"], new_employee["temp_password"])
    return {"session": session, "user": data["user"], "meta": new_employee}


# -- auth / login ----------------------------------------------------------
class TestAuth:
    def test_admin_login(self):
        r = requests.post(f"{API}/auth/login",
                          json={"phone": ADMIN_PHONE, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        body = r.json()
        assert body["user"]["role"] == "admin"
        assert body["user"]["phone"] == ADMIN_PHONE
        assert "password_hash" not in body["user"]
        assert isinstance(body["token"], str) and len(body["token"]) > 20

    def test_invalid_password(self):
        r = requests.post(f"{API}/auth/login",
                          json={"phone": ADMIN_PHONE, "password": "WrongPass!!"})
        assert r.status_code == 401

    def test_unknown_phone(self):
        r = requests.post(f"{API}/auth/login",
                          json={"phone": "0000000000", "password": "Whatever@123"})
        assert r.status_code == 401

    def test_me_requires_auth(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_me_admin(self, admin):
        r = admin["session"].get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["role"] == "admin"

    def test_employee_must_change_password_flag(self, employee):
        r = employee["session"].get(f"{API}/auth/me")
        assert r.status_code == 200
        me = r.json()
        assert me["role"] == "employee"
        assert me["must_change_password"] is True

    def test_seeded_employee_login_and_flag(self):
        # Seeded employee should still login with Welcome@123 as long as not overridden.
        r = requests.post(f"{API}/auth/login",
                          json={"phone": EMPLOYEE_PHONE, "password": EMPLOYEE_TEMP_PASSWORD})
        if r.status_code == 401:
            pytest.skip("Seed employee password already changed; skipping")
        assert r.status_code == 200
        assert r.json()["user"]["must_change_password"] is True


# -- role isolation --------------------------------------------------------
class TestRoleIsolation:
    def test_employee_blocked_from_employees_list(self, employee):
        r = employee["session"].get(f"{API}/employees")
        assert r.status_code == 403

    def test_employee_blocked_from_add_employee(self, employee):
        r = employee["session"].post(f"{API}/employees",
                                     json={"name": "Nope", "phone": "9111111111",
                                           "territory": "ZZ", "temporary_password": "Abcd@1234"})
        assert r.status_code == 403

    def test_employee_blocked_from_vendor_create(self, employee):
        r = employee["session"].post(f"{API}/vendors",
                                     json={"name": "XX", "business_name": "YY",
                                           "phone": "9111111111", "address": "somewhere"})
        assert r.status_code == 403

    def test_employee_blocked_from_vendor_update(self, employee, admin):
        vendors = admin["session"].get(f"{API}/vendors").json()
        vid = vendors[0]["id"]
        r = employee["session"].put(f"{API}/vendors/{vid}",
                                    json={"name": "XX", "business_name": "YY",
                                          "phone": "9111111111", "address": "somewhere"})
        assert r.status_code == 403

    def test_employee_blocked_from_vendor_delete(self, employee, admin):
        vendors = admin["session"].get(f"{API}/vendors").json()
        r = employee["session"].delete(f"{API}/vendors/{vendors[0]['id']}")
        assert r.status_code == 403

    def test_employee_blocked_from_employee_activity(self, employee, admin):
        r = employee["session"].get(f"{API}/employees/emp-raj/activity")
        assert r.status_code == 403

    def test_employee_blocked_from_other_employee_collections(self, employee):
        r = employee["session"].get(f"{API}/collections", params={"employee_id": "emp-raj"})
        assert r.status_code == 403

    def test_employee_blocked_from_other_employee_dashboard(self, employee):
        r = employee["session"].get(f"{API}/dashboard", params={"employee_id": "emp-raj"})
        assert r.status_code == 403

    def test_admin_cannot_post_collection(self, admin):
        r = admin["session"].post(f"{API}/collections",
                                  json={"vendor_name": "TT", "amount": 10, "payment_mode": "Cash"})
        assert r.status_code == 403

    def test_admin_cannot_post_expense(self, admin):
        r = admin["session"].post(f"{API}/expenses",
                                  json={"category": "Fuel", "amount": 5})
        assert r.status_code == 403


# -- admin profile / employee mgmt -----------------------------------------
class TestAdminFlows:
    def test_admin_profile(self, admin):
        r = admin["session"].get(f"{API}/profile")
        assert r.status_code == 200
        body = r.json()
        assert body["account"]["role"] == "admin"
        assert body["employee"] is None

    def test_admin_lists_employees(self, admin):
        r = admin["session"].get(f"{API}/employees")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) > 0

    def test_admin_employee_activity(self, admin):
        r = admin["session"].get(f"{API}/employees/emp-raj/activity")
        assert r.status_code == 200
        d = r.json()
        for key in ("employee", "today_total", "today_vendors", "collections", "expenses"):
            assert key in d
        assert d["employee"]["id"] == "emp-raj"

    def test_admin_dashboard(self, admin):
        r = admin["session"].get(f"{API}/dashboard")
        assert r.status_code == 200
        for k in ("today_collection", "monthly_collection", "trend", "active_vendors", "active_employees"):
            assert k in r.json()

    def test_duplicate_phone_rejected(self, admin, new_employee):
        r = admin["session"].post(
            f"{API}/employees",
            json={"name": "Dup", "phone": new_employee["phone"], "territory": "ZZ",
                  "temporary_password": "Something@123"},
        )
        assert r.status_code == 400


# -- employee flows --------------------------------------------------------
class TestEmployeeFlows:
    def test_profile_shows_only_own(self, employee):
        r = employee["session"].get(f"{API}/profile")
        assert r.status_code == 200
        body = r.json()
        assert body["account"]["role"] == "employee"
        assert body["employee"]["id"] == employee["user"]["employee_id"]

    def test_change_password_flow(self, employee):
        new_password = "NewPass@2026"
        r = employee["session"].post(
            f"{API}/auth/change-password",
            json={"current_password": employee["meta"]["temp_password"],
                  "new_password": new_password},
        )
        assert r.status_code == 200
        # old password should not work
        r_old = requests.post(f"{API}/auth/login",
                              json={"phone": employee["meta"]["phone"],
                                    "password": employee["meta"]["temp_password"]})
        assert r_old.status_code == 401
        # new password should work
        r_new = requests.post(f"{API}/auth/login",
                              json={"phone": employee["meta"]["phone"],
                                    "password": new_password})
        assert r_new.status_code == 200
        assert r_new.json()["user"]["must_change_password"] is False
        # update fixture session token so subsequent tests still work
        employee["session"].headers.update(
            {"Authorization": f"Bearer {r_new.json()['token']}"}
        )
        employee["meta"]["temp_password"] = new_password  # noqa

    def test_collection_uses_signed_identity(self, employee):
        vendors = requests.get(f"{API}/vendors",
                               headers={"Authorization": employee["session"].headers["Authorization"]}).json()
        payload = {
            "vendor_id": vendors[0]["id"],
            "vendor_name": vendors[0]["business_name"],
            "amount": 500,
            "payment_mode": "UPI",
            "remarks": "TEST_auth_identity",
            # Attempt to spoof another identity — server must ignore
            "employee_id": "emp-raj",
            "employee_name": "Impersonator",
        }
        r = employee["session"].post(f"{API}/collections", json=payload)
        # extra keys should either be silently dropped by pydantic or accepted;
        # in either case server must overwrite identity
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["employee_id"] == employee["user"]["employee_id"]
        assert body["employee_name"] == employee["user"]["name"]
        assert body["receipt_number"].startswith("LFC-")

    def test_expense_uses_signed_identity(self, employee):
        r = employee["session"].post(
            f"{API}/expenses",
            json={"category": "Fuel", "amount": 100, "remarks": "TEST",
                  "employee_id": "emp-raj", "employee_name": "Spoof"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["employee_id"] == employee["user"]["employee_id"]

    def test_employee_dashboard_scoped(self, employee):
        r = employee["session"].get(f"{API}/dashboard")
        assert r.status_code == 200

    def test_employee_collections_scoped(self, employee):
        r = employee["session"].get(f"{API}/collections")
        assert r.status_code == 200
        for c in r.json():
            assert c["employee_id"] == employee["user"]["employee_id"]

    def test_logout(self, employee):
        r = employee["session"].post(f"{API}/auth/logout")
        assert r.status_code == 200


# -- misc ------------------------------------------------------------------
def test_health():
    r = requests.get(f"{API}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_no_mongo_id_leak(admin):
    for ep in ["/vendors", "/employees", "/collections", "/expenses"]:
        r = admin["session"].get(f"{API}{ep}")
        assert r.status_code == 200
        for item in r.json():
            assert "_id" not in item
