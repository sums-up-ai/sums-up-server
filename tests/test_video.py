from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_process_video():
    response = client.post("/video", json={"videoId": "test123"})
    assert response.status_code == 200
    assert response.json() == {"message": "Your video ID: test123"}
