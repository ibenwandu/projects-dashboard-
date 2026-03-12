#!/usr/bin/env python
"""Run all OANDA integration tests.

Comprehensive test runner that executes:
1. Database schema tests
2. Database CRUD operation tests
3. OandaClient API tests
4. TradingAgent validation tests
5. End-to-end integration tests
"""
import subprocess
import sys
import os

def run_test(test_file: str, description: str) -> bool:
    """Run a single test file and report results."""
    print(f"\n{'='*70}")
    print(f"Running: {description}")
    print(f"File: {test_file}")
    print('='*70)

    result = subprocess.run(
        [sys.executable, test_file],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        capture_output=False
    )

    if result.returncode == 0:
        print(f"[OK] {description} PASSED")
        return True
    else:
        print(f"[FAIL] {description} FAILED")
        return False


def main():
    """Run all test suites."""
    print("\n" + "="*70)
    print("OANDA INTEGRATION TEST SUITE")
    print("="*70)

    tests = [
        ("test_database_oanda.py", "Database Schema Tests"),
        ("test_database_crud.py", "Database CRUD Tests"),
        ("test_oanda_client.py", "OandaClient Tests"),
        ("test_trading_agent.py", "TradingAgent Validation Tests"),
        ("test_oanda_integration.py", "End-to-End Integration Tests"),
    ]

    results = {}
    for test_file, description in tests:
        results[description] = run_test(test_file, description)

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for description, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {description}")

    print("\n" + "-"*70)
    print(f"Total: {passed}/{total} test suites passed")
    print("-"*70)

    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[ERROR] {total - passed} test suite(s) failed")
        return 1


if __name__ == '__main__':
    exit(main())
