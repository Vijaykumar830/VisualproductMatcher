import requests
import sys
import json
import os
from datetime import datetime
from pathlib import Path

class VisualProductMatcherTester:
    def __init__(self):
        # Use the public endpoint from frontend .env
        self.base_url = "https://similarpick.preview.emergentagent.com/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.passed_tests = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            self.passed_tests.append(name)
            print(f"✅ {name} - PASSED")
        else:
            self.failed_tests.append({"test": name, "details": details})
            print(f"❌ {name} - FAILED: {details}")

    def test_api_health(self):
        """Test basic API health"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            success = response.status_code == 200
            if success:
                data = response.json()
                clip_available = data.get('clip_available', False)
                self.log_test("API Health Check", success, f"CLIP Available: {clip_available}")
                return clip_available
            else:
                self.log_test("API Health Check", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("API Health Check", False, str(e))
            return False

    def test_get_products_empty(self):
        """Test getting products when database is empty"""
        try:
            response = requests.get(f"{self.base_url}/products", timeout=10)
            success = response.status_code == 200
            if success:
                products = response.json()
                self.log_test("Get Products (Empty DB)", success, f"Found {len(products)} products")
                return len(products)
            else:
                self.log_test("Get Products (Empty DB)", False, f"Status: {response.status_code}")
                return -1
        except Exception as e:
            self.log_test("Get Products (Empty DB)", False, str(e))
            return -1

    def test_seed_products(self):
        """Test seeding database with sample products"""
        try:
            response = requests.get(f"{self.base_url}/seed-products", timeout=60)
            success = response.status_code == 200
            if success:
                data = response.json()
                inserted = data.get('inserted', 0)
                failed = data.get('failed', 0)
                self.log_test("Seed Products", success, f"Inserted: {inserted}, Failed: {failed}")
                return inserted > 0
            else:
                self.log_test("Seed Products", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Seed Products", False, str(e))
            return False

    def test_get_products_after_seed(self):
        """Test getting products after seeding"""
        try:
            response = requests.get(f"{self.base_url}/products", timeout=10)
            success = response.status_code == 200
            if success:
                products = response.json()
                count = len(products)
                self.log_test("Get Products (After Seed)", success, f"Found {count} products")
                return products if count > 0 else []
            else:
                self.log_test("Get Products (After Seed)", False, f"Status: {response.status_code}")
                return []
        except Exception as e:
            self.log_test("Get Products (After Seed)", False, str(e))
            return []

    def test_get_categories(self):
        """Test getting product categories"""
        try:
            response = requests.get(f"{self.base_url}/products/categories", timeout=10)
            success = response.status_code == 200
            if success:
                data = response.json()
                categories = data.get('categories', [])
                self.log_test("Get Categories", success, f"Found categories: {categories}")
                return categories
            else:
                self.log_test("Get Categories", False, f"Status: {response.status_code}")
                return []
        except Exception as e:
            self.log_test("Get Categories", False, str(e))
            return []

    def test_search_by_url(self):
        """Test search by image URL"""
        try:
            # Use a simple test image URL
            test_url = "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500"
            
            data = {
                'url': test_url,
                'limit': 5,
                'min_similarity': 0.3
            }
            
            response = requests.post(f"{self.base_url}/search/url", data=data, timeout=30)
            success = response.status_code == 200
            if success:
                results = response.json()
                self.log_test("Search by URL", success, f"Found {len(results)} similar products")
                return len(results) > 0
            else:
                self.log_test("Search by URL", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Search by URL", False, str(e))
            return False

    def test_search_by_upload(self):
        """Test search by file upload"""
        try:
            # Create a simple test image (1x1 pixel PNG)
            import io
            from PIL import Image
            
            # Create a small test image
            img = Image.new('RGB', (100, 100), color='red')
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            files = {'file': ('test.png', img_bytes, 'image/png')}
            data = {
                'limit': 5,
                'min_similarity': 0.1  # Lower threshold for test
            }
            
            response = requests.post(f"{self.base_url}/search/upload", files=files, data=data, timeout=30)
            success = response.status_code == 200
            if success:
                results = response.json()
                self.log_test("Search by Upload", success, f"Found {len(results)} similar products")
                return len(results) >= 0  # Accept 0 results as valid
            else:
                self.log_test("Search by Upload", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Search by Upload", False, str(e))
            return False

    def test_create_product(self):
        """Test creating a new product"""
        try:
            product_data = {
                "name": "Test Product",
                "category": "Test",
                "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500",
                "price": 99.99,
                "description": "Test product for API testing"
            }
            
            response = requests.post(f"{self.base_url}/products", json=product_data, timeout=30)
            success = response.status_code == 200
            if success:
                product = response.json()
                self.log_test("Create Product", success, f"Created product: {product.get('name')}")
                return product.get('id')
            else:
                self.log_test("Create Product", False, f"Status: {response.status_code}, Response: {response.text}")
                return None
        except Exception as e:
            self.log_test("Create Product", False, str(e))
            return None

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Visual Product Matcher Backend Tests")
        print("=" * 60)
        
        # Test 1: API Health
        clip_available = self.test_api_health()
        if not clip_available:
            print("⚠️  CLIP model not available - some tests may fail")
        
        # Test 2: Get products (empty)
        initial_count = self.test_get_products_empty()
        
        # Test 3: Seed products (if needed)
        if initial_count == 0:
            seed_success = self.test_seed_products()
            if not seed_success:
                print("❌ Seeding failed - skipping dependent tests")
                return self.get_results()
        
        # Test 4: Get products after seeding
        products = self.test_get_products_after_seed()
        
        # Test 5: Get categories
        categories = self.test_get_categories()
        
        # Test 6: Create new product
        if clip_available:
            new_product_id = self.test_create_product()
        
        # Test 7: Search by URL
        if clip_available and len(products) > 0:
            self.test_search_by_url()
        
        # Test 8: Search by upload
        if clip_available and len(products) > 0:
            self.test_search_by_upload()
        
        return self.get_results()

    def get_results(self):
        """Get test results summary"""
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.failed_tests:
            print("\n❌ Failed Tests:")
            for test in self.failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        
        if self.passed_tests:
            print(f"\n✅ Passed Tests: {', '.join(self.passed_tests)}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        return {
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "failed_tests": len(self.failed_tests),
            "success_rate": success_rate,
            "passed_test_names": self.passed_tests,
            "failed_test_details": self.failed_tests
        }

def main():
    """Main test execution"""
    tester = VisualProductMatcherTester()
    results = tester.run_all_tests()
    
    # Return appropriate exit code
    return 0 if results["failed_tests"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())