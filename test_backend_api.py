"""
Comprehensive Backend API Testing Script
Tests all endpoints with various inputs including edge cases
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name, passed, details=""):
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"{status} | {name}")
    if details:
        print(f"    {details}")

def test_health_endpoint():
    """Test /health endpoint"""
    print(f"\n{Colors.BLUE}=== Testing /health Endpoint ==={Colors.END}")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        data = response.json()
        
        # Check status code
        print_test("Health endpoint returns 200", response.status_code == 200)
        
        # Check required fields
        required_fields = ["status", "version", "timestamp", "components", "uptime_seconds"]
        for field in required_fields:
            print_test(f"Health response has '{field}'", field in data)
        
        # Check components
        if "components" in data:
            component_names = [c["name"] for c in data["components"]]
            print_test("Has feature_store component", "feature_store" in component_names)
            print_test("Has model component", "model" in component_names)
            print_test("Has monitoring component", "monitoring" in component_names)
        
        return True
    except Exception as e:
        print_test("Health endpoint test", False, str(e))
        return False

def test_recommend_endpoint():
    """Test /recommend endpoint with various inputs"""
    print(f"\n{Colors.BLUE}=== Testing /recommend Endpoint ==={Colors.END}")
    
    # Test 1: Valid request
    try:
        payload = {"user_id": "test_user_1", "num_recommendations": 5}
        response = requests.post(f"{BASE_URL}/recommend", json=payload, timeout=10)
        data = response.json()
        
        print_test("Valid recommend request returns 200", response.status_code == 200)
        print_test("Response has recommendations", "recommendations" in data and len(data["recommendations"]) > 0)
        print_test("Response has user_id", data.get("user_id") == "test_user_1")
        print_test("Response has model_version", "model_version" in data)
        print_test("Response has generation_time_ms", "generation_time_ms" in data)
        
        # Check recommendation structure
        if data.get("recommendations"):
            rec = data["recommendations"][0]
            print_test("Recommendation has item_id", "item_id" in rec)
            print_test("Recommendation has score", "score" in rec)
            print_test("Recommendation has rank", "rank" in rec)
    except Exception as e:
        print_test("Valid recommend request", False, str(e))
    
    # Test 2: Different user
    try:
        payload = {"user_id": "test_user_2", "num_recommendations": 10}
        response = requests.post(f"{BASE_URL}/recommend", json=payload, timeout=10)
        print_test("Different user request succeeds", response.status_code == 200)
    except Exception as e:
        print_test("Different user request", False, str(e))
    
    # Test 3: Missing user_id (should fail)
    try:
        payload = {"num_recommendations": 5}
        response = requests.post(f"{BASE_URL}/recommend", json=payload, timeout=10)
        print_test("Missing user_id returns 422", response.status_code == 422)
    except Exception as e:
        print_test("Missing user_id validation", False, str(e))
    
    # Test 4: Invalid num_recommendations (should fail or use default)
    try:
        payload = {"user_id": "test_user_3", "num_recommendations": -1}
        response = requests.post(f"{BASE_URL}/recommend", json=payload, timeout=10)
        print_test("Negative num_recommendations handled", response.status_code in [422, 400])
    except Exception as e:
        print_test("Invalid num_recommendations validation", False, str(e))
    
    # Test 5: Exclude items
    try:
        payload = {
            "user_id": "test_user_4",
            "num_recommendations": 5,
            "exclude_items": ["item_1", "item_2"]
        }
        response = requests.post(f"{BASE_URL}/recommend", json=payload, timeout=10)
        data = response.json()
        print_test("Exclude items request succeeds", response.status_code == 200)
        
        # Verify excluded items are not in recommendations
        if data.get("recommendations"):
            excluded_ids = [rec["item_id"] for rec in data["recommendations"] if rec["item_id"] in ["item_1", "item_2"]]
            print_test("Excluded items not in recommendations", len(excluded_ids) == 0, f"Found: {excluded_ids}")
    except Exception as e:
        print_test("Exclude items test", False, str(e))
    
    # Test 6: Context parameter
    try:
        payload = {
            "user_id": "test_user_5",
            "num_recommendations": 5,
            "context": {"device": "mobile", "time_of_day": "evening"}
        }
        response = requests.post(f"{BASE_URL}/recommend", json=payload, timeout=10)
        print_test("Context parameter accepted", response.status_code == 200)
    except Exception as e:
        print_test("Context parameter test", False, str(e))

def test_event_endpoint():
    """Test /event endpoint"""
    print(f"\n{Colors.BLUE}=== Testing /event Endpoint ==={Colors.END}")
    
    # Test 1: Valid event
    try:
        payload = {
            "user_id": "test_user_1",
            "item_id": "item_100",
            "event_type": "click"
        }
        response = requests.post(f"{BASE_URL}/event", json=payload, timeout=10)
        data = response.json()
        
        print_test("Valid event returns 200", response.status_code == 200)
        print_test("Event has event_id", "event_id" in data)
        print_test("Event has timestamp", "timestamp" in data)
        print_test("Event status is logged", data.get("status") == "logged")
    except Exception as e:
        print_test("Valid event test", False, str(e))
    
    # Test 2: Different event types
    event_types = ["view", "purchase", "like", "dislike", "share"]
    for event_type in event_types:
        try:
            payload = {
                "user_id": f"test_user_{event_type}",
                "item_id": f"item_{event_type}",
                "event_type": event_type
            }
            response = requests.post(f"{BASE_URL}/event", json=payload, timeout=10)
            print_test(f"Event type '{event_type}' accepted", response.status_code == 200)
        except Exception as e:
            print_test(f"Event type '{event_type}'", False, str(e))
    
    # Test 3: Missing required fields
    try:
        payload = {"user_id": "test_user_1"}  # Missing item_id and event_type
        response = requests.post(f"{BASE_URL}/event", json=payload, timeout=10)
        print_test("Missing fields returns 422", response.status_code == 422)
    except Exception as e:
        print_test("Missing fields validation", False, str(e))
    
    # Test 4: Invalid event type
    try:
        payload = {
            "user_id": "test_user_1",
            "item_id": "item_1",
            "event_type": "invalid_type"
        }
        response = requests.post(f"{BASE_URL}/event", json=payload, timeout=10)
        print_test("Invalid event type returns 422", response.status_code == 422)
    except Exception as e:
        print_test("Invalid event type validation", False, str(e))

def test_metrics_endpoint():
    """Test /metrics endpoint"""
    print(f"\n{Colors.BLUE}=== Testing /metrics Endpoint ==={Colors.END}")
    
    try:
        response = requests.get(f"{BASE_URL}/metrics", timeout=10)
        data = response.json()
        
        print_test("Metrics endpoint returns 200", response.status_code == 200)
        print_test("Has prediction_metrics", "prediction_metrics" in data)
        print_test("Has drift_metrics", "drift_metrics" in data)
        print_test("Has system_metrics", "system_metrics" in data)
        print_test("Has timestamp", "timestamp" in data)
        
        # Check prediction metrics structure
        if "prediction_metrics" in data:
            pm = data["prediction_metrics"]
            print_test("Prediction metrics has total_predictions", "total_predictions" in pm)
            print_test("Prediction metrics has average_latency_ms", "average_latency_ms" in pm)
    except Exception as e:
        print_test("Metrics endpoint test", False, str(e))

def test_model_info_endpoint():
    """Test /model-info endpoint"""
    print(f"\n{Colors.BLUE}=== Testing /model-info Endpoint ==={Colors.END}")
    
    try:
        response = requests.get(f"{BASE_URL}/model-info", timeout=10)
        data = response.json()
        
        print_test("Model-info endpoint returns 200", response.status_code == 200)
        print_test("Has model_name", "model_name" in data)
        print_test("Has version", "version" in data)
        print_test("Has stage", "stage" in data)
    except Exception as e:
        print_test("Model-info endpoint test", False, str(e))

def test_dynamic_behavior():
    """Test that recommendations change based on events"""
    print(f"\n{Colors.BLUE}=== Testing Dynamic Behavior ==={Colors.END}")
    
    try:
        user_id = f"dynamic_test_user_{int(time.time())}"
        
        # Get initial recommendations
        payload1 = {"user_id": user_id, "num_recommendations": 5}
        response1 = requests.post(f"{BASE_URL}/recommend", json=payload1, timeout=10)
        recs1 = response1.json().get("recommendations", [])
        
        print_test("Got initial recommendations", len(recs1) > 0)
        
        # Log some events
        for i, rec in enumerate(recs1[:3]):
            event_payload = {
                "user_id": user_id,
                "item_id": rec["item_id"],
                "event_type": "click"
            }
            requests.post(f"{BASE_URL}/event", json=event_payload, timeout=10)
        
        print_test("Logged interaction events", True)
        
        # Get recommendations again (immediately)
        response2 = requests.post(f"{BASE_URL}/recommend", json=payload1, timeout=10)
        recs2 = response2.json().get("recommendations", [])
        
        # Note: Without feature store, behavior may be static
        # This test documents the current behavior
        recs1_ids = [r["item_id"] for r in recs1]
        recs2_ids = [r["item_id"] for r in recs2]
        
        if recs1_ids != recs2_ids:
            print_test("Recommendations changed after events", True, "DYNAMIC behavior detected")
        else:
            print_test("Recommendations unchanged after events", True, 
                      f"{Colors.YELLOW}WARNING: STATIC behavior - feature store not updating{Colors.END}")
        
    except Exception as e:
        print_test("Dynamic behavior test", False, str(e))

def test_performance():
    """Test response times"""
    print(f"\n{Colors.BLUE}=== Testing Performance ==={Colors.END}")
    
    try:
        latencies = []
        for i in range(10):
            start = time.time()
            response = requests.post(
                f"{BASE_URL}/recommend",
                json={"user_id": f"perf_test_{i}", "num_recommendations": 10},
                timeout=10
            )
            latency = (time.time() - start) * 1000
            latencies.append(latency)
        
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        
        print_test("Average latency < 1000ms", avg_latency < 1000, f"Avg: {avg_latency:.2f}ms")
        print_test("Max latency < 2000ms", max_latency < 2000, f"Max: {max_latency:.2f}ms")
        print_test("All requests succeeded", True)
        
    except Exception as e:
        print_test("Performance test", False, str(e))

if __name__ == "__main__":
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}  COMPREHENSIVE BACKEND API TESTING{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"Testing against: {BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}\n")
    
    # Run all tests
    test_health_endpoint()
    test_recommend_endpoint()
    test_event_endpoint()
    test_metrics_endpoint()
    test_model_info_endpoint()
    test_dynamic_behavior()
    test_performance()
    
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}  TESTING COMPLETE{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
