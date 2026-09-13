"""
Integration tests for Admin AI Control features.

Required environment variables:
- REACT_APP_BACKEND_URL
- SECUREGUARD_TEST_EMAIL
- SECUREGUARD_TEST_PASSWORD
- SECUREGUARD_TEST_CLIENT_ID
"""

import os

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
TEST_EMAIL = os.environ.get("SECUREGUARD_TEST_EMAIL")
TEST_PASSWORD = os.environ.get("SECUREGUARD_TEST_PASSWORD")
TEST_CLIENT_ID = os.environ.get("SECUREGUARD_TEST_CLIENT_ID")


def require_test_config():
    missing = [
        name
        for name, value in {
            "REACT_APP_BACKEND_URL": BASE_URL,
            "SECUREGUARD_TEST_EMAIL": TEST_EMAIL,
            "SECUREGUARD_TEST_PASSWORD": TEST_PASSWORD,
            "SECUREGUARD_TEST_CLIENT_ID": TEST_CLIENT_ID,
        }.items()
        if not value
    ]
    if missing:
        pytest.skip("Missing integration-test configuration: " + ", ".join(missing))


def login():
    require_test_config()
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        timeout=15,
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert "token" in data
    return data


@pytest.fixture
def auth_headers():
    data = login()
    return {"Authorization": f"Bearer {data['token']}"}


class TestLogin:
    def test_login_success(self):
        data = login()
        assert data["user"]["email"] == TEST_EMAIL

    def test_login_invalid_credentials(self):
        require_test_config()
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "invalid@example.com", "password": "invalid-password"},
            timeout=15,
        )
        assert response.status_code == 200
        assert response.json().get("success") is False


class TestEdgeAIStatus:
    def test_edge_ai_status_structure(self, auth_headers):
        response = requests.get(
            f"{BASE_URL}/api/edge/ai-status/{TEST_CLIENT_ID}",
            headers=auth_headers,
            timeout=15,
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "device_name" in data
        assert "is_online" in data
        assert "last_heartbeat" in data
        assert "ai_model_status" in data

        ai_status = data["ai_model_status"]
        for model_name in ("yolo", "pose", "deepface", "vision_ai"):
            assert model_name in ai_status
            assert "enabled" in ai_status[model_name]
            assert "loaded" in ai_status[model_name]
            assert "status" in ai_status[model_name]
        assert "provider" in ai_status["vision_ai"]

    def test_edge_ai_status_requires_auth(self):
        require_test_config()
        response = requests.get(
            f"{BASE_URL}/api/edge/ai-status/{TEST_CLIENT_ID}", timeout=15
        )
        assert response.status_code == 401


class TestAdminClients:
    def test_get_clients_list(self, auth_headers):
        response = requests.get(
            f"{BASE_URL}/api/admin/clients?limit=100",
            headers=auth_headers,
            timeout=15,
        )
        assert response.status_code == 200
        clients = response.json().get("clients")
        assert isinstance(clients, list)


class TestAISettings:
    def test_get_ai_settings(self, auth_headers):
        response = requests.get(
            f"{BASE_URL}/api/admin/ai/settings/{TEST_CLIENT_ID}",
            headers=auth_headers,
            timeout=15,
        )
        assert response.status_code == 200
        settings = response.json()["settings"]
        for key in (
            "enable_yolo",
            "enable_deepface",
            "enable_pose",
            "enable_gpt_analysis",
            "detection_sensitivity",
            "threat_threshold",
        ):
            assert key in settings


class TestMLStatus:
    def test_ml_status_endpoint(self, auth_headers):
        response = requests.get(
            f"{BASE_URL}/api/ml/status", headers=auth_headers, timeout=15
        )
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
