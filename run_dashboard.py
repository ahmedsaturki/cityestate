"""
Dashboard Runner — تشغيل لوحة التحكم
======================================
Run the Streamlit dashboard.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def run_dashboard():
    """Run the Streamlit dashboard."""
    import subprocess

    dashboard_path = Path(__file__).parent / "src" / "dashboard" / "app.py"

    print("=" * 60)
    print("CityEstate Dashboard")
    print("=" * 60)
    print(f"Starting dashboard at: {dashboard_path}")
    print("Open http://localhost:8050 in your browser")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(dashboard_path),
        "--server.port", "8050",
        "--server.headless", "true",
    ])


if __name__ == "__main__":
    run_dashboard()
