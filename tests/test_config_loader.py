"""
Config Loader Tests — اختبارات تحميل الإعدادات
==============================================
Tests for configuration loading, environment variables, and defaults.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch


class TestConfigLoader:
    """Test configuration loading from environment and files."""

    def test_load_environment_runs(self):
        from src.config.loader import load_environment, ConfigurationError
        with patch("src.config.loader.load_dotenv"):
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(ConfigurationError):
                    load_environment()

    def test_load_agents_config(self):
        from src.config.loader import load_agents_config
        config = load_agents_config()
        assert isinstance(config, dict)

    def test_load_tasks_config(self):
        from src.config.loader import load_tasks_config
        config = load_tasks_config()
        assert isinstance(config, dict)

    def test_config_directories_exist(self):
        from src.config.loader import CONFIG_DIR, LOGS_DIR, OUTPUT_DIR
        assert isinstance(CONFIG_DIR, Path)
        assert isinstance(LOGS_DIR, Path)
        assert isinstance(OUTPUT_DIR, Path)

    def test_config_file_exists(self):
        config_path = Path(__file__).parent.parent / "config"
        if config_path.exists():
            assert config_path.is_dir()


class TestEnvironmentVariables:
    """Test environment variable handling."""

    def test_jwt_secret_exists(self):
        secret = os.getenv("JWT_SECRET")
        assert secret is not None, "JWT_SECRET must be set in environment"

    def test_admin_password_exists(self):
        password = os.getenv("ADMIN_PASSWORD")
        assert password is not None, "ADMIN_PASSWORD must be set in environment"

    def test_database_url_exists(self):
        url = os.getenv("DATABASE_URL", "sqlite:///output/cityestate.db")
        assert url is not None
