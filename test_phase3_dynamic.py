"""
Phase 3: Dynamic Data Validation Test
Tests that the system changes behavior based on events (not static)
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_dynamic_recommendations():
    """Test that recommendations change with events"""
    print("=" * 60)
    print("PHASE 3: DYNAMIC DATA VALIDATION")
    print("=" * 60)
    
    user_id = f"dynamic_user_{int(time.time())}"
    
    # Step 1: Get initial recommendations
    print(f"\n1. Getting initial recommendations for {user_id}...")
    response1 = requests.post(
        f"{BASE_URL}/recommend",
        json={"user_id": user_id, "num_recommendations": 10},
        timeout=10
    )
    recs1 = response1.json()
    print(f"   Status: {response1.status_code}")
    print(f"   Cold start: {recs1.get('cold_start')}")
    print(f"   Number of recommendations: {len(recs1.get('recommendations', []))}")
    initial_items = [r['item_id'] for r in recs1.get('recommendations', [])]
    print(f"   Initial items: {initial_items[:5]}...")
    
    # Step 2: Log interactions for several items
    print(f"\n2. Logging interaction events...")
    events_logged = 0
    for i, rec in enumerate(recs1.get('recommendations', [])[:3]):
        event_response = requests.post(
            f"{BASE_URL}/event",
            json={
                "user_id": user_id,
                "item_id": rec['item_id'],
                "event_type": "click"
            },
            timeout=10
        )
        if event_response.status_code == 200:
            events_logged += 1
            print(f"   ✓ Logged click on {rec['item_id']}")
    
    print(f"   Total events logged: {events_logged}")
    
    # Step 3: Log more diverse events
    print(f"\n3. Logging additional event types...")
    for event_type in ["view", "like"]:
        response = requests.post(
            f"{BASE_URL}/event",
            json={
                "user_id": user_id,
                "item_id": f"item_special_{event_type}",
                "event_type": event_type
            },
            timeout=10
        )
        if response.status_code == 200:
            print(f"   ✓ Logged {event_type} event")
    
    # Step 4: Get recommendations again (immediately)
    print(f"\n4. Getting recommendations again (immediately after events)...")
    response2 = requests.post(
        f"{BASE_URL}/recommend",
        json={"user_id": user_id, "num_recommendations": 10},
        timeout=10
    )
    recs2 = response2.json()
    print(f"   Status: {response2.status_code}")
    print(f"   Cold start: {recs2.get('cold_start')}")
    second_items = [r['item_id'] for r in recs2.get('recommendations', [])]
    print(f"   Second items: {second_items[:5]}...")
    
    # Step 5: Wait and get recommendations again
    print(f"\n5. Waiting 2 seconds and getting recommendations again...")
    time.sleep(2)
    response3 = requests.post(
        f"{BASE_URL}/recommend",
        json={"user_id": user_id, "num_recommendations": 10},
        timeout=10
    )
    recs3 = response3.json()
    third_items = [r['item_id'] for r in recs3.get('recommendations', [])]
    print(f"   Third items: {third_items[:5]}...")
    
    # Analysis
    print(f"\n" + "="*60)
    print("ANALYSIS: System Behavior")
    print("="*60)
    
    if initial_items == second_items == third_items:
        print("⚠️  WARNING: STATIC BEHAVIOR DETECTED")
        print("   Recommendations did not change despite logging events")
        print("   This indicates:")
        print("   - Feature store is not updating from events")
        print("   - System is using fixed cold-start recommendations")
        print("   - Real-time personalization is NOT working")
        behavior = "STATIC"
    elif initial_items != second_items or initial_items != third_items:
        print("✓ DYNAMIC BEHAVIOR DETECTED")
        print("   Recommendations changed after events")
        print("   System is responsive to user interactions")
        behavior = "DYNAMIC"
    else:
        print("? UNDETERMINED")
        behavior = "UNKNOWN"
    
    # Check if cached
    cached_initially = recs1.get('cached', False)
    cached_second = recs2.get('cached', False)
    cached_third = recs3.get('cached', False)
    
    print(f"\nCaching behavior:")
    print(f"   Initial request cached: {cached_initially}")
    print(f"   Second request cached: {cached_second}")
    print(f"   Third request cached: {cached_third}")
    
    # Check generation times
    print(f"\nGeneration times:")
    print(f"   Initial: {recs1.get('generation_time_ms', 0):.2f}ms")
    print(f"   Second: {recs2.get('generation_time_ms', 0):.2f}ms")
    print(f"   Third: {recs3.get('generation_time_ms', 0):.2f}ms")
    
    print(f"\n" + "="*60)
    print(f"RESULT: System is {behavior}")
    print("="*60)
    
    return behavior

def test_different_users_different_recs():
    """Test that different users get different recommendations"""
    print(f"\n" + "="*60)
    print("TEST: Different Users Get Different Recommendations")
    print("="*60)
    
    users = [f"test_user_{i}_{int(time.time())}" for i in range(5)]
    all_recs = {}
    
    for user in users:
        response = requests.post(
            f"{BASE_URL}/recommend",
            json={"user_id": user, "num_recommendations": 5},
            timeout=10
        )
        recs = response.json()
        items = [r['item_id'] for r in recs.get('recommendations', [])]
        all_recs[user] = items
        print(f"   {user}: {items}")
    
    # Check if all users got same recommendations
    first_user_items = list(all_recs.values())[0]
    all_same = all(items == first_user_items for items in all_recs.values())
    
    if all_same:
        print("\n⚠️  All users received identical recommendations")
        print("   This is expected for cold-start users")
    else:
        print("\n✓ Different users received different recommendations")
        print("   System has some personalization")
    
    return not all_same

def test_metrics_increment():
    """Test that metrics actually increment"""
    print(f"\n" + "="*60)
    print("TEST: Metrics Increment with Requests")
    print("="*60)
    
    # Get initial metrics
    response1 = requests.get(f"{BASE_URL}/metrics", timeout=10)
    metrics1 = response1.json()
    initial_predictions= metrics1['prediction_metrics']['total_predictions']
    
    print(f"\nInitial predictions: {initial_predictions}")
    
    # Make some recommendation requests
    print("Making 5 recommendation requests...")
    for i in range(5):
        requests.post(
            f"{BASE_URL}/recommend",
            json={"user_id": f"metrics_test_{i}", "num_recommendations": 5},
            timeout=10
        )
    
    # Get updated metrics
    response2 = requests.get(f"{BASE_URL}/metrics", timeout=10)
    metrics2 = response2.json()
    final_predictions = metrics2['prediction_metrics']['total_predictions']
    
    print(f"Final predictions: {final_predictions}")
    print(f"Increment: +{final_predictions - initial_predictions}")
    
    if final_predictions > initial_predictions:
        print("\n✓ Metrics are incrementing correctly")
        return True
    else:
        print("\n✗ Metrics did NOT increment (PROBLEM)")
        return False

if __name__ == "__main__":
    print("\n")
    print("#" * 60)
    print("#  PHASE 3: DYNAMIC DATA VALIDATION")  
    print("#" * 60)
    
    try:
        # Test 1: Dynamic recommendations
        behavior = test_dynamic_recommendations()
        
        # Test 2: Different users
        personalized = test_different_users_different_recs()
        
        # Test 3: Metrics increment
        metrics_work = test_metrics_increment()
        
        print(f"\n\n" + "#" * 60)
        print("# PHASE 3 SUMMARY")
        print("#" * 60)
        print(f"System Behavior: {behavior}")
        print(f"Personalization: {'Working' if personalized else 'Not Working'}")
        print(f"Metrics Tracking: {'Working' if metrics_work else 'Not Working'}")
        
        if behavior == "STATIC":
            print("\n❌ CRITICAL: System is STATIC - events do not change recommendations")
            print("ROOT CAUSE: Feature store is not being updated with events")
            print("IMPACT: No real-time personalization")
        else:
            print("\n✓ System shows dynamic behavior")
        
        print("#" * 60 + "\n")
        
    except Exception as e:
        import traceback
        print(f"\n\n❌ PHASE 3 FAILED: {str(e)}")
        traceback.print_exc()
