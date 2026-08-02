"""
Test Runner for CityEstate
==========================
Run all tests with pytest.
"""

import subprocess
import sys
from pathlib import Path


def run_tests():
    """Run all tests with pytest."""
    project_root = Path(__file__).parent
    
    # Install pytest if not available
    try:
        import pytest
    except ImportError:
        print("Installing pytest...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest>=7.4.0", "pytest-asyncio>=0.23.0"])
    
    # Run tests
    print("=" * 60)
    print("Running CityEstate Tests")
    print("=" * 60)
    
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            str(project_root / "tests"),
            "-v",
            "--tb=short",
            "-x",  # Stop on first failure
            "-W", "ignore::DeprecationWarning",
        ],
        cwd=str(project_root),
    )
    
    print("=" * 60)
    if result.returncode == 0:
        print("All tests passed!")
    else:
        print("Some tests failed!")
    print("=" * 60)
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests())
