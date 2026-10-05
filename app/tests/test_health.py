from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api_gateway_alive():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "NorthStar API Gateway is live"}