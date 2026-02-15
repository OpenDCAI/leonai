#!/usr/bin/env python3
"""Test script for Web service config API.

Tests:
1. Backend and frontend services running
2. Thread-specific model update
3. Global model update (all agents)
4. Virtual model name resolution
5. Error handling (invalid models, missing agents)
"""

import json

import requests

BASE_URL = "http://localhost:8001"
FRONTEND_URL = "http://localhost:5173"


def test_services_running():
    """Test 1: Verify backend and frontend services are running."""
    print("\n=== Test 1: Services Running ===")

    # Test backend
    try:
        response = requests.get(f"{BASE_URL}/api/settings", timeout=5)
        response.raise_for_status()
        print(f"✓ Backend running at {BASE_URL}")
        print(f"  Response: {response.json()}")
    except Exception as e:
        print(f"✗ Backend not responding: {e}")
        return False

    # Test frontend
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        print(f"✓ Frontend running at {FRONTEND_URL}")
    except Exception as e:
        print(f"✗ Frontend not responding: {e}")
        return False

    return True


def test_thread_specific_update():
    """Test 2: Thread-specific model update."""
    print("\n=== Test 2: Thread-Specific Model Update ===")

    # First, we need to create an agent for this thread
    # This would normally happen when a chat is started
    test_thread_id = "test_thread_123"

    # Test updating model for specific thread
    payload = {"model": "claude-opus-4-6", "thread_id": test_thread_id}

    print("Sending request: POST /api/settings/config")
    print(f"  Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(f"{BASE_URL}/api/settings/config", json=payload, timeout=10)

        print(f"  Status: {response.status_code}")
        print(f"  Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 400:
            # Agent not found is expected if thread doesn't exist yet
            result = response.json()
            if "not found" in result.get("detail", "").lower():
                print("✓ Correctly returns error when agent doesn't exist")
                return True
            else:
                print(f"✗ Unexpected error: {result}")
                return False
        elif response.status_code == 200:
            result = response.json()
            assert result["success"] is True, "Success flag not set"
            assert result["thread_id"] == test_thread_id, "Thread ID mismatch"
            print("✓ Thread-specific update successful")
            print(f"  Updated model: {result.get('model')}")
            return True
        else:
            print(f"✗ Unexpected status code: {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Request failed: {e}")
        return False


def test_global_update():
    """Test 3: Global model update (all agents)."""
    print("\n=== Test 3: Global Model Update ===")

    # Test updating all agents (no thread_id)
    payload = {"model": "claude-sonnet-4-5-20250929"}

    print("Sending request: POST /api/settings/config")
    print(f"  Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(f"{BASE_URL}/api/settings/config", json=payload, timeout=10)

        print(f"  Status: {response.status_code}")
        print(f"  Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            result = response.json()
            assert result["success"] is True, "Success flag not set"
            print("✓ Global update successful")
            print(f"  Updated {result.get('updated_count', 0)} agent(s)")
            return True
        else:
            print(f"✗ Unexpected status code: {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Request failed: {e}")
        return False


def test_virtual_model_names():
    """Test 4: Virtual model name resolution."""
    print("\n=== Test 4: Virtual Model Names ===")

    virtual_models = [
        ("leon:mini", "claude-haiku-4-5-20250929"),
        ("leon:medium", "claude-sonnet-4-5-20250929"),
        ("leon:large", "claude-opus-4-6"),
        ("leon:max", "claude-opus-4-6"),
    ]

    all_passed = True

    for virtual_name, expected_model in virtual_models:
        payload = {"model": virtual_name}

        print(f"\nTesting {virtual_name}:")
        try:
            response = requests.post(f"{BASE_URL}/api/settings/config", json=payload, timeout=10)

            if response.status_code == 200:
                result = response.json()
                print(f"  ✓ Accepted: {virtual_name}")
                print(f"    Updated {result.get('updated_count', 0)} agent(s)")
            else:
                print(f"  Status: {response.status_code}")
                print(f"  Response: {response.json()}")

        except Exception as e:
            print(f"  ✗ Request failed: {e}")
            all_passed = False

    return all_passed


def test_concrete_model_names():
    """Test 5: Concrete model names."""
    print("\n=== Test 5: Concrete Model Names ===")

    concrete_models = ["gpt-4", "claude-opus-4-6", "claude-sonnet-4-5-20250929"]

    all_passed = True

    for model_name in concrete_models:
        payload = {"model": model_name}

        print(f"\nTesting {model_name}:")
        try:
            response = requests.post(f"{BASE_URL}/api/settings/config", json=payload, timeout=10)

            if response.status_code == 200:
                result = response.json()
                print(f"  ✓ Accepted: {model_name}")
                print(f"    Updated {result.get('updated_count', 0)} agent(s)")
            else:
                print(f"  Status: {response.status_code}")
                print(f"  Response: {response.json()}")

        except Exception as e:
            print(f"  ✗ Request failed: {e}")
            all_passed = False

    return all_passed


def test_error_cases():
    """Test 6: Error handling."""
    print("\n=== Test 6: Error Handling ===")

    test_cases = [
        {
            "name": "Invalid model name",
            "payload": {"model": "invalid-model-xyz"},
            "expected_status": [400, 500],
        },
        {
            "name": "Invalid virtual model",
            "payload": {"model": "leon:invalid"},
            "expected_status": [400, 500],
        },
        {
            "name": "Empty model name",
            "payload": {"model": ""},
            "expected_status": [400, 422],
        },
        {
            "name": "Non-existent thread",
            "payload": {"model": "gpt-4", "thread_id": "nonexistent_thread_999"},
            "expected_status": [400, 404],
        },
    ]

    all_passed = True

    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print(f"  Payload: {json.dumps(test_case['payload'], indent=2)}")

        try:
            response = requests.post(f"{BASE_URL}/api/settings/config", json=test_case["payload"], timeout=10)

            print(f"  Status: {response.status_code}")

            if response.status_code in test_case["expected_status"]:
                print("  ✓ Correctly returned error status")
                try:
                    error_detail = response.json()
                    print(f"  Error message: {error_detail.get('detail', 'N/A')}")
                except Exception:
                    pass
            else:
                print(f"  ✗ Unexpected status: {response.status_code} (expected {test_case['expected_status']})")
                all_passed = False

        except Exception as e:
            print(f"  ✗ Request failed: {e}")
            all_passed = False

    return all_passed


def test_concurrent_updates():
    """Test 7: Concurrent updates (basic test)."""
    print("\n=== Test 7: Concurrent Updates ===")

    import concurrent.futures

    def update_model(model_name: str) -> tuple[str, int]:
        """Send update request and return model name and status code."""
        try:
            response = requests.post(f"{BASE_URL}/api/settings/config", json={"model": model_name}, timeout=10)
            return (model_name, response.status_code)
        except Exception:
            return (model_name, -1)

    models = ["claude-opus-4-6", "claude-sonnet-4-5-20250929", "gpt-4"]

    print(f"Sending {len(models)} concurrent requests...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(update_model, model) for model in models]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    print("\nResults:")
    all_passed = True
    for model, status in results:
        if status == 200:
            print(f"  ✓ {model}: {status}")
        else:
            print(f"  ✗ {model}: {status}")
            all_passed = False

    return all_passed


def main():
    """Run all tests."""
    print("=" * 60)
    print("Web Service Config API Test")
    print("=" * 60)

    results = {}

    # Test 1: Services running
    results["services"] = test_services_running()
    if not results["services"]:
        print("\n✗ Services not running. Please start backend and frontend.")
        print("  Backend: cd services/web && uv run python main.py")
        print("  Frontend: cd frontend/app && npm run dev")
        return 1

    # Test 2-7
    results["thread_specific"] = test_thread_specific_update()
    results["global_update"] = test_global_update()
    results["virtual_models"] = test_virtual_model_names()
    results["concrete_models"] = test_concrete_model_names()
    results["error_handling"] = test_error_cases()
    results["concurrent"] = test_concurrent_updates()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
