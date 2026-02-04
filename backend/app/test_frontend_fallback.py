import os
from fastapi.testclient import TestClient
from .main import app

def test_frontend_fallback():
    # Ensure static directory and index.html exist for the test
    os.makedirs("static", exist_ok=True)
    with open("static/index.html", "w") as f:
        f.write("<html><body>Frontend Index</body></html>")

    client = TestClient(app)

    # 1. Test existing API route
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # 2. Test non-existent API route (should be 404)
    response = client.get("/api/nonexistent")
    assert response.status_code == 404

    # 3. Test frontend route (should fallback to index.html)
    response = client.get("/login")
    assert response.status_code == 200
    assert "Frontend Index" in response.text

    # 4. Test nested frontend route
    response = client.get("/dashboard/tasks/1")
    assert response.status_code == 200
    assert "Frontend Index" in response.text

if __name__ == "__main__":
    test_frontend_fallback()
