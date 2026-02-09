#!/usr/bin/env python3
"""
Dynamic AI/MLOps Demo Script

This script demonstrates all dynamic features of the recommendation system:
1. Real-time feature updates
2. Online learning
3. Drift detection & auto-retraining
4. A/B testing with multiple models
"""

import requests
import time
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

def print_section(title):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def print_json(data):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=2))

def demo_realtime_features():
    """Demonstrate real-time feature updates."""
    print_section("🔥 1. REAL-TIME FEATURE UPDATES")
    
    user_id = "demo_user_001"
    
    # Get initial recommendation
    print("➤ Getting initial recommendations...")
    response = requests.post(
        f"{BASE_URL}/recommend",
        json={"user_id": user_id, "num_recommendations": 3}
    )
    initial_recs = response.json()
    print(f"Initial recommendations: {[r['item_id'] for r in initial_recs['recommendations']]}")
    
    # Log several interactions
    print("\n➤ Logging user interactions (updates features in real-time)...")
    interactions = [
        {"user_id": user_id, "item_id": "item_50", "event_type": "view"},
        {"user_id": user_id, "item_id": "item_50", "event_type": "click"},
        {"user_id": user_id, "item_id": "item_50", "event_type": "purchase"},
        {"user_id": user_id, "item_id": "item_16", "event_type": "like"},
    ]
    
    for interaction in interactions:
        response = requests.post(f"{BASE_URL}/event", json=interaction)
        result = response.json()
        print(f"  ✓ {interaction['event_type'].upper()} on {interaction['item_id']} → Features updated")
    
    # Get updated recommendation
    print("\n➤ Getting new recommendations (with updated features)...")
    response = requests.post(
        f"{BASE_URL}/recommend",
        json={"user_id": user_id, "num_recommendations": 3}
    )
    updated_recs = response.json()
    print(f"Updated recommendations: {[r['item_id'] for r in updated_recs['recommendations']]}")
    print("\n✅ Features updated in real-time! Recommendations reflect user behavior.")

def demo_online_learning():
    """Demonstrate online learning."""
    print_section("🔄 2. ONLINE LEARNING (Incremental Updates)")
    
    # Check initial status
    print("➤ Checking online learning status...")
    response = requests.get(f"{BASE_URL}/mlops/online-learning/status")
    status = response.json()
    print_json(status)
    
    # Simulate many interactions to fill buffer
    print("\n➤ Simulating 100 user interactions to fill learning buffer...")
    for i in range(100):
        user_id = f"user_{i % 20}"  # 20 different users
        item_id = f"item_{i % 50}"  # 50 different items
        event_type = ["view", "click", "purchase"][i % 3]
        
        requests.post(
            f"{BASE_URL}/event",
            json={"user_id": user_id, "item_id": item_id, "event_type": event_type}
        )
    
    print("  ✓ Logged 100 interactions")
    
    # Check updated status
    print("\n➤ Online learning status after interactions:")
    response = requests.get(f"{BASE_URL}/mlops/online-learning/status")
    status = response.json()
    print_json(status)
    print(f"\n  Buffer utilization: {status['buffer_utilization']*100:.1f}%")
    
    # Trigger incremental update
    print("\n➤ Triggering incremental model update...")
    response = requests.post(f"{BASE_URL}/mlops/online-learning/trigger")
    result = response.json()
    print_json(result)
    print("\n✅ Model updated incrementally without full retraining!")

def demo_drift_detection():
    """Demonstrate drift detection and auto-retraining."""
    print_section("📈 3. DRIFT DETECTION & AUTO-RETRAINING")
    
    # Check retraining status
    print("➤ Checking auto-retrain status...")
    response = requests.get(f"{BASE_URL}/mlops/retrain/status")
    status = response.json()
    print_json(status)
    
    # Trigger retraining check
    print("\n➤ Checking retraining triggers (drift, schedule, data volume)...")
    response = requests.post(
        f"{BASE_URL}/mlops/retrain",
        json={"force": False}
    )
    result = response.json()
    print(f"\n  Retraining triggered: {result['triggered']}")
    print(f"  Reason: {result['reason']}")
    
    # Force retrain for demo
    print("\n➤ Forcing manual retrain for demonstration...")
    response = requests.post(
        f"{BASE_URL}/mlops/retrain",
        json={"force": True, "reason": "Demo: Manual trigger"}
    )
    result = response.json()
    print(f"\n  Status: {result['reason']}")
    print("\n✅ Auto-retraining system monitors for drift and triggers retraining!")

