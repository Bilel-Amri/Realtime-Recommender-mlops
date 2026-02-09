"""
Quick System Test - Verify all fixes are working
Run this after fixing the scripts to ensure everything works
"""
import requests
import time

BASE_URL = "http://localhost:8000/api/v1"

print("\n" + "="*60)
print("QUICK SYSTEM TEST")
print("="*60)

# Test 1: Health Check
print("\n1. Testing Health Endpoint...")
try:
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    if response.status_code == 200:
        print("   ✅ Health check PASSED")
    else:
        print(f"   ❌ Health check FAILED: {response.status_code}")
except Exception as e:
    print(f"   ❌ Health check ERROR: {e}")

# Test 2: Recommendations
print("\n2. Testing Recommendations Endpoint...")
try:
    response = requests.post(
        f"{BASE_URL}/recommend",
        json={"user_id": "user_1", "num_recommendations": 5},
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        recs = data.get("recommendations", [])
        print(f"   ✅ Recommendations PASSED ({len(recs)} items returned)")
        print(f"      First item: {recs[0]['item_id'] if recs else 'none'}")
    else:
        print(f"   ❌ Recommendations FAILED: {response.status_code}")
        print(f"      Response: {response.text}")
except Exception as e:
    print(f"   ❌ Recommendations ERROR: {e}")

# Test 3: Event Logging
print("\n3. Testing Event Logging...")
try:
    response = requests.post(
        f"{BASE_URL}/event",
        json={
            "user_id": "user_test",
            "item_id": "item_100",
            "event_type": "view"
        },
        timeout=5
    )
    if response.status_code == 200:
        print("   ✅ Event logging PASSED")
    else:
        print(f"   ❌ Event logging FAILED: {response.status_code}")
        print(f"      Response: {response.text}")
except Exception as e:
    print(f"   ❌ Event logging ERROR: {e}")

# Test 4: Dashboard Metrics
print("\n4. Testing Dashboard Metrics...")
try:
    response = requests.get(f"{BASE_URL}/metrics/dashboard", timeout=5)
    if response.status_code == 200:
        data = response.json()
        events_total = data.get("events", {}).get("total", 0)
        print(f"   ✅ Dashboard metrics PASSED")
        print(f"      Total events: {events_total}")
    else:
        print(f"   ❌ Dashboard metrics FAILED: {response.status_code}")
except Exception as e:
    print(f"   ❌ Dashboard metrics ERROR: {e}")

# Test 5: Interactive Learning
print("\n5. Testing Interactive Learning...")
user_id = "user_quick_test"

try:
    # Get initial recommendations
    response1 = requests.post(
        f"{BASE_URL}/recommend",
        json={"user_id": user_id, "num_recommendations": 8},
        timeout=10
    )
    
    if response1.status_code != 200:
        print(f"   ❌ Initial recommendations FAILED: {response1.status_code}")
    else:
        initial_recs = [r["item_id"] for r in response1.json()["recommendations"]]
        
        # Log interactions
        for i, item_id in enumerate(initial_recs[:3]):
            event_type = ["view", "like", "click"][i]
            requests.post(
                f"{BASE_URL}/event",
                json={"user_id": user_id, "item_id": item_id, "event_type": event_type},
                timeout=5
            )
        
        # Wait for processing
        time.sleep(2)
        
        # Get new recommendations
        response2 = requests.post(
            f"{BASE_URL}/recommend",
            json={"user_id": user_id, "num_recommendations": 8},
            timeout=10
        )
        
        if response2.status_code != 200:
            print(f"   ❌ Updated recommendations FAILED: {response2.status_code}")
        else:
            new_recs = [r["item_id"] for r in response2.json()["recommendations"]]
            changes = sum(1 for i in range(len(initial_recs)) if initial_recs[i] != new_recs[i])
            change_rate = (changes / len(initial_recs)) * 100
            
            if changes >= 5:
                print(f"   ✅ Interactive learning PASSED")
                print(f"      {changes}/8 items changed ({change_rate:.1f}%)")
            else:
                print(f"   ⚠️  Interactive learning PARTIAL")
                print(f"      Only {changes}/8 items changed ({change_rate:.1f}%)")
                print(f"      Expected 5+ changes")
            
except Exception as e:
    print(f"   ❌ Interactive learning ERROR: {e}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60 + "\n")

print("If all tests passed, run:")
print("  → python verify_system.py     (comprehensive check)")
print("  → python run_defense_demo.py  (full demo)")
print()
