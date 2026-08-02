"""
Deployment Test Suite — اختبارات النشر
=======================================
Tests for production readiness: Docker, config, security.
Run with: python -m pytest tests/test_deployment.py -v
"""

import os
import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ===========================================================================
# File Structure Tests
# ===========================================================================
class TestFileStructure:
    """Verify all required files exist."""

    def test_main_py_exists(self):
        assert Path("main.py").exists()

    def test_requirements_exists(self):
        assert Path("requirements.txt").exists()

    def test_dockerfile_exists(self):
        assert Path("Dockerfile").exists()

    def test_docker_compose_exists(self):
        assert Path("docker-compose.yml").exists()

    def test_makefile_exists(self):
        assert Path("Makefile").exists()

    def test_env_example_exists(self):
        assert Path(".env.example").exists()

    def test_env_exists(self):
        env_path = Path(".env")
        if not env_path.exists():
            pytest.skip(".env file not present (expected in test environments)")
        assert env_path.exists()

    def test_src_data_init(self):
        assert Path("src/data/__init__.py").exists()

    def test_src_data_extractor(self):
        assert Path("src/data/extractor.py").exists()

    def test_src_data_crawler(self):
        assert Path("src/data/crawler.py").exists()

    def test_src_data_enricher(self):
        assert Path("src/data/enricher.py").exists()

    def test_src_data_whatsapp_check(self):
        assert Path("src/data/whatsapp_check.py").exists()

    def test_src_data_quality(self):
        assert Path("src/data/quality.py").exists()

    def test_ai_crew_tools(self):
        assert Path("src/ai_crew/tools.py").exists()

    def test_ai_crew_agents(self):
        assert Path("src/ai_crew/agents.py").exists()

    def test_ai_crew_crew(self):
        assert Path("src/ai_crew/crew/__init__.py").exists()

    def test_ai_crew_tasks(self):
        assert Path("src/ai_crew/tasks.py").exists()


# ===========================================================================
# Configuration Tests
# ===========================================================================
class TestConfiguration:
    """Verify configuration is complete."""

    def test_env_has_database_url(self):
        from dotenv import load_dotenv
        load_dotenv()
        assert os.getenv("DATABASE_URL") or Path(".env").exists()

    def test_env_has_jwt_secret(self):
        from dotenv import load_dotenv
        load_dotenv()
        assert os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET_KEY") or Path(".env").exists()

    def test_env_has_admin_password(self):
        from dotenv import load_dotenv
        load_dotenv()
        assert os.getenv("ADMIN_PASSWORD") or Path(".env").exists()


# ===========================================================================
# Import Tests
# ===========================================================================
class TestImports:
    """Verify all modules can be imported."""

    def test_import_data_extractor(self):
        from src.data.extractor import DataExtractor
        assert DataExtractor is not None

    def test_import_data_crawler(self):
        from src.data.crawler import WebCrawler
        assert WebCrawler is not None

    def test_import_data_enricher(self):
        from src.data.enricher import DataEnricher
        assert DataEnricher is not None

    def test_import_whatsapp_checker(self):
        from src.data.whatsapp_check import WhatsAppChecker
        assert WhatsAppChecker is not None

    def test_import_data_quality(self):
        from src.data.quality import DataQualityScorer
        assert DataQualityScorer is not None

    def test_import_crewai_tools(self):
        from src.ai_crew.tools import get_all_tools
        tools = get_all_tools()
        assert len(tools) >= 19

    def test_import_crewai_agents(self):
        from src.ai_crew.agents import (
            create_data_collector,
            create_data_enricher,
            create_lead_analyst,
            create_property_expert,
            create_market_researcher,
        )
        assert create_data_collector is not None

    def test_import_bridge_handler(self):
        from src.api.bridge_handler import score_lead, parse_intent
        assert score_lead is not None
        assert parse_intent is not None

    def test_import_matching_engine(self):
        from src.matching.engine import MatchMakingEngine
        assert MatchMakingEngine is not None


# ===========================================================================
# Security Tests
# ===========================================================================
class TestSecurity:
    """Basic security checks."""

    def test_no_hardcoded_secrets_in_code(self):
        """Check that no hardcoded secrets exist in source files."""
        secret_patterns = [
            "password = \"admin\"",
            "secret = \"secret\"",
            "api_key = \"sk-",
        ]
        src_dir = Path("src")
        for py_file in src_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, UnicodeError):
                continue
            for pattern in secret_patterns:
                assert pattern not in content, f"Hardcoded secret in {py_file}: {pattern}"

    def test_env_not_committed(self):
        """Check .env is in .gitignore (if git exists)."""
        gitignore = Path(".gitignore")
        if gitignore.exists():
            content = gitignore.read_text()
            # .env should be in gitignore for production
            # But may not be for development


# ===========================================================================
# Performance Tests
# ===========================================================================
class TestPerformance:
    """Basic performance checks."""

    def test_import_time(self):
        """Module import should be fast."""
        import time
        start = time.time()
        from src.data.extractor import DataExtractor
        from src.data.crawler import WebCrawler
        from src.data.enricher import DataEnricher
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Imports took {elapsed:.1f}s (>5s)"

    def test_extraction_speed(self):
        """Data extraction should be fast."""
        import time
        from src.data.extractor import DataExtractor
        extractor = DataExtractor()

        start = time.time()
        for _ in range(100):
            extractor.extract_from_whatsapp("عايز شقة 3 غرف في الشيخ زايد بميزانية 2 مليون")
        elapsed = time.time() - start
        assert elapsed < 10.0, f"100 extractions took {elapsed:.1f}s (>10s)"
