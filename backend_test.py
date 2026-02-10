#!/usr/bin/env python3

import requests
import sys
import json
import time
from datetime import datetime
from pathlib import Path

class ShopliftingDetectionTester:
    def __init__(self, base_url="https://edgeai-1.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.uploaded_video_id = None
        
        # Sample video URLs
        self.shoplifting_video_url = "https://customer-assets.emergentagent.com/job_securemart-5/artifacts/9ptu5xam_shoplifting-1.mp4"
        self.normal_video_url = "https://customer-assets.emergentagent.com/job_securemart-5/artifacts/csje1ghn_normal-1.mp4"

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, timeout=30):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {}
        
        if data and not files:
            headers['Content-Type'] = 'application/json'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                if files:
                    response = requests.post(url, data=data, files=files, timeout=timeout)
                else:
                    response = requests.post(url, json=data, headers=headers, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text[:200]}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def download_sample_video(self, video_url, filename):
        """Download sample video for testing"""
        print(f"\n📥 Downloading sample video: {filename}")
        try:
            response = requests.get(video_url, timeout=60)
            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Downloaded {filename} ({len(response.content)} bytes)")
                return True
            else:
                print(f"❌ Failed to download {filename} - Status: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Download error: {str(e)}")
            return False

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root API", "GET", "", 200)

    def test_dashboard_stats(self):
        """Test dashboard stats endpoint"""
        return self.run_test("Dashboard Stats", "GET", "dashboard/stats", 200)

    def test_analytics(self):
        """Test analytics endpoint"""
        return self.run_test("Analytics", "GET", "analytics", 200)

    def test_get_videos(self):
        """Test get videos endpoint"""
        return self.run_test("Get Videos", "GET", "videos", 200)

    def test_get_incidents(self):
        """Test get incidents endpoint"""
        return self.run_test("Get Incidents", "GET", "incidents", 200)

    def test_upload_video(self, video_file_path, store_type="convenience"):
        """Test video upload"""
        if not Path(video_file_path).exists():
            print(f"❌ Video file not found: {video_file_path}")
            return False, {}
        
        try:
            with open(video_file_path, 'rb') as f:
                files = {'file': (Path(video_file_path).name, f, 'video/mp4')}
                data = {'store_type': store_type}
                
                success, response_data = self.run_test(
                    f"Upload Video ({Path(video_file_path).name})", 
                    "POST", 
                    "videos/upload", 
                    200, 
                    data=data, 
                    files=files,
                    timeout=120
                )
                
                if success and 'id' in response_data:
                    self.uploaded_video_id = response_data['id']
                    print(f"   Video ID: {self.uploaded_video_id}")
                
                return success, response_data
        except Exception as e:
            print(f"❌ Upload error: {str(e)}")
            return False, {}

    def test_analyze_video(self, video_id=None, max_frames=3):
        """Test video analysis"""
        if not video_id:
            video_id = self.uploaded_video_id
        
        if not video_id:
            print("❌ No video ID available for analysis")
            return False, {}
        
        print(f"\n🤖 Starting AI analysis (this may take 30-60 seconds)...")
        success, response_data = self.run_test(
            f"Analyze Video ({video_id})", 
            "POST", 
            f"videos/{video_id}/analyze?max_frames={max_frames}", 
            200,
            timeout=180  # Longer timeout for AI analysis
        )
        
        if success:
            incidents_count = response_data.get('incidents_detected', 0)
            print(f"   🎯 Analysis complete: {incidents_count} incidents detected")
            
            if incidents_count > 0:
                print("   📋 Detected incidents:")
                for i, incident in enumerate(response_data.get('incidents', [])[:3]):
                    print(f"      {i+1}. {incident.get('severity', 'unknown').upper()}: {incident.get('description', 'No description')}")
        
        return success, response_data

    def test_get_video_details(self, video_id=None):
        """Test getting specific video details"""
        if not video_id:
            video_id = self.uploaded_video_id
        
        if not video_id:
            print("❌ No video ID available")
            return False, {}
        
        return self.run_test(f"Get Video Details ({video_id})", "GET", f"videos/{video_id}", 200)

    def test_incident_filtering(self):
        """Test incident filtering"""
        # Test severity filter
        success1, _ = self.run_test("Filter Incidents (Critical)", "GET", "incidents?severity=critical", 200)
        success2, _ = self.run_test("Filter Incidents (Warning)", "GET", "incidents?severity=warning", 200)
        success3, _ = self.run_test("Filter Incidents (Store Type)", "GET", "incidents?store_type=convenience", 200)
        
        return success1 and success2 and success3

def main():
    print("🛡️  SHOPLIFTING DETECTION SYSTEM - API TESTING")
    print("=" * 60)
    
    tester = ShopliftingDetectionTester()
    
    # Test basic endpoints first
    print("\n📡 TESTING BASIC API ENDPOINTS")
    print("-" * 40)
    
    tester.test_root_endpoint()
    tester.test_dashboard_stats()
    tester.test_analytics()
    tester.test_get_videos()
    tester.test_get_incidents()
    
    # Test video upload and analysis workflow
    print("\n🎥 TESTING VIDEO UPLOAD & ANALYSIS WORKFLOW")
    print("-" * 50)
    
    # Download sample video
    video_filename = "test_shoplifting_video.mp4"
    if tester.download_sample_video(tester.shoplifting_video_url, video_filename):
        # Upload video
        upload_success, upload_data = tester.test_upload_video(video_filename, "convenience")
        
        if upload_success:
            # Get video details
            tester.test_get_video_details()
            
            # Analyze video
            analyze_success, analyze_data = tester.test_analyze_video(max_frames=3)
            
            if analyze_success:
                # Test getting updated video details
                tester.test_get_video_details()
                
                # Test incident filtering
                tester.test_incident_filtering()
        
        # Clean up
        try:
            Path(video_filename).unlink()
            print(f"🗑️  Cleaned up {video_filename}")
        except:
            pass
    
    # Test with normal video too
    print("\n🎥 TESTING WITH NORMAL VIDEO")
    print("-" * 35)
    
    normal_video_filename = "test_normal_video.mp4"
    if tester.download_sample_video(tester.normal_video_url, normal_video_filename):
        upload_success, _ = tester.test_upload_video(normal_video_filename, "liquor")
        if upload_success:
            tester.test_analyze_video(max_frames=2)
        
        # Clean up
        try:
            Path(normal_video_filename).unlink()
            print(f"🗑️  Cleaned up {normal_video_filename}")
        except:
            pass
    
    # Final results
    print("\n" + "=" * 60)
    print(f"📊 FINAL RESULTS: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed! Backend API is working correctly.")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed. Check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())