"""Tests for deployment config regression:
- MONGO_URL from env not overridden by backend/.env
- CORS accepts production-like origin (wildcard config)
- Health / API reachable
- Login regression (admin + employee)
"""
import os
import requests
import pytest
from pathlib import Path
from dotenv import load_dotenv

BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/') if 'REACT_APP_BACKEND_URL' in os.environ else None
if not BASE_URL:
    # fall back to frontend/.env
    fe = Path('/app/frontend/.env').read_text()
    for line in fe.splitlines():
        if line.startswith('REACT_APP_BACKEND_URL='):
            BASE_URL = line.split('=', 1)[1].strip().rstrip('/')
            break


def test_dotenv_does_not_override_existing_env(monkeypatch):
    """Simulate Kubernetes injecting MONGO_URL; verify load_dotenv preserves it."""
    monkeypatch.setenv('MONGO_URL', 'mongodb://k8s-injected:27017')
    monkeypatch.setenv('CORS_ORIGINS', 'https://prod.example.com')
    load_dotenv(Path('/app/backend/.env'))  # matches server.py call (no override)
    assert os.environ['MONGO_URL'] == 'mongodb://k8s-injected:27017'
    assert os.environ['CORS_ORIGINS'] == 'https://prod.example.com'


def test_server_source_has_no_override_true():
    src = Path('/app/backend/server.py').read_text()
    assert 'load_dotenv' in src
    # Ensure not called with override=True
    assert 'override=True' not in src


def test_api_root_reachable():
    # Any response other than connection error means backend is up
    r = requests.get(f"{BASE_URL}/api/", timeout=15)
    assert r.status_code < 500, f"Got {r.status_code}: {r.text[:200]}"


def test_cors_preflight_allows_production_origin():
    origin = "https://fieldpay-manager-1.preview.emergentagent.com"
    r = requests.options(
        f"{BASE_URL}/api/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=15,
    )
    assert r.status_code in (200, 204), f"Preflight status {r.status_code}"
    allow_origin = r.headers.get("access-control-allow-origin")
    assert allow_origin in (origin, "*"), f"CORS allow-origin={allow_origin!r}"


def test_admin_login():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"phone": "9999999999", "password": "Admin@123"},
        timeout=15,
    )
    assert r.status_code == 200, f"{r.status_code}: {r.text[:300]}"
    data = r.json()
    # Session cookie should be set
    assert any(c for c in r.cookies), "Expected session cookie set"
    assert data.get("user", {}).get("role") in ("admin", "administrator", "ADMIN")


def test_employee_login():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"phone": "+91 98765 42100", "password": "Welcome@123"},
        timeout=15,
    )
    assert r.status_code == 200, f"{r.status_code}: {r.text[:300]}"
    data = r.json()
    assert data.get("user", {}).get("role") in ("employee", "field_employee", "EMPLOYEE")
