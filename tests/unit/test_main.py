import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import uuid

from app.main import app, get_user_id
from app.models import TaskIn, TaskDB


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_task_payload():
    return {
        "title": "Study Queen's Gambit",
        "category": "openings",
        "estimated_minutes": 30,
        "due_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
    }


def override_get_user_id():
    return "demo-user-1"


app.dependency_overrides[get_user_id] = override_get_user_id


class TestCreateTask:

    @patch("app.main.get_col")
    @patch("uuid.uuid4", return_value="test-uuid-123")
    @patch("app.main.datetime")
    def test_create_task_success(self, mock_datetime, mock_uuid, mock_get_col, client, sample_task_payload):
        mock_db_col = AsyncMock()
        mock_get_col.return_value = mock_db_col
        mock_db_col.insert_one = AsyncMock()

        test_date = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = test_date
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        response = client.post("/tasks", json=sample_task_payload)
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "test-uuid-123"
        assert data["user_id"] == "demo-user-1"
        assert data["title"] == sample_task_payload["title"]
        assert data["state"] == "todo"
        assert data["priority"] == 50
        assert data["created_at"] == "2023-01-01T12:00:00"

        mock_db_col.insert_one.assert_called_once()

    def test_create_task_invalid_payload(self, client):
        invalid_payload = {
            "title": "",
            "category": "invalid_category",
            "estimated_minutes": -10
        }

        response = client.post("/tasks", json=invalid_payload)
        assert response.status_code == 422

    @patch("app.main.get_col")
    @patch("uuid.uuid4", return_value="test-uuid-x1")
    @patch("app.main.datetime")
    def test_create_task_with_user_injection(self, mock_datetime, mock_uuid, mock_get_col, client):
        mock_db_col = AsyncMock()
        mock_get_col.return_value = mock_db_col
        mock_db_col.insert_one = AsyncMock()

        mock_datetime.utcnow.return_value = datetime(2023, 1, 1)
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        response = client.post("/tasks", json={
            "title": "Injected Test",
            "category": "tactics",
            "estimated_minutes": 15
        })

        assert response.status_code == 200
        assert response.json()["user_id"] == "demo-user-1"

    @patch("app.main.get_col")
    def test_create_task_database_error(self, mock_get_col, client, sample_task_payload):
        mock_get_col.side_effect = RuntimeError("DB client not initialized")

        response = client.post("/tasks", json=sample_task_payload)

        # ✅ Requiere manejo de errores en la API → de momento falla correctamente
        assert response.status_code >= 500

    @patch("app.main.get_col")
    @patch("uuid.uuid4", return_value="test-uuid-789")
    @patch("app.main.datetime")
    def test_create_task_all_fields(self, mock_datetime, mock_uuid, mock_get_col, client):
        mock_db_col = AsyncMock()
        mock_get_col.return_value = mock_db_col
        mock_db_col.insert_one = AsyncMock()

        payload = {
            "title": "Analyze Sicilian Defense",
            "category": "analysis",
            "estimated_minutes": 45,
            "due_at": "2023-06-20T15:00:00"
        }

        dt = datetime(2023, 6, 15, 10, 30)
        mock_datetime.utcnow.return_value = dt
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        response = client.post("/tasks", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "test-uuid-789"
        assert data["created_at"] == "2023-06-15T10:30:00"
