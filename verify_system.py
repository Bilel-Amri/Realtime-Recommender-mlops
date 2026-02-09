"""
Pre-Defense System Verification Script
======================================

Run this script before your academic defense to verify
all components are working properly.

Usage: python verify_system.py
"""

import requests
import time
import sys
from typing import Dict, Any, List, Tuple


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


def check_service(name: str, url: str, expected_status: int = 200) -> bool:
    """Check if a service is responding"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == expected_status:
            print_success(f"{name} is running (Status: {response.status_code})")
            return True
        else:
            print_error(f"{name} returned status {response.status_code} (expected {expected_status})")
            return False
    except requests.exceptions.ConnectionError:
        print_error(f"{name} is not accessible at {url}")
        return False
    except requests.exceptions.Timeout:
        print_error(f"{name} timed out")
        return False
    except Exception as e:
        print_error(f"{name} check failed: {str(e)}")
        return False


def check_backend_health() -> bool:
    """Check backend health endpoint"""
    try:
        response = requests.get("http://localhost:8000/api/v1/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Backend health: {data.get('status', 'unknown')}")
            print_info(f"  Version: {data.get('version', 'unknown')}")
            uptime = data.get('uptime', 0)
            if isinstance(uptime, (int, float)):
                print_info(f"  Uptime: {uptime:.2f}s")
            else:
                print_info(f"  Uptime: {uptime}")
            return True
        else:
            print_error(f"Backend health check failed (Status: {response.status_code})")
            return False
    except Exception as e:
        print_error(f"Backend health check failed: {str(e)}")
        return False


def check_recommendations_endpoint() -> bool:
    """Test recommendation endpoint"""
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/recommend",
            json={"user_id": "user_1", "num_recommendations": 5},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            recs = data.get("recommendations", [])
            if len(recs) > 0:
                print_success(f"Recommendations endpoint working ({len(recs)} items returned)")
                print_info(f"  First recommendation: {recs[0].get('item_id', 'unknown')}")
                print_info(f"  Response time: {data.get('response_time_ms', 'unknown')}ms")
                return True
            else:
                print_error("Recommendations endpoint returned empty list")
                return False
        else:
            print_error(f"Recommendations endpoint failed (Status: {response.status_code})")
            return False
    except Exception as e:
        print_error(f"Recommendations test failed: {str(e)}")
        return False


def check_dashboard_metrics() -> bool:
    """Check dashboard metrics endpoint"""
    try:
        response = requests.get("http://localhost:8000/api/v1/metrics/dashboard", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success("Dashboard metrics endpoint working")
            
            # Check events
            events = data.get("events", {})
            print_info(f"  Total events: {events.get('total', 0)}")
            
            # Check learning
            learning = data.get("learning", {})
            print_info(f"  Embeddings updated: {learning.get('user_embeddings_updated', 0)}")
            
            # Check model
            model = data.get("model", {})
            print_info(f"  Model RMSE: {model.get('rmse', 'unknown')}")
            print_info(f"  Model R²: {model.get('r2', 'unknown')}")
            
            return True
        else:
            print_error(f"Dashboard metrics failed (Status: {response.status_code})")
            return False
    except Exception as e:
        print_error(f"Dashboard metrics test failed: {str(e)}")
        return False


def check_event_logging() -> bool:
    """Test event logging"""
    try:
        # Log a test event
        event_data = {
            "user_id": "user_999",
            "item_id": "item_1",
            "event_type": "view"
        }
        
        response = requests.post(
            "http://localhost:8000/api/v1/event",
            json=event_data,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Event logging working")
            print_info(f"  Status: {data.get('status', 'unknown')}")
            return True
        else:
            print_error(f"Event logging failed (Status: {response.status_code})")
            return False
    except Exception as e:
        print_error(f"Event logging test failed: {str(e)}")
        return False


def check_interactive_learning() -> bool:
    """Test that recommendations change after interaction"""
    try:
        user_id = "user_1"
        
        # Get initial recommendations
        print_info("Getting initial recommendations...")
        response1 = requests.post(
            "http://localhost:8000/api/v1/recommend",
            json={"user_id": user_id, "num_recommendations": 8},
            timeout=10
        )
        
        if response1.status_code != 200:
            print_error("Failed to get initial recommendations")
            return False
        
        initial_recs = [r["item_id"] for r in response1.json()["recommendations"]]
        
        # Log interaction events
        print_info("Logging test interactions...")
        events = [
            {"user_id": user_id, "item_id": initial_recs[0], "event_type": "view"},
            {"user_id": user_id, "item_id": initial_recs[1], "event_type": "like"},
            {"user_id": user_id, "item_id": initial_recs[2], "event_type": "rating", "rating": 5.0}
        ]
        
        for event in events:
            requests.post("http://localhost:8000/api/v1/event", json=event, timeout=5)
        
        # Wait for feature recomputation
        time.sleep(2)
        
        # Get new recommendations
        print_info("Getting updated recommendations...")
        response2 = requests.post(
            "http://localhost:8000/api/v1/recommend",
            json={"user_id": user_id, "num_recommendations": 8},
            timeout=10
        )
        
        if response2.status_code != 200:
            print_error("Failed to get updated recommendations")
            return False
        
        new_recs = [r["item_id"] for r in response2.json()["recommendations"]]
        
        # Count changes
        changes = sum(1 for i, r in enumerate(new_recs) if r != initial_recs[i])
        change_percentage = (changes / len(initial_recs)) * 100
        
        if changes >= 5:  # At least 5/8 items changed
            print_success(f"Interactive learning working ({changes}/{len(initial_recs)} items changed, {change_percentage:.1f}%)")
            print_info(f"  Before: {initial_recs[:3]}")
            print_info(f"  After:  {new_recs[:3]}")
            return True
        else:
            print_warning(f"Only {changes}/{len(initial_recs)} items changed ({change_percentage:.1f}%) - expected more")
            print_info(f"  Before: {initial_recs[:3]}")
            print_info(f"  After:  {new_recs[:3]}")
            return False
            
    except Exception as e:
        print_error(f"Interactive learning test failed: {str(e)}")
        return False


def check_ab_testing_endpoint() -> bool:
    """Check A/B testing endpoint"""
    try:
        response = requests.get("http://localhost:8000/api/v1/mlops/ab-results-demo", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success("A/B testing endpoint working")
            
            variants = data.get("variants", {})
            winner = data.get("winner", "unknown")
            
            print_info(f"  Variants: {len(variants)}")
            print_info(f"  Winner: {winner}")
            print_info(f"  Statistical significance: {data.get('statistical_analysis', {}).get('is_significant', 'unknown')}")
            
            return True
        else:
            print_error(f"A/B testing endpoint failed (Status: {response.status_code})")
            return False
    except Exception as e:
        print_error(f"A/B testing test failed: {str(e)}")
        return False


def check_files_exist() -> Tuple[int, int]:
    """Check that important files exist"""
    import os
    
    files_to_check = [
        ("training/recommendation_model.txt", "LightGBM model"),
        ("training/feature_importance.csv", "Feature importance"),
        ("models/embedding_model.pkl", "Embedding model"),
        ("AI_ROLE_EXPLAINED.md", "AI explanation doc"),
        ("RETRAINING_DEMO.md", "Retraining demo doc"),
        ("DEFENSE_CHEAT_SHEET.md", "Defense cheat sheet"),
        ("README_COMPLETE.md", "Complete README"),
        (".github/workflows/ci-cd.yml", "CI/CD pipeline"),
        ("docker-compose.yml", "Docker Compose config"),
    ]
    
    found = 0
    total = len(files_to_check)
    
    for filepath, description in files_to_check:
        if os.path.exists(filepath):
            print_success(f"{description}: {filepath}")
            found += 1
        else:
            print_warning(f"{description} not found: {filepath}")
    
    return found, total


def main():
    """Run all verification checks"""
    print_header("🎓 PRE-DEFENSE SYSTEM VERIFICATION")
    
    print_info("Starting comprehensive system check...")
    print_info("This will verify all components needed for academic defense\n")
    
    results = []
    
    # Check Docker services
    print_header("1️⃣  Docker Services")
    results.append(("Frontend", check_service("Frontend", "http://localhost:3000")))
    results.append(("Backend", check_service("Backend", "http://localhost:8000")))
    results.append(("MLflow", check_service("MLflow", "http://localhost:5000")))
    
    # Check backend endpoints
    print_header("2️⃣  Backend API Endpoints")
    results.append(("Health Check", check_backend_health()))
    results.append(("Recommendations", check_recommendations_endpoint()))
    results.append(("Dashboard Metrics", check_dashboard_metrics()))
    results.append(("Event Logging", check_event_logging()))
    results.append(("A/B Testing", check_ab_testing_endpoint()))
    
    # Check interactive learning
    print_header("3️⃣  Real-Time Learning")
    results.append(("Interactive Learning", check_interactive_learning()))
    
    # Check files
    print_header("4️⃣  Documentation & Files")
    found, total = check_files_exist()
    results.append((f"Files ({found}/{total})", found == total))
    
    # Print summary
    print_header("📊 VERIFICATION SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total_checks = len(results)
    success_rate = (passed / total_checks) * 100
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total_checks} checks passed ({success_rate:.1f}%){Colors.END}\n")
    
    for test_name, result in results:
        if result:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")
    
    # Final verdict
    print("\n" + "="*70)
    if passed == total_checks:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 SYSTEM READY FOR DEFENSE! 🎉{Colors.END}")
        print(f"{Colors.GREEN}All checks passed. You can confidently present your work.{Colors.END}\n")
    elif passed >= total_checks * 0.8:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  SYSTEM MOSTLY READY (minor issues){Colors.END}")
        print(f"{Colors.YELLOW}Most checks passed. Review failed checks before defense.{Colors.END}\n")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ SYSTEM NOT READY{Colors.END}")
        print(f"{Colors.RED}Multiple checks failed. Troubleshoot before defense.{Colors.END}\n")
    
    print("="*70 + "\n")
    
    # Recommendations
    if passed < total_checks:
        print_header("🔧 TROUBLESHOOTING RECOMMENDATIONS")
        
        if not any(r for name, r in results if "Frontend" in name):
            print_info("Frontend not responding:")
            print("  → Run: docker-compose restart frontend")
            print("  → Check: docker-compose logs frontend")
        
        if not any(r for name, r in results if "Backend" in name):
            print_info("Backend not responding:")
            print("  → Run: docker-compose restart backend")
            print("  → Check: docker-compose logs backend")
        
        if not any(r for name, r in results if "Interactive Learning" in name):
            print_info("Learning not working properly:")
            print("  → Restart Redis: docker-compose restart redis")
            print("  → Restart backend: docker-compose restart backend")
        
        print()
    
    # Exit code
    sys.exit(0 if passed == total_checks else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Verification interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{Colors.RED}Unexpected error: {str(e)}{Colors.END}")
        sys.exit(1)
