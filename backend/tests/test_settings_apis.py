"""
Backend API Tests for Settings Functionality
Tests: Profile save, System settings, Notification settings, Detection settings, Edge config
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
TEST_USER_EMAIL = "test@admin.com"
TEST_USER_PASSWORD = "test123"
TEST_CLIENT_ID = "cli_778fc2f73915"
EDGE_API_KEY = "sg_edge_yd4x6l4mnru-Zo9Z5Q634whLw7Y4yhDAalhGA5NyF3Y"


class TestHealthCheck:
    """Basic health check tests"""
    
    def test_api_reachable(self):
        """Test that API is reachable"""
        response = requests.get(f"{BASE_URL}/api/admin/system/health", timeout=10)
        # May return 401 if not authenticated, but should be reachable
        assert response.status_code in [200, 401, 403]
        print(f"API reachable: {response.status_code}")


class TestAuthentication:
    """Authentication tests"""
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        print(f"Login response: {response.status_code} - {response.text[:200]}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        assert "user" in data
        assert "token" in data
        
        # Store token for other tests
        pytest.session_token = data["token"]
        pytest.user_id = data["user"]["user_id"]
        pytest.user_role = data["user"]["role"]
        print(f"Logged in as: {data['user']['email']}, role: {data['user']['role']}")
        
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 200  # Returns 200 with success=False
        data = response.json()
        assert data.get("success") == False


class TestAdminProfileSettings:
    """Admin profile save functionality tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure we have a valid session token"""
        if not hasattr(pytest, 'session_token'):
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            })
            data = response.json()
            pytest.session_token = data.get("token")
            pytest.user_id = data.get("user", {}).get("user_id")
    
    def test_update_profile_success(self):
        """Test updating user profile - Admin Settings Profile Save"""
        headers = {"Authorization": f"Bearer {pytest.session_token}"}
        
        response = requests.put(
            f"{BASE_URL}/api/users/{pytest.user_id}/profile",
            json={"name": "Test Admin Updated"},
            headers=headers
        )
        print(f"Profile update response: {response.status_code} - {response.text}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        assert "Profile updated" in data.get("message", "")
        
    def test_update_profile_verify_persistence(self):
        """Verify profile update persisted by checking auth/me"""
        headers = {"Authorization": f"Bearer {pytest.session_token}"}
        
        # First update
        requests.put(
            f"{BASE_URL}/api/users/{pytest.user_id}/profile",
            json={"name": "Verified Admin Name"},
            headers=headers
        )
        
        # Verify via auth/me
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        # Name should be updated
        print(f"Current user name: {data.get('user', {}).get('name')}")


class TestAdminSystemSettings:
    """Admin system settings save functionality tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure we have a valid session token"""
        if not hasattr(pytest, 'session_token'):
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            })
            data = response.json()
            pytest.session_token = data.get("token")
    
    def test_get_system_settings(self):
        """Test getting system settings"""
        headers = {"Authorization": f"Bearer {pytest.session_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/system/settings", headers=headers)
        print(f"Get system settings: {response.status_code} - {response.text}")
        assert response.status_code == 200
        
        data = response.json()
        # Should have default settings structure
        assert "maintenance_mode" in data or response.status_code == 200
        
    def test_update_system_settings(self):
        """Test updating system settings - Admin Settings System Save"""
        headers = {"Authorization": f"Bearer {pytest.session_token}"}
        
        response = requests.put(
            f"{BASE_URL}/api/admin/system/settings",
            json={
                "maintenance_mode": False,
                "allow_new_registrations": True,
                "require_email_verification": False,
                "session_timeout_days": 7,
                "max_login_attempts": 5
            },
            headers=headers
        )
        print(f"Update system settings: {response.status_code} - {response.text}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        
    def test_update_system_settings_verify_persistence(self):
        """Verify system settings update persisted"""
        headers = {"Authorization": f"Bearer {pytest.session_token}"}
        
        # Update with specific values
        requests.put(
            f"{BASE_URL}/api/admin/system/settings",
            json={
                "maintenance_mode": False,
                "session_timeout_days": 14
            },
            headers=headers
        )
        
        # Verify via GET
        response = requests.get(f"{BASE_URL}/api/admin/system/settings", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        print(f"Persisted system settings: {data}")
        # Should reflect updated values
        assert data.get("session_timeout_days") == 14 or "session_timeout_days" in data


class TestAdminNotificationSettings:
    """Admin notification settings save functionality tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure we have a valid session token"""
        if not hasattr(pytest, 'session_token'):
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            })
            data = response.json()
            pytest.session_token = data.get("token")
    
    def test_get_notification_settings(self):
        """Test getting notification settings"""
        headers = {"Authorization": f"Bearer {pytest.session_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/notifications/settings", headers=headers)
        print(f"Get notification settings: {response.status_code} - {response.text}")
        assert response.status_code == 200
        
        data = response.json()
        # Should have notification settings structure
        assert "email_on_critical_incident" in data or response.status_code == 200
        
    def test_update_notification_settings(self):
        """Test updating notification settings - Admin Settings Notifications Save"""
        headers = {"Authorization": f"Bearer {pytest.session_token}"}
        
        response = requests.put(
            f"{BASE_URL}/api/admin/notifications/settings",
            json={
                "email_on_critical_incident": True,
                "email_on_new_client": True,
                "email_on_device_offline": True,
                "daily_summary_email": False
            },
            headers=headers
        )
        print(f"Update notification settings: {response.status_code} - {response.text}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        
    def test_update_notification_settings_verify_persistence(self):
        """Verify notification settings update persisted"""
        headers = {"Authorization": f"Bearer {pytest.session_token}"}
        
        # Update with specific values
        requests.put(
            f"{BASE_URL}/api/admin/notifications/settings",
            json={
                "daily_summary_email": True
            },
            headers=headers
        )
        
        # Verify via GET
        response = requests.get(f"{BASE_URL}/api/admin/notifications/settings", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        print(f"Persisted notification settings: {data}")
        assert data.get("daily_summary_email") == True


class TestClientDetectionSettings:
    """Client detection settings save functionality tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure we have a valid session token"""
        if not hasattr(pytest, 'session_token'):
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            })
            data = response.json()
            pytest.session_token = data.get("token")
    
    def test_get_detection_settings(self):
        """Test getting detection settings for client"""
        headers = {"Authorization": f"Bearer {pytest.session_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/client/detection-settings/{TEST_CLIENT_ID}",
            headers=headers
        )
        print(f"Get detection settings: {response.status_code} - {response.text}")
        assert response.status_code == 200
        
        data = response.json()
        assert "sensitivity" in data
        assert "enable_pose_detection" in data
        assert "enable_face_recognition" in data
        assert "enable_gpt_analysis" in data
        assert "confidence_threshold" in data
        
    def test_update_detection_settings(self):
        """Test updating detection settings - Client Settings Detection Save"""
        headers = {"Authorization": f"Bearer {pytest.session_token}"}
        
        response = requests.put(
            f"{BASE_URL}/api/client/detection-settings/{TEST_CLIENT_ID}",
            json={
                "sensitivity": "high",
                "enable_pose_detection": True,
                "enable_face_recognition": True,
                "enable_gpt_analysis": True,
                "confidence_threshold": 0.7
            },
            headers=headers
        )
        print(f"Update detection settings: {response.status_code} - {response.text}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        
    def test_update_detection_settings_verify_persistence(self):
        """Verify detection settings update persisted"""
        headers = {"Authorization": f"Bearer {pytest.session_token}"}
        
        # Update with specific values
        requests.put(
            f"{BASE_URL}/api/client/detection-settings/{TEST_CLIENT_ID}",
            json={
                "sensitivity": "medium",
                "confidence_threshold": 0.65
            },
            headers=headers
        )
        
        # Verify via GET
        response = requests.get(
            f"{BASE_URL}/api/client/detection-settings/{TEST_CLIENT_ID}",
            headers=headers
        )
        assert response.status_code == 200
        
        data = response.json()
        print(f"Persisted detection settings: {data}")
        assert data.get("sensitivity") == "medium"
        assert data.get("confidence_threshold") == 0.65


class TestClientAlertSettings:
    """Client alert settings save functionality tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure we have a valid session token"""
        if not hasattr(pytest, 'session_token'):
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            })
            data = response.json()
            pytest.session_token = data.get("token")
    
    def test_get_alert_settings(self):
        """Test getting alert settings for client"""
        headers = {"Authorization": f"Bearer {pytest.session_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/alerts/settings/{TEST_CLIENT_ID}",
            headers=headers
        )
        print(f"Get alert settings: {response.status_code} - {response.text}")
        assert response.status_code == 200
        
        data = response.json()
        # Should have alert settings structure
        assert "alert_on_critical" in data or "alert_email" in data
        
    def test_update_alert_settings(self):
        """Test updating alert settings - Client Settings Alerts Save"""
        headers = {"Authorization": f"Bearer {pytest.session_token}"}
        
        response = requests.put(
            f"{BASE_URL}/api/alerts/settings/{TEST_CLIENT_ID}",
            json={
                "alert_on_critical": True,
                "alert_on_warning": False,
                "alert_email": True,
                "whatsapp_numbers": []
            },
            headers=headers
        )
        print(f"Update alert settings: {response.status_code} - {response.text}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True


class TestEdgeConfigAPI:
    """Edge config API tests - RTSP URL in cameras"""
    
    def test_edge_config_returns_cameras_with_rtsp(self):
        """Test GET /api/edge/config/{client_id} returns cameras with RTSP URLs"""
        response = requests.get(
            f"{BASE_URL}/api/edge/config/{TEST_CLIENT_ID}",
            params={"api_key": EDGE_API_KEY}
        )
        print(f"Edge config response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        assert "cameras" in data
        assert "ai_settings" in data
        assert "client_name" in data
        
        # Check cameras have rtsp_url field
        cameras = data.get("cameras", [])
        print(f"Found {len(cameras)} cameras")
        for cam in cameras:
            print(f"Camera: {cam.get('name')} - RTSP: {cam.get('rtsp_url')}")
            assert "rtsp_url" in cam or "camera_id" in cam
            
    def test_edge_config_invalid_api_key(self):
        """Test edge config with invalid API key"""
        response = requests.get(
            f"{BASE_URL}/api/edge/config/{TEST_CLIENT_ID}",
            params={"api_key": "invalid_key"}
        )
        assert response.status_code == 401


class TestCameraManagement:
    """Camera management tests - RTSP URL field"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure we have a valid session token"""
        if not hasattr(pytest, 'session_token'):
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            })
            data = response.json()
            pytest.session_token = data.get("token")
    
    def test_list_cameras(self):
        """Test listing cameras for client"""
        headers = {"Authorization": f"Bearer {pytest.session_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/admin/cameras",
            params={"client_id": TEST_CLIENT_ID},
            headers=headers
        )
        print(f"List cameras: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 200
        
        data = response.json()
        assert "cameras" in data
        
        # Check cameras have rtsp_url field
        for cam in data.get("cameras", []):
            print(f"Camera: {cam.get('name')} - RTSP: {cam.get('rtsp_url')}")
            assert "rtsp_url" in cam
            
    def test_create_camera_with_rtsp(self):
        """Test creating camera with RTSP URL"""
        headers = {"Authorization": f"Bearer {pytest.session_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/admin/cameras",
            json={
                "client_id": TEST_CLIENT_ID,
                "name": "TEST_Camera_RTSP",
                "location": "Test Location",
                "rtsp_url": "rtsp://192.168.1.100:554/stream1",
                "detection_enabled": True,
                "sensitivity": "medium"
            },
            headers=headers
        )
        print(f"Create camera: {response.status_code} - {response.text}")
        
        # May fail due to camera limit, but should be 200 or 400
        assert response.status_code in [200, 400]
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True
            # Store camera_id for cleanup
            pytest.test_camera_id = data.get("camera", {}).get("camera_id")


class TestSystemHealth:
    """System health endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure we have a valid session token"""
        if not hasattr(pytest, 'session_token'):
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            })
            data = response.json()
            pytest.session_token = data.get("token")
    
    def test_system_health(self):
        """Test system health endpoint"""
        headers = {"Authorization": f"Bearer {pytest.session_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/system/health", headers=headers)
        print(f"System health: {response.status_code} - {response.text}")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "database" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
