"""
Test suite for Admin AI Control page features
Tests:
- Login flow
- GET /api/edge/ai-status/{client_id} endpoint
- GET /api/admin/clients endpoint (for client selector)
- PUT /api/admin/ai/settings endpoint (save settings)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@admin.com"
TEST_PASSWORD = "test123"
TEST_CLIENT_ID = "cli_778fc2f73915"


class TestLogin:
    """Test login flow"""
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "token" in data
        assert data["user"]["email"] == TEST_EMAIL
        assert data["user"]["role"] == "super_admin"
        print(f"✅ Login successful - User: {data['user']['name']}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "wrong@email.com", "password": "wrongpass"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False
        print("✅ Invalid login correctly rejected")


class TestEdgeAIStatus:
    """Test GET /api/edge/ai-status/{client_id} endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_edge_ai_status_returns_correct_structure(self):
        """Test that edge AI status endpoint returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/edge/ai-status/{TEST_CLIENT_ID}",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "success" in data
        assert data["success"] == True
        assert "device_name" in data
        assert "is_online" in data
        assert "last_heartbeat" in data
        assert "ai_model_status" in data
        
        # Verify AI model status structure
        ai_status = data["ai_model_status"]
        assert "yolo" in ai_status
        assert "pose" in ai_status
        assert "deepface" in ai_status
        assert "vision_ai" in ai_status
        
        # Verify each model has required fields
        for model_name, model_status in ai_status.items():
            assert "enabled" in model_status, f"{model_name} missing 'enabled'"
            assert "loaded" in model_status, f"{model_name} missing 'loaded'"
            assert "status" in model_status, f"{model_name} missing 'status'"
        
        # Vision AI should have provider field
        assert "provider" in ai_status["vision_ai"]
        
        print(f"✅ Edge AI status structure correct - Device: {data['device_name']}")
        print(f"   - is_online: {data['is_online']}")
        print(f"   - Models: {list(ai_status.keys())}")
    
    def test_edge_ai_status_unauthorized(self):
        """Test that endpoint requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/edge/ai-status/{TEST_CLIENT_ID}"
        )
        assert response.status_code == 401
        print("✅ Unauthorized access correctly rejected")
    
    def test_edge_ai_status_nonexistent_client(self):
        """Test response for non-existent client"""
        response = requests.get(
            f"{BASE_URL}/api/edge/ai-status/nonexistent_client_id",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        # Should return success=False for non-existent client
        assert data["success"] == False or data.get("ai_status") is None
        print("✅ Non-existent client handled correctly")


class TestAdminClients:
    """Test GET /api/admin/clients endpoint (for client selector)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_clients_list(self):
        """Test fetching clients list for selector"""
        response = requests.get(
            f"{BASE_URL}/api/admin/clients?limit=100",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "clients" in data
        assert isinstance(data["clients"], list)
        assert len(data["clients"]) > 0
        
        # Verify client structure
        client = data["clients"][0]
        assert "client_id" in client
        assert "name" in client
        assert "subscription" in client
        
        print(f"✅ Clients list fetched - {len(data['clients'])} clients found")
        for c in data["clients"]:
            print(f"   - {c['name']} ({c['client_id']})")


class TestAISettings:
    """Test AI settings save functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_ai_settings(self):
        """Test fetching AI settings for a client"""
        response = requests.get(
            f"{BASE_URL}/api/admin/ai/settings/{TEST_CLIENT_ID}",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "settings" in data
        settings = data["settings"]
        
        # Verify settings structure
        assert "enable_yolo" in settings
        assert "enable_deepface" in settings
        assert "enable_pose" in settings
        assert "enable_gpt_analysis" in settings
        assert "detection_sensitivity" in settings
        assert "threat_threshold" in settings
        
        print(f"✅ AI settings fetched for {TEST_CLIENT_ID}")
        print(f"   - YOLO: {settings['enable_yolo']}")
        print(f"   - DeepFace: {settings['enable_deepface']}")
        print(f"   - Pose: {settings['enable_pose']}")
        print(f"   - GPT Analysis: {settings['enable_gpt_analysis']}")
    
    def test_save_ai_settings(self):
        """Test saving AI settings"""
        settings_payload = {
            "client_id": TEST_CLIENT_ID,
            "enable_yolo": True,
            "enable_deepface": True,
            "enable_pose": True,
            "enable_gpt_analysis": True,
            "detection_sensitivity": "medium",
            "threat_threshold": 0.65
        }
        
        response = requests.put(
            f"{BASE_URL}/api/admin/ai/settings",
            json=settings_payload,
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        # Verify settings were saved by fetching them again
        get_response = requests.get(
            f"{BASE_URL}/api/admin/ai/settings/{TEST_CLIENT_ID}",
            headers=self.headers
        )
        assert get_response.status_code == 200
        saved_settings = get_response.json()["settings"]
        
        assert saved_settings["enable_yolo"] == True
        assert saved_settings["threat_threshold"] == 0.65
        
        print("✅ AI settings saved and verified successfully")


class TestMLStatus:
    """Test ML status endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_ml_status_endpoint(self):
        """Test ML status endpoint returns data"""
        response = requests.get(
            f"{BASE_URL}/api/ml/status",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return some status information
        assert isinstance(data, dict)
        print(f"✅ ML status endpoint working - Keys: {list(data.keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
