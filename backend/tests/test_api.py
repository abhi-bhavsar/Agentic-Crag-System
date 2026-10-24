import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "vector_db_backend" in data

def test_system_config_endpoint():
    response = client.get("/api/system/config")
    assert response.status_code == 200
    data = response.json()
    assert "default_model" in data
    assert "embedding_dim" in data

def test_documents_list_endpoint():
    response = client.get("/api/documents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_chat_greeting_endpoint():
    response = client.post("/api/chat", json={"message": "hello"})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["traces"]) > 0
