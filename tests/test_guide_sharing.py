import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Mock environment variables
os.environ["SECRET_KEY"] = "test_secret_key"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.main import app
from app.database import Base, get_db
from app import models, auth

# Setup test database
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(setup_db):
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

def get_token(client, email, password):
    client.post("/api/auth/register", json={"email": email, "password": password})
    tok_resp = client.post("/api/auth/token", data={"username": email, "password": password})
    return tok_resp.json()["access_token"]

def test_guide_sharing_on_creation(client):
    owner_email = "owner@example.com"
    shared_email = "shared@example.com"
    password = "password123"

    owner_token = get_token(client, owner_email, password)
    shared_token = get_token(client, shared_email, password)

    # Create guide with shared email
    resp = client.post(
        "/api/guides/",
        json={
            "name": "Shared Guide",
            "shortcut": "shared1",
            "description": "Shared",
            "is_public": False,
            "shared_emails": [shared_email],
            "steps": [{"instruction": "Step 1", "selector": "body"}]
        },
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp.status_code == 201
    guide_id = resp.json()["id"]

    # Check if shared user can see it in their guides list
    resp = client.get("/api/guides/", headers={"Authorization": f"Bearer {shared_token}"})
    assert resp.status_code == 200
    guides = resp.json()
    assert any(g["id"] == guide_id for g in guides)

    # Check if shared user can access by shortcut
    resp = client.get("/api/guides/search?shortcut=shared1", headers={"Authorization": f"Bearer {shared_token}"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Shared Guide"

def test_guide_sharing_update(client):
    owner_email = "owner2@example.com"
    shared_email = "shared2@example.com"
    password = "password123"

    owner_token = get_token(client, owner_email, password)
    shared_token = get_token(client, shared_email, password)

    # Create private guide
    resp = client.post(
        "/api/guides/",
        json={
            "name": "Private to Shared",
            "shortcut": "priv2shared",
            "description": "Private",
            "is_public": False,
            "steps": [{"instruction": "Step 1", "selector": "body"}]
        },
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp.status_code == 201
    guide_id = resp.json()["id"]

    # Shared user should NOT see it
    resp = client.get("/api/guides/", headers={"Authorization": f"Bearer {shared_token}"})
    assert not any(g["id"] == guide_id for g in resp.json())

    # Update to share it
    resp = client.put(
        f"/api/guides/{guide_id}",
        json={"shared_emails": [shared_email]},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp.status_code == 200
    assert shared_email in resp.json()["shared_emails"]

    # Shared user should NOW see it
    resp = client.get("/api/guides/", headers={"Authorization": f"Bearer {shared_token}"})
    assert any(g["id"] == guide_id for g in resp.json())

    # Shared user should be able to update guide content
    resp = client.put(
        f"/api/guides/{guide_id}",
        json={"description": "Updated by shared user"},
        headers={"Authorization": f"Bearer {shared_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated by shared user"

    # Shared user should NOT be able to update sharing settings
    resp = client.put(
        f"/api/guides/{guide_id}",
        json={"shared_emails": []},
        headers={"Authorization": f"Bearer {shared_token}"}
    )
    assert resp.status_code == 403

def test_unauthorized_access_prevented(client):
    owner_email = "owner3@example.com"
    other_email = "other@example.com"
    password = "password123"

    owner_token = get_token(client, owner_email, password)
    other_token = get_token(client, other_email, password)

    # Create private guide
    resp = client.post(
        "/api/guides/",
        json={
            "name": "Strictly Private",
            "shortcut": "strict",
            "description": "Private",
            "is_public": False,
            "steps": [{"instruction": "Step 1", "selector": "body"}]
        },
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    guide_id = resp.json()["id"]

    # Other user should NOT be able to access by shortcut
    resp = client.get("/api/guides/search?shortcut=strict", headers={"Authorization": f"Bearer {other_token}"})
    assert resp.status_code == 404

    # Other user should NOT be able to export
    resp = client.get(f"/api/guides/{guide_id}/export-pdf", headers={"Authorization": f"Bearer {other_token}"})
    assert resp.status_code == 403

def test_share_link_functionality(client):
    owner_email = "owner_link@example.com"
    claimant_email = "claimant@example.com"
    password = "password123"

    owner_token = get_token(client, owner_email, password)
    claimant_token = get_token(client, claimant_email, password)

    # 1. Create guide
    resp = client.post(
        "/api/guides/",
        json={
            "name": "Link Guide",
            "shortcut": "link1",
            "description": "Shareable",
            "is_public": False,
            "steps": [{"instruction": "Step 1", "selector": "body"}]
        },
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    guide_id = resp.json()["id"]

    # 2. Generate share token
    resp = client.post(f"/api/guides/{guide_id}/share-token", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 200
    share_token = resp.json()["share_token"]
    assert share_token is not None

    # 3. Claimant should NOT have access yet
    resp = client.get("/api/guides/", headers={"Authorization": f"Bearer {claimant_token}"})
    assert not any(g["id"] == guide_id for g in resp.json())

    # 4. Claimant uses share link to get access
    resp = client.post(f"/api/guides/share/access/{share_token}", headers={"Authorization": f"Bearer {claimant_token}"})
    assert resp.status_code == 200
    assert claimant_email in resp.json()["shared_emails"]

    # 5. Claimant should NOW have access
    resp = client.get("/api/guides/", headers={"Authorization": f"Bearer {claimant_token}"})
    assert any(g["id"] == guide_id for g in resp.json())

    # 6. Invalid token should return 404
    resp = client.post("/api/guides/share/access/invalid_token", headers={"Authorization": f"Bearer {claimant_token}"})
    assert resp.status_code == 404
