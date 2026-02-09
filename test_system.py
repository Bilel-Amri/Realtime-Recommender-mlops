"""
Quick System Test Script

Tests the recommendation system for:
1. Backend health
2. Recommendation API
3. Event logging
4. Learning behavior (recommendations change after interactions)

Usage:
    python test_system.py

Prerequisites:
    - Backend running: uvicorn app.main:app --reload
"""

import requests
import json
import time
from typing import List, Dict

BASE_URL = "http://localhost:8000"
COLORS = {
    'GREEN': '\033[92m',
    'RED': '\033[91m',
    'YELLOW': '\033[93m',
    'BLUE': '\033[94m',
    'END': '\033[0m'
}

def print_success(msg):
    print(f"{COLORS['GREEN']}✅ {msg}{COLORS['END']}")

def print_error(msg):
    print(f"{COLORS['RED']}❌ {msg}{COLORS['END']}")

def print_warning(msg):
    print(f"{COLORS['YELLOW']}⚠️  {msg}{COLORS['END']}")

def print_info(msg):
    print(f"{COLORS['BLUE']}ℹ️  {msg}{COLORS['END']}")


def test_health():
    """Test if backend is running."""
    print("\n" + "="*60)
    print("Test 1: Backend Health Check")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success("Backend is healthy")
            print(f"   Status: {data.get('status', 'unknown')}")
            return True
        else:
            print_error(f"Health check failed: HTTP {response.status_code}")
            return False
            
    except requests.ConnectionError:
        print_error("Cannot connect to backend")
        print_info("Make sure backend is running:")
        print_info("  cd backend && uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print_error(f"Health check error: {e}")
        return False


def test_recommendations_before(user_id: str = "test_user_1") -> List[Dict]:
    """Get initial recommendations."""
    print("\n" + "="*60)
    print("Test 2: Get Initial Recommendations")
    print("="*60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/recommend",
            json={"user_id": user_id, "num_recommendations": 5},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            
            print_success(f"Received {len(recommendations)} recommendations")
            print(f"\nRecommendations for user '{user_id}' BEFORE interaction:")
            
            for i, rec in enumerate(recommendations[:5]):
                item_id = rec.get('item_id', 'unknown')
                score = rec.get('score', 'N/A')
                print(f"   {i+1}. Item: {item_id} (score: {score})")
            
            return recommendations
        else:
            print_error(f"Recommendation request failed: HTTP {response.status_code}")
            return []
            
    except Exception as e:
        print_error(f"Recommendation error: {e}")
        return []


def test_send_event(user_id: str = "test_user_1", item_id: str = "item_50"):
    """Send interaction event."""
    print("\n" + "="*60)
    print("Test 3: Send User Interaction Event")
    print("="*60)
    
    event = {
        "user_id": user_id,
        "item_id": item_id,
        "event_type": "click",
        "timestamp": "2026-02-06T10:30:00Z"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/event",
            json=event,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Event logged successfully")
            print(f"   User: {user_id}")
            print(f"   Item: {item_id}")
            print(f"   Type: click")
            return True
        else:
            print_error(f"Event logging failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Event logging error: {e}")
        return False


def test_recommendations_after(user_id: str = "test_user_1") -> List[Dict]:
    """Get recommendations after interaction."""
    print("\n" + "="*60)
    print("Test 4: Get Recommendations After Interaction")
    print("="*60)
    
    # Wait a moment for processing
    time.sleep(1)
    
    try:
        response = requests.post(
            f"{BASE_URL}/recommend",
            json={"user_id": user_id, "num_recommendations": 5},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            
            print_success(f"Received {len(recommendations)} recommendations")
            print(f"\nRecommendations for user '{user_id}' AFTER interaction:")
            
            for i, rec in enumerate(recommendations[:5]):
                item_id = rec.get('item_id', 'unknown')
                score = rec.get('score', 'N/A')
                print(f"   {i+1}. Item: {item_id} (score: {score})")
            
            return recommendations
        else:
            print_error(f"Recommendation request failed: HTTP {response.status_code}")
            return []
            
    except Exception as e:
        print_error(f"Recommendation error: {e}")
        return []


def test_learning_behavior():
    """Test if recommendations change (learning behavior)."""
    print("\n" + "="*80)
    print("🧠 TESTING LEARNING BEHAVIOR")
    print("="*80)
    
    user_id = "test_user_1"
    
    # Get initial recommendations
    recs_before = test_recommendations_before(user_id)
    
    if not recs_before:
        print_error("Cannot test learning - no initial recommendations")
        return False
    
    # Send interaction
    if not test_send_event(user_id, "item_50"):
        print_error("Cannot test learning - event logging failed")
        return False
    
    # Get recommendations after
    recs_after = test_recommendations_after(user_id)
    
    if not recs_after:
        print_error("Cannot test learning - no recommendations after interaction")
        return False
    
    # Compare
    before_ids = [r.get('item_id') for r in recs_before]
    after_ids = [r.get('item_id') for r in recs_after]
    
    print("\n" + "="*80)
    print("LEARNING ANALYSIS")
    print("="*80)
    
    if before_ids != after_ids:
        print_success("Recommendations CHANGED after interaction!")
        print_info("System is learning and adapting to user behavior 🎉")
        print(f"\nBefore: {before_ids}")
        print(f"After:  {after_ids}")
        return True
    else:
        print_warning("Recommendations stayed the SAME")
        print_info("This is expected with MockModel")
        print_info("To see real learning:")
        print_info("  1. Train embedding model: cd training && python train_embeddings.py")
        print_info("  2. Integrate trained model into backend")
        print_info("  3. Restart backend and test again")
        return False


def test_multiple_users():
    """Test that different users get different recommendations."""
    print("\n" + "="*80)
    print("👥 TESTING PERSONALIZATION (Multiple Users)")
    print("="*80)
    
    users = ["user_A", "user_B", "user_C"]
    all_recommendations = {}
    
    for user_id in users:
        try:
            response = requests.post(
                f"{BASE_URL}/recommend",
                json={"user_id": user_id, "num_recommendations": 5},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                recs = data.get('recommendations', [])
                rec_ids = [r.get('item_id') for r in recs[:5]]
                all_recommendations[user_id] = rec_ids
                
                print(f"\n{user_id}: {rec_ids}")
            else:
                print_error(f"Failed to get recommendations for {user_id}")
                
        except Exception as e:
            print_error(f"Error for {user_id}: {e}")
    
    # Check uniqueness
    if len(all_recommendations) < 2:
        print_warning("Not enough users to test personalization")
        return False
    
    unique_recs = len(set(tuple(recs) for recs in all_recommendations.values()))
    total_users = len(all_recommendations)
    
    print("\n" + "-"*80)
    if unique_recs == total_users:
        print_success(f"All {total_users} users got DIFFERENT recommendations!")
        print_info("System is personalizing! 🎉")
        return True
    elif unique_recs > 1:
        print_warning(f"{unique_recs}/{total_users} users got unique recommendations")
        print_info("Some personalization detected")
        return True
    else:
        print_warning("All users got the SAME recommendations")
        print_info("Expected with MockModel. Train real model for personalization.")
        return False


def run_all_tests():
    """Run complete test suite."""
    print("\n" + "="*80)
    print("🧪 REAL-TIME RECOMMENDATION SYSTEM - TEST SUITE")
    print("="*80)
    
    results = {
        'health': False,
        'learning': False,
        'personalization': False
    }
    
    # Test 1: Health
    results['health'] = test_health()
    
    if not results['health']:
        print("\n" + "="*80)
        print_error("TESTS ABORTED - Backend not available")
        print("="*80)
        return False
    
    # Test 2: Learning
    results['learning'] = test_learning_behavior()
    
    # Test 3: Personalization
    results['personalization'] = test_multiple_users()
    
    # Final summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed_flag in results.items():
        status = "✅ PASS" if passed_flag else "❌ FAIL"
        print(f"{status} - {test_name.title()}")
    
    print("\n" + "-"*80)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print_success("ALL TESTS PASSED! System is working correctly. 🎉")
    elif results['health'] and not (results['learning'] or results['personalization']):
        print_warning("Backend works but using MockModel")
        print_info("Next steps:")
        print_info("  1. cd training && python train_embeddings.py")
        print_info("  2. Integrate trained model into backend")
        print_info("  3. Test again to see real learning")
    else:
        print_error("Some tests failed. Check errors above.")
    
    print("="*80)
    
    return passed == total


if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        exit(1)
    except Exception as e:
        print_error(f"Test suite crashed: {e}")
        exit(1)
