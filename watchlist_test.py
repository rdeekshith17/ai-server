#!/usr/bin/env python3

import requests
import sys
import json
import base64
from datetime import datetime
from pathlib import Path

class WatchlistTester:
    def __init__(self, base_url="https://retail-guard-2.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.created_person_ids = []
        
        # Sample image data (1x1 pixel PNG)
        self.sample_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

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
                    print(f"   Response: {json.dumps(response_data, indent=2)[:300]}...")
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

    def create_sample_image_file(self, filename="test_person.png"):
        """Create a sample image file for testing"""
        try:
            image_data = base64.b64decode(self.sample_image_base64)
            with open(filename, 'wb') as f:
                f.write(image_data)
            print(f"✅ Created sample image: {filename}")
            return True
        except Exception as e:
            print(f"❌ Failed to create sample image: {str(e)}")
            return False

    def test_get_empty_watchlist(self):
        """Test getting empty watchlist"""
        return self.run_test("Get Empty Watchlist", "GET", "watchlist", 200)

    def test_get_watchlist_stats(self):
        """Test getting watchlist statistics"""
        return self.run_test("Get Watchlist Stats", "GET", "watchlist/stats/summary", 200)

    def test_add_person_to_watchlist(self, name="John Doe", alias="JD", threat_level="high"):
        """Test adding a person to watchlist"""
        image_filename = f"test_person_{name.replace(' ', '_').lower()}.png"
        
        if not self.create_sample_image_file(image_filename):
            return False, {}
        
        try:
            with open(image_filename, 'rb') as f:
                files = {'photo': (image_filename, f, 'image/png')}
                data = {
                    'name': name,
                    'alias': alias,
                    'description': f'Test person {name} for watchlist testing',
                    'threat_level': threat_level,
                    'notes': f'Added during automated testing at {datetime.now().isoformat()}'
                }
                
                success, response_data = self.run_test(
                    f"Add Person to Watchlist ({name})", 
                    "POST", 
                    "watchlist", 
                    200, 
                    data=data, 
                    files=files,
                    timeout=60
                )
                
                if success and 'id' in response_data:
                    person_id = response_data['id']
                    self.created_person_ids.append(person_id)
                    print(f"   Person ID: {person_id}")
                
                # Clean up image file
                try:
                    Path(image_filename).unlink()
                except:
                    pass
                
                return success, response_data
        except Exception as e:
            print(f"❌ Add person error: {str(e)}")
            return False, {}

    def test_get_populated_watchlist(self):
        """Test getting watchlist with people"""
        return self.run_test("Get Populated Watchlist", "GET", "watchlist", 200)

    def test_get_person_details(self, person_id):
        """Test getting specific person details"""
        return self.run_test(f"Get Person Details ({person_id})", "GET", f"watchlist/{person_id}", 200)

    def test_delete_person(self, person_id):
        """Test deleting a person from watchlist"""
        success, response_data = self.run_test(f"Delete Person ({person_id})", "DELETE", f"watchlist/{person_id}", 200)
        
        if success and person_id in self.created_person_ids:
            self.created_person_ids.remove(person_id)
        
        return success, response_data

    def test_invalid_requests(self):
        """Test various invalid requests"""
        print("\n🚫 Testing Invalid Requests")
        
        # Test adding person without photo
        success1, _ = self.run_test("Add Person Without Photo", "POST", "watchlist", 422, data={'name': 'Test'})
        
        # Test getting non-existent person
        success2, _ = self.run_test("Get Non-existent Person", "GET", "watchlist/invalid-id", 404)
        
        # Test deleting non-existent person
        success3, _ = self.run_test("Delete Non-existent Person", "DELETE", "watchlist/invalid-id", 404)
        
        return success1 and success2 and success3

    def cleanup(self):
        """Clean up created test data"""
        print(f"\n🗑️  Cleaning up {len(self.created_person_ids)} test persons...")
        for person_id in self.created_person_ids.copy():
            try:
                self.test_delete_person(person_id)
            except:
                pass

def main():
    print("👥 WATCHLIST FUNCTIONALITY - API TESTING")
    print("=" * 50)
    
    tester = WatchlistTester()
    
    try:
        # Test initial empty state
        print("\n📋 TESTING INITIAL STATE")
        print("-" * 30)
        
        tester.test_get_empty_watchlist()
        tester.test_get_watchlist_stats()
        
        # Test adding people to watchlist
        print("\n➕ TESTING ADD PEOPLE TO WATCHLIST")
        print("-" * 40)
        
        # Add multiple people with different threat levels
        tester.test_add_person_to_watchlist("John Doe", "Johnny", "high")
        tester.test_add_person_to_watchlist("Jane Smith", "Janie", "medium")
        tester.test_add_person_to_watchlist("Bob Wilson", "Bobby", "low")
        
        # Test getting populated watchlist
        print("\n📋 TESTING POPULATED WATCHLIST")
        print("-" * 35)
        
        tester.test_get_populated_watchlist()
        tester.test_get_watchlist_stats()
        
        # Test individual person operations
        print("\n👤 TESTING INDIVIDUAL PERSON OPERATIONS")
        print("-" * 45)
        
        if tester.created_person_ids:
            # Test getting person details
            for person_id in tester.created_person_ids[:2]:  # Test first 2
                tester.test_get_person_details(person_id)
        
        # Test invalid requests
        tester.test_invalid_requests()
        
        # Test deletion
        print("\n🗑️  TESTING PERSON DELETION")
        print("-" * 30)
        
        if tester.created_person_ids:
            # Delete one person
            person_to_delete = tester.created_person_ids[0]
            tester.test_delete_person(person_to_delete)
            
            # Verify watchlist updated
            tester.test_get_populated_watchlist()
            tester.test_get_watchlist_stats()
    
    finally:
        # Clean up remaining test data
        tester.cleanup()
    
    # Final results
    print("\n" + "=" * 50)
    print(f"📊 WATCHLIST TESTS: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All watchlist tests passed! API is working correctly.")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed. Check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())