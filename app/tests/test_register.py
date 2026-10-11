import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.routes.auth_routes import router

app = FastAPI()
app.include_router(router)

client = TestClient(app)

VALID_REGISTER_PAYLOAD = {
    "email": "test@company.com",
    "employee_id": "EMP123",
    "name": "John Doe",
    "age": 30,
    "gender": "MALE",
    "phone": "+1234567890",
    "department": "Engineering",
    "designation": "Software Engineer",
    "role": "EMPLOYEE",
    "password": "strongpassword123"
}

# IMPORTANT: Patch the exact path where `register_user` is imported in your router file
@patch("app.routes.auth_routes.register_user", new_callable=AsyncMock)
def test_register_success(mock_register):
    # Mock a successful response from the service
    mock_register.return_value = (True, "mocked_mongo_id_5f12b...")

    response = client.post("/auth/register", json=VALID_REGISTER_PAYLOAD)

    assert response.status_code == 200
    assert response.json() == {
        "message": "User Registered Successfully",
        "user_id": "mocked_mongo_id_5f12b..."
    }
    mock_register.assert_called_once()


@patch("app.routes.auth_routes.register_user", new_callable=AsyncMock)
def test_register_manager_not_found(mock_register):
    # Mock a failure response from the service (e.g., manager_id is invalid)
    error_msg = "manager_id does not match an existing employee"
    mock_register.return_value = (False, error_msg)

    payload = VALID_REGISTER_PAYLOAD.copy()
    payload["manager_id"] = "INVALID_MANAGER"

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": error_msg}


def test_register_validation_error_age():
    payload = VALID_REGISTER_PAYLOAD.copy()
    payload["age"] = 16  # Invalid age, should trigger validation error

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 422
    assert "age" in response.text