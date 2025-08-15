#!/usr/bin/env python3
"""
Test runner script for NASA MCP Demo.

This script provides various test running options including coverage reporting,
performance testing, and test categorization.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, capture_output=False):
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    
    if capture_output:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    else:
        return subprocess.run(cmd).returncode


def run_unit_tests(coverage=False, verbose=False):
    """Run unit tests."""
    cmd = ["python", "-m", "pytest", "tests/unit/"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=nasa_mcp_demo", "--cov-report=html", "--cov-report=term"])
    
    return run_command(cmd)


def run_integration_tests(coverage=False, verbose=False):
    """Run integration tests."""
    cmd = ["python", "-m", "pytest", "tests/integration/"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=nasa_mcp_demo", "--cov-report=html", "--cov-report=term"])
    
    return run_command(cmd)


def run_performance_tests(verbose=False):
    """Run performance tests."""
    cmd = ["python", "-m", "pytest", "-m", "performance"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd)


def run_all_tests(coverage=False, verbose=False, exclude_slow=False):
    """Run all tests."""
    cmd = ["python", "-m", "pytest", "tests/"]
    
    if verbose:
        cmd.append("-v")
    
    if exclude_slow:
        cmd.extend(["-m", "not slow"])
    
    if coverage:
        cmd.extend([
            "--cov=nasa_mcp_demo",
            "--cov-report=html",
            "--cov-report=term",
            "--cov-report=xml",
            "--cov-fail-under=80"
        ])
    
    return run_command(cmd)


def run_specific_test(test_path, verbose=False):
    """Run a specific test file or test function."""
    cmd = ["python", "-m", "pytest", test_path]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd)


def check_test_coverage():
    """Check current test coverage."""
    cmd = [
        "python", "-m", "pytest", 
        "--cov=nasa_mcp_demo",
        "--cov-report=term-missing",
        "--cov-report=html",
        "tests/"
    ]
    
    return run_command(cmd)


def run_linting():
    """Run code linting."""
    print("Running code linting...")
    
    # Run ruff
    ruff_result = run_command(["python", "-m", "ruff", "check", "nasa_mcp_demo/", "tests/"])
    
    # Run black check
    black_result = run_command(["python", "-m", "black", "--check", "nasa_mcp_demo/", "tests/"])
    
    # Run mypy
    mypy_result = run_command(["python", "-m", "mypy", "nasa_mcp_demo/"])
    
    return max(ruff_result, black_result, mypy_result)


def generate_test_report():
    """Generate comprehensive test report."""
    print("Generating comprehensive test report...")
    
    # Run tests with detailed reporting
    cmd = [
        "python", "-m", "pytest",
        "--cov=nasa_mcp_demo",
        "--cov-report=html:htmlcov",
        "--cov-report=xml:coverage.xml",
        "--cov-report=term",
        "--junit-xml=test-results.xml",
        "-v",
        "tests/"
    ]
    
    result = run_command(cmd)
    
    if result == 0:
        print("\nTest report generated successfully!")
        print("- HTML coverage report: htmlcov/index.html")
        print("- XML coverage report: coverage.xml")
        print("- JUnit test results: test-results.xml")
    
    return result


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="NASA MCP Demo Test Runner")
    
    parser.add_argument(
        "command",
        choices=[
            "unit", "integration", "performance", "all", "coverage", 
            "lint", "report", "specific"
        ],
        help="Test command to run"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Run tests in verbose mode"
    )
    
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run tests with coverage reporting"
    )
    
    parser.add_argument(
        "--exclude-slow",
        action="store_true",
        help="Exclude slow tests from execution"
    )
    
    parser.add_argument(
        "--test-path",
        help="Specific test file or function to run (for 'specific' command)"
    )
    
    args = parser.parse_args()
    
    # Change to project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Ensure we're in a virtual environment or have required packages
    try:
        import pytest
        import nasa_mcp_demo
    except ImportError as e:
        print(f"Error: Required packages not found: {e}")
        print("Please install the project dependencies:")
        print("pip install -e .[dev]")
        return 1
    
    # Run the specified command
    if args.command == "unit":
        return run_unit_tests(coverage=args.coverage, verbose=args.verbose)
    
    elif args.command == "integration":
        return run_integration_tests(coverage=args.coverage, verbose=args.verbose)
    
    elif args.command == "performance":
        return run_performance_tests(verbose=args.verbose)
    
    elif args.command == "all":
        return run_all_tests(
            coverage=args.coverage, 
            verbose=args.verbose,
            exclude_slow=args.exclude_slow
        )
    
    elif args.command == "coverage":
        return check_test_coverage()
    
    elif args.command == "lint":
        return run_linting()
    
    elif args.command == "report":
        return generate_test_report()
    
    elif args.command == "specific":
        if not args.test_path:
            print("Error: --test-path is required for 'specific' command")
            return 1
        return run_specific_test(args.test_path, verbose=args.verbose)
    
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())