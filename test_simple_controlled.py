"""
Simple controlled test - one request at a time with delays
"""
import requests
import time
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_simple_flow():
    """Test basic flow step by step"""
    
    print("\n" + "="*60)
    print("SIMPLE CONTROLLED TEST")
    print("="*60)
    
    user_id = f"simple_test_{int(time.time())}"
    
    # Test 1: Health
    print("\n1. Health Check...")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"   ✓ Status: {r.json()['status']}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return
    
    # Test 2: First recommendation
    print("\n2. First Recommendation...")
    try:
        r = requests.post(f"{BASE_URL}/recommend", 
                         json={"user_id": user_id, "num_recommendations": 5},
                         timeout=10)
        data = r.json()
        items1 = [rec['item_id'] for rec in data['recommendations']]
        print(f"   ✓ Got {len(items1)} items: {items1}")
        print(f"   Cold start: {data['cold_start']}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return
    
    time.sleep(1)
    
    # Test 3: Log event
    print("\n3. Log Click Event...")
    try:
        r = requests.post(f"{BASE_URL}/event",
                         json={"user_id": user_id, "item_id": items1[0], "event_type": "click"},
                         timeout=10)
        print(f"   ✓ Event logged: {r.json()['event_id']}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return
    
    time.sleep(1)
    
    # Test 4: Second recommendation
    print("\n4. Second Recommendation...")
    try:
        r = requests.post(f"{BASE_URL}/recommend",
                         json={"user_id": user_id, "num_recommendations": 5},
                         timeout=10)
        data = r.json()
        items2 = [rec['item_id'] for rec in data['recommendations']]
        print(f"   ✓ Got {len(items2)} items: {items2}")  
        print(f"   Cold start: {data['cold_start']}")
        
        if items1 == items2:
            print("   ⚠️  Recommendations UNCHANGED (STATIC)")
        else:
            print("   ✓ Recommendations CHANGED (DYNAMIC)")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return
    
    time.sleep(1)
    
    # Test 5: Metrics
    print("\n5. Check Metrics...")
    try:
        r = requests.get(f"{BASE_URL}/metrics", timeout=10)
        metrics = r.json()
        preds = metrics['prediction_metrics']['total_predictions']
        print(f"   ✓ Total predictions: {preds}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return
    
    print("\n" + "="*60)
    print("✓ ALL TESTS PASSED - Backend is stable")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_simple_flow()