def demo_ab_testing():
    """Demonstrate A/B testing framework."""
    print_section("🧪 4. A/B TESTING (Multi-Model Serving)")
    
    # Create experiment
    print("➤ Creating A/B test experiment...")
    experiment_data = {
        "name": "Model Comparison Demo",
        "description": "Compare champion vs challenger model",
        "variants": [
            {
                "name": "champion",
                "model_path": "/app/models/champion.pkl",
                "model_version": "v1.0"
            },
            {
                "name": "challenger",
                "model_path": "/app/models/challenger.pkl",
                "model_version": "v2.0"
            }
        ],
        "allocation_strategy": "thompson_sampling",
        "traffic_percentage": 100.0
    }
    
    response = requests.post(f"{BASE_URL}/mlops/experiments", json=experiment_data)
    result = response.json()
    experiment_id = result["experiment_id"]
    print(f"  ✓ Experiment created: {experiment_id}")
    print(f"  ✓ {result['message']}")
    
    # Start experiment
    print("\n➤ Starting experiment...")
    response = requests.post(f"{BASE_URL}/mlops/experiments/{experiment_id}/start")
    result = response.json()
    print(f"  ✓ Status: {result['status']}")
    
    # Simulate traffic
    print("\n➤ Simulating 50 requests (Thompson Sampling allocation)...")
    for i in range(50):
        user_id = f"ab_test_user_{i}"
        requests.post(
            f"{BASE_URL}/recommend",
            json={"user_id": user_id, "num_recommendations": 5}
        )
    print("  ✓ Traffic distributed adaptively between variants")
    
    # Get results
    print("\n➤ Getting experiment results...")
    response = requests.get(f"{BASE_URL}/mlops/experiments/{experiment_id}")
    results = response.json()
    
    print(f"\n  Experiment: {results['name']}")
    print(f"  Status: {results['status']}")
    print(f"  Total impressions: {results['total_impressions']}")
    
    for variant in results['variants']:
        print(f"\n  📊 {variant['name'].upper()}:")
        print(f"     Impressions: {variant['impressions']}")
        print(f"     Conversions: {variant['conversions']}")
        print(f"     Conversion rate: {variant['conversion_rate']*100:.2f}%")
        print(f"     Avg latency: {variant['avg_latency_ms']:.2f}ms")
    
    if results.get('winning_variant'):
        print(f"\n  🏆 Winner: {results['winning_variant']} (confidence: {results['confidence']*100:.2f}%)")
    
    # Stop experiment
    print("\n➤ Stopping experiment...")
    response = requests.post(f"{BASE_URL}/mlops/experiments/{experiment_id}/stop")
    print("  ✓ Experiment stopped")
    
    print("\n✅ A/B testing enables safe model deployment and automatic optimization!")

def demo_complete_workflow():
    """Demonstrate complete dynamic MLOps workflow."""
    print_section("🎯 5. COMPLETE DYNAMIC WORKFLOW")
    
    print("This is what happens with EVERY user interaction:\n")
    print("1️⃣  Event logged → Real-time feature update in Redis")
    print("2️⃣  Interaction added to online learning buffer")
    print("3️⃣  Features tracked for drift detection")
    print("4️⃣  A/B test selects model variant for user")
    print("5️⃣  Recommendation generated with updated features")
    print("6️⃣  Performance tracked for variant improvement")
    print("7️⃣  When buffer full → Incremental model update")
    print("8️⃣  When drift detected → Full retraining triggered")
    print("9️⃣  Best variant automatically promoted\n")
    
    print("✨ The system is ALWAYS learning, adapting, and optimizing!")

def main():
    """Run the complete demo."""
    print("\n" + "="*60)
    print("  🔥 DYNAMIC AI/MLOps SYSTEM DEMONSTRATION 🔥")
    print("="*60)
    print("\nThis demo showcases a truly dynamic recommendation system")
    print("that learns continuously and adapts automatically.\n")
    
    input("Press Enter to start the demo...")
    
    try:
        demo_realtime_features()
        input("\nPress Enter to continue to Online Learning demo...")
        
        demo_online_learning()
        input("\nPress Enter to continue to Drift Detection demo...")
        
        demo_drift_detection()
        input("\nPress Enter to continue to A/B Testing demo...")
        
        demo_ab_testing()
        input("\nPress Enter to see the complete workflow...")
        
        demo_complete_workflow()
        
        print_section("🎉 DEMO COMPLETE!")
        print("Your recommendation system is now:")
        print("  ✅ Learning from every interaction")
        print("  ✅ Updating features in real-time")
        print("  ✅ Adapting models incrementally")
        print("  ✅ Detecting drift automatically")
        print("  ✅ Testing multiple models simultaneously")
        print("  ✅ Optimizing performance continuously\n")
        print("This is TRUE Dynamic AI/MLOps! 🚀\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to the API at", BASE_URL)
        print("Make sure the backend is running with: docker-compose up\n")
    except Exception as e:
        print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    main()
