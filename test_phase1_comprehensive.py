#!/usr/bin/env python3
"""
Comprehensive test execution script for Phase 1.

This script runs all Phase 1 tests and validates the comprehensive test suite
implementation according to task requirements.
"""

import os
import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd, capture_output=True):
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=capture_output, text=True)
    return result.returncode, result.stdout, result.stderr


def check_test_files_exist():
    """Check that all required test files exist."""
    print("Checking test file structure...")
    
    required_files = [
        "tests/fixtures/nasa_api_responses.py",
        "tests/integration/test_fastapi_endpoints.py",
        "tests/integration/test_nasa_service_integration.py", 
        "tests/integration/test_logging_integration.py",
        "tests/integration/test_error_handling.py",
        "tests/integration/test_performance.py",
        "tests/integration/test_comprehensive_endpoints.py",
        "tests/unit/test_models.py",
        "tests/unit/test_nasa_client.py",
        "tests/unit/test_nasa_service.py",
        "tests/conftest.py",
        "tests/run_tests.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing test files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    else:
        print("✅ All required test files exist")
        return True


def run_unit_tests():
    """Run unit tests."""
    print("\n" + "="*50)
    print("RUNNING UNIT TESTS")
    print("="*50)
    
    cmd = [
        "python", "-m", "pytest", 
        "tests/unit/",
        "-v",
        "--tb=short"
    ]
    
    return_code, stdout, stderr = run_command(cmd)
    
    print(stdout)
    if stderr:
        print("STDERR:", stderr)
    
    return return_code == 0


def run_integration_tests():
    """Run integration tests."""
    print("\n" + "="*50)
    print("RUNNING INTEGRATION TESTS")
    print("="*50)
    
    cmd = [
        "python", "-m", "pytest",
        "tests/integration/",
        "-v",
        "--tb=short"
    ]
    
    return_code, stdout, stderr = run_command(cmd)
    
    print(stdout)
    if stderr:
        print("STDERR:", stderr)
    
    return return_code == 0


def run_error_handling_tests():
    """Run error handling tests specifically."""
    print("\n" + "="*50)
    print("RUNNING ERROR HANDLING TESTS")
    print("="*50)
    
    cmd = [
        "python", "-m", "pytest",
        "tests/integration/test_error_handling.py",
        "-v",
        "--tb=short"
    ]
    
    return_code, stdout, stderr = run_command(cmd)
    
    print(stdout)
    if stderr:
        print("STDERR:", stderr)
    
    return return_code == 0


def run_performance_tests():
    """Run performance tests."""
    print("\n" + "="*50)
    print("RUNNING PERFORMANCE TESTS")
    print("="*50)
    
    cmd = [
        "python", "-m", "pytest",
        "tests/integration/test_performance.py",
        "-v",
        "--tb=short",
        "-m", "not slow"  # Exclude slow tests for faster execution
    ]
    
    return_code, stdout, stderr = run_command(cmd)
    
    print(stdout)
    if stderr:
        print("STDERR:", stderr)
    
    return return_code == 0


def run_comprehensive_endpoint_tests():
    """Run comprehensive endpoint tests."""
    print("\n" + "="*50)
    print("RUNNING COMPREHENSIVE ENDPOINT TESTS")
    print("="*50)
    
    cmd = [
        "python", "-m", "pytest",
        "tests/integration/test_comprehensive_endpoints.py",
        "-v",
        "--tb=short"
    ]
    
    return_code, stdout, stderr = run_command(cmd)
    
    print(stdout)
    if stderr:
        print("STDERR:", stderr)
    
    return return_code == 0


def generate_coverage_report():
    """Generate test coverage report."""
    print("\n" + "="*50)
    print("GENERATING COVERAGE REPORT")
    print("="*50)
    
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "--cov=nasa_mcp_demo",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-fail-under=70",  # Require at least 70% coverage
        "-q"  # Quiet mode for coverage
    ]
    
    return_code, stdout, stderr = run_command(cmd)
    
    print(stdout)
    if stderr:
        print("STDERR:", stderr)
    
    if return_code == 0:
        print("✅ Coverage report generated successfully")
        print("📊 HTML coverage report: htmlcov/index.html")
    else:
        print("❌ Coverage requirements not met")
    
    return return_code == 0


