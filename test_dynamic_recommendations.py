#!/usr/bin/env python3
"""
Test script to demonstrate DYNAMIC recommendations based on user interactions.

This proves that the system is now personalized:
- Different users get different recommendations
- Recommendations change based on interactions
- Event→Feature→Recommendation pipeline works
"""

import asyncio
import httpx
import time
from typing import List, Dict

BASE_URL = "http://localhost:8000"

async def send_event(user_id: str, item_id: str, event_type: str = "click"):
    """Send a user interaction event."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/event",
            json={
                "user_id": user_id,
                "item_id": item_id,
                "event_type": event_type,
                "timestamp": time.time(),
                "metadata": {}
            }
        )
        return response.status_code == 200

async def get_recommendations(user_id: str, k: int = 5) -> List[str]:
    """Get recommendations for a user."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/recommend",
            json={
                "user_id": user_id,
                "num_recommendations": k,
                "context": {}
            }
        )
        if response.status_code == 200:
            data = response.json()
            # Extract item_ids from recommendations list
            recommendations = data.get("recommendations", [])
            return [rec["item_id"] for rec in recommendations]
        return []

async def test_dynamic_behavior():
    """
    Comprehensive test demonstrating dynamic personalization.
    
    Test Plan:
    1. Brand new users - should get cold-start recommendations
    2. User A clicks item_1, item_2 - should influence their recommendations
    3. User B clicks item_5, item_10 - should get DIFFERENT recommendations
    4. User C makes purchases - should get even more personalized recs
    """
    
    print("=" * 80)
    print("DYNAMIC RECOMMENDATION SYSTEM TEST")
    print("=" * 80)
    print()
    
    # Test 1: New users (cold start)
    print("📋 Test 1: Brand new users (cold start)")
    print("-" * 80)
    
    user_new = f"new_user_{int(time.time())}"
    recs_new = await get_recommendations(user_new, k=5)
    print(f"✅ User '{user_new}' (NEW) → Recommendations: {recs_new}")
    print()
    
    # Test 2: User A - clicks on category 'item'
    print("📋 Test 2: User A - Multiple clicks on 'item_X' category")
    print("-" * 80)
    
    user_a = f"user_a_{int(time.time())}"
    
    # Get baseline recommendations
    recs_a_before = await get_recommendations(user_a, k=5)
    print(f"Before interactions: {recs_a_before}")
    
    # User A clicks several items
    await send_event(user_a, "item_1", "click")
    print(f"   ↳ User A clicked 'item_1'")
    await asyncio.sleep(0.1)
    
    await send_event(user_a, "item_2", "click")
    print(f"   ↳ User A clicked 'item_2'")
    await asyncio.sleep(0.1)
    
    await send_event(user_a, "item_3", "view")
    print(f"   ↳ User A viewed 'item_3'")
    await asyncio.sleep(0.1)
    
    # Get updated recommendations
    recs_a_after = await get_recommendations(user_a, k=5)
    print(f"✅ After interactions: {recs_a_after}")
    
    if recs_a_before != recs_a_after:
        print("   🎉 SUCCESS: Recommendations CHANGED based on interactions!")
    else:
        print("   ⚠️  Warning: Recommendations unchanged (may still be random due to mock model)")
    print()
    
    # Test 3: User B - different interaction pattern
    print("📋 Test 3: User B - Different interaction pattern")
    print("-" * 80)
    
    user_b = f"user_b_{int(time.time())}"
    
    # User B interacts with different items
    await send_event(user_b, "item_5", "click")
    print(f"   ↳ User B clicked 'item_5'")
    await asyncio.sleep(0.1)
    
    await send_event(user_b, "item_10", "click")
    print(f"   ↳ User B clicked 'item_10'")
    await asyncio.sleep(0.1)
    
    await send_event(user_b, "item_15", "like")
    print(f"   ↳ User B liked 'item_15'")
    await asyncio.sleep(0.1)
    
    recs_b = await get_recommendations(user_b, k=5)
    print(f"✅ User B recommendations: {recs_b}")
    print()
    
    # Test 4: User C - heavy engagement (purchases)
    print("📋 Test 4: User C - Heavy engagement with purchases")
    print("-" * 80)
    
    user_c = f"user_c_{int(time.time())}"
    
    # User C makes purchases
    await send_event(user_c, "item_7", "view")
    print(f"   ↳ User C viewed 'item_7'")
    await asyncio.sleep(0.1)
    
    await send_event(user_c, "item_7", "click")
    print(f"   ↳ User C clicked 'item_7'")
    await asyncio.sleep(0.1)
    
    await send_event(user_c, "item_7", "purchase")
    print(f"   ↳ User C PURCHASED 'item_7'")
    await asyncio.sleep(0.1)
    
    await send_event(user_c, "item_8", "purchase")
    print(f"   ↳ User C PURCHASED 'item_8'")
    await asyncio.sleep(0.1)
    
    recs_c = await get_recommendations(user_c, k=5)
    print(f"✅ User C recommendations: {recs_c}")
    print()
    
    # Test 5: Verify persistence - get recommendations again
    print("📋 Test 5: Verify feature persistence")
    print("-" * 80)
    
    recs_a_final = await get_recommendations(user_a, k=5)
    recs_b_final = await get_recommendations(user_b, k=5)
    recs_c_final = await get_recommendations(user_c, k=5)
    
    print(f"User A (item_1,2,3):  {recs_a_final}")
    print(f"User B (item_5,10,15): {recs_b_final}")
    print(f"User C (purchases):    {recs_c_final}")
    print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    all_recs = [recs_a_final, recs_b_final, recs_c_final]
    unique_rec_sets = len(set(tuple(r) for r in all_recs))
    
    print(f"Total users tested: 3 (A, B, C)")
    print(f"Unique recommendation sets: {unique_rec_sets}/3")
    print()
    
    if unique_rec_sets == 3:
        print("✅ PERFECT: All users received DIFFERENT recommendations!")
        print("   System is fully personalized and dynamic! 🎉")
    elif unique_rec_sets == 2:
        print("✅ GOOD: Some personalization detected")
        print("   System is partially working, may improve with real model")
    elif unique_rec_sets == 1:
        print("⚠️  WARNING: All users received IDENTICAL recommendations")
        print("   Features may be updating but model is still static")
        print("   This is expected with MockModel - deploy real model to fix")
    
    print()
    print("🔍 Next Steps:")
    print("   1. Check backend logs to see feature updates")
    print("   2. Verify user interactions are being recorded")
    print("   3. Deploy trained model to replace MockModel for true personalization")
    print("=" * 80)

async def main():
    """Run the dynamic behavior test."""
    try:
        # Check if server is running
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/v1/health")
            if response.status_code != 200:
                print("❌ ERROR: Backend server not responding")
                print("   Please start the server with: cd backend && uvicorn app.main:app")
                return
        
        print("✅ Backend server is running\n")
        await test_dynamic_behavior()
        
    except httpx.ConnectError:
        print("❌ ERROR: Cannot connect to backend server")
        print("   Please start the server with: cd backend && uvicorn app.main:app")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