def validate_mock_responses():
    """Validate mock NASA API responses."""
    print("\n" + "="*50)
    print("VALIDATING MOCK RESPONSES")
    print("="*50)
    
    try:
        from tests.fixtures.nasa_api_responses import (
            MockNASAResponses,
            SAMPLE_APOD_RESPONSES,
            SAMPLE_MARS_RESPONSES,
            SAMPLE_NEO_RESPONSES,
            ERROR_RESPONSES
        )
        
        # Test APOD responses
        apod_response = MockNASAResponses.get_apod_response()
        assert "date" in apod_response
        assert "title" in apod_response
        assert "explanation" in apod_response
        print("✅ APOD mock responses valid")
        
        # Test Mars rover responses
        mars_response = MockNASAResponses.get_mars_rover_response()
        assert "photos" in mars_response
        print("✅ Mars rover mock responses valid")
        
        # Test NEO responses
        neo_response = MockNASAResponses.get_neo_response("2023-12-01", "2023-12-01")
        assert "near_earth_objects" in neo_response
        assert "element_count" in neo_response
        print("✅ NEO mock responses valid")
        
        # Test error responses
        error_response = MockNASAResponses.get_error_response(404)
        assert "error" in error_response
        print("✅ Error mock responses valid")
        
        print("✅ All mock responses validated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Mock response validation failed: {e}")
        return False


def check_test_requirements():
    """Check that test requirements are met."""
    print("\n" + "="*50)
    print("CHECKING TEST REQUIREMENTS")
    print("="*50)
    
    requirements_met = True
    
    # Check for pytest and related packages
    try:
        import pytest
        import pytest_asyncio
        import pytest_cov
        print("✅ Pytest and plugins available")
    except ImportError as e:
        print(f"❌ Missing pytest dependencies: {e}")
        requirements_met = False
    
    # Check for application dependencies
    try:
        import nasa_mcp_demo
        from nasa_mcp_demo.main import app
        from nasa_mcp_demo.services.nasa_service import NASAService
        print("✅ Application modules importable")
    except ImportError as e:
        print(f"❌ Cannot import application modules: {e}")
        requirements_met = False
    
    # Check for test utilities
    try:
        from unittest.mock import AsyncMock, Mock, patch
        from fastapi.testclient import TestClient
        import httpx
        print("✅ Test utilities available")
    except ImportError as e:
        print(f"❌ Missing test utilities: {e}")
        requirements_met = False
    
    return requirements_met


def run_quick_smoke_test():
    """Run a quick smoke test to ensure basic functionality."""
    print("\n" + "="*50)
    print("RUNNING SMOKE TEST")
    print("="*50)
    
    try:
        from fastapi.testclient import TestClient
        from nasa_mcp_demo.main import app
        
        client = TestClient(app)
        
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        print("✅ Root endpoint working")
        
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        print("✅ Health endpoint working")
        
        # Test rovers endpoint
        response = client.get("/rovers")
        assert response.status_code == 200
        print("✅ Rovers endpoint working")
        
        # Test OpenAPI docs
        response = client.get("/openapi.json")
        assert response.status_code == 200
        print("✅ OpenAPI documentation working")
        
        print("✅ Smoke test passed")
        return True
        
    except Exception as e:
        print(f"❌ Smoke test failed: {e}")
        return False


def main():
    """Main test execution function."""
    print("NASA MCP Demo - Phase 1 Comprehensive Test Suite")
    print("=" * 60)
    
    start_time = time.time()
    
    # Step 1: Check test file structure
    if not check_test_files_exist():
        print("❌ Test suite setup incomplete")
        return 1
    
    # Step 2: Check requirements
    if not check_test_requirements():
        print("❌ Test requirements not met")
        return 1
    
    # Step 3: Run smoke test
    if not run_quick_smoke_test():
        print("❌ Basic functionality not working")
        return 1
    
    # Step 4: Validate mock responses
    if not validate_mock_responses():
        print("❌ Mock responses invalid")
        return 1
    
    # Step 5: Run all test categories
    test_results = []
    
    print("\n" + "🧪 EXECUTING COMPREHENSIVE TEST SUITE" + "\n")
    
    # Unit tests
    test_results.append(("Unit Tests", run_unit_tests()))
    
    # Integration tests
    test_results.append(("Integration Tests", run_integration_tests()))
    
    # Error handling tests
    test_results.append(("Error Handling Tests", run_error_handling_tests()))
    
    # Performance tests
    test_results.append(("Performance Tests", run_performance_tests()))
    
    # Comprehensive endpoint tests
    test_results.append(("Comprehensive Endpoint Tests", run_comprehensive_endpoint_tests()))
    
    # Coverage report
    test_results.append(("Coverage Report", generate_coverage_report()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST EXECUTION SUMMARY")
    print("="*60)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<30} {status}")
        if result:
            passed_tests += 1
    
    print(f"\nOverall: {passed_tests}/{total_tests} test categories passed")
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"Total execution time: {duration:.2f} seconds")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! Phase 1 test suite is comprehensive and working.")
        return 0
    else:
        print(f"\n❌ {total_tests - passed_tests} test categories failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())