"""Unit tests for config module"""

import pytest
import os
from unittest.mock import patch
from config import Config


class TestConfig:
    """Test cases for Config class"""

    def test_default_values(self):
        """Test default configuration values"""
        # These should have default values even without .env
        assert isinstance(Config.HEADLESS, bool)
        assert Config.BROWSER_TYPE == os.getenv("BROWSER_TYPE", "chromium")
        assert Config.MODEL_NAME == os.getenv("MODEL_NAME", "gpt-4o")

    def test_search_keywords_parsing(self):
        """Test parsing of search keywords from environment

        Note: Module reload is necessary here because Config class attributes
        are loaded at import time from environment variables. This is a design
        limitation of the current Config implementation but is acceptable for
        these isolated tests.
        """
        with patch.dict(os.environ, {"SEARCH_KEYWORDS": "python,javascript,react"}):
            from importlib import reload
            import config as config_module

            reload(config_module)

            # Should parse comma-separated keywords
            assert len(config_module.config.SEARCH_KEYWORDS) == 3
            assert "python" in config_module.config.SEARCH_KEYWORDS
            assert "javascript" in config_module.config.SEARCH_KEYWORDS
            assert "react" in config_module.config.SEARCH_KEYWORDS

    def test_locations_parsing(self):
        """Test parsing of locations from environment"""
        with patch.dict(os.environ, {"LOCATIONS": "Київ,Львів,Одеса"}):
            from importlib import reload
            import config as config_module

            reload(config_module)

            # Should parse comma-separated locations
            assert len(config_module.config.LOCATIONS) == 3
            assert "Київ" in config_module.config.LOCATIONS
            assert "Львів" in config_module.config.LOCATIONS

    def test_remote_only_parsing(self):
        """Test parsing of remote_only flag"""
        with patch.dict(os.environ, {"REMOTE_ONLY": "true"}):
            from importlib import reload
            import config as config_module

            reload(config_module)

            assert config_module.config.REMOTE_ONLY is True

        with patch.dict(os.environ, {"REMOTE_ONLY": "false"}):
            from importlib import reload

            reload(config_module)

            assert config_module.config.REMOTE_ONLY is False

    def test_integer_parsing(self):
        """Test parsing of integer configuration values"""
        with patch.dict(
            os.environ, {"MAX_APPLICATIONS": "25", "MIN_SCORE": "8", "MIN_SALARY": "5"}
        ):
            from importlib import reload
            import config as config_module

            reload(config_module)

            assert config_module.config.MAX_APPLICATIONS == 25
            assert config_module.config.MIN_SCORE == 8
            assert config_module.config.MIN_SALARY == 5

    def test_float_parsing(self):
        """Test parsing of float configuration values"""
        with patch.dict(os.environ, {"TEMPERATURE": "0.5"}):
            from importlib import reload
            import config as config_module

            reload(config_module)

            assert config_module.config.TEMPERATURE == 0.5

    def test_url_constants(self):
        """Test URL constants are set correctly"""
        assert Config.WORKUA_BASE_URL == "https://www.work.ua"
        assert Config.WORKUA_LOGIN_URL == "https://www.work.ua/ua/login/"
        assert Config.WORKUA_SEARCH_URL == "https://www.work.ua/jobs/"

    def test_validate_with_api_key(self):
        """Test validation with API key present"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            from importlib import reload
            import config as config_module

            reload(config_module)

            # Should not raise an error
            result = config_module.config.validate()
            assert result is True

    def test_validate_without_api_key(self):
        """Test validation without API key"""
        with patch.dict(os.environ, {}, clear=True):
            from importlib import reload
            import config as config_module

            reload(config_module)

            # Should raise ValueError
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                config_module.config.validate()

    def test_empty_keyword_filtering(self):
        """Test that empty keywords are filtered out"""
        with patch.dict(os.environ, {"SEARCH_KEYWORDS": "python,,javascript, ,react"}):
            from importlib import reload
            import config as config_module

            reload(config_module)

            # Should filter out empty strings
            keywords = config_module.config.SEARCH_KEYWORDS
            assert len(keywords) == 3
            assert "" not in keywords
            assert " " not in keywords

    def test_use_llm_flag(self):
        """Test USE_LLM flag parsing"""
        with patch.dict(os.environ, {"USE_LLM": "true"}):
            from importlib import reload
            import config as config_module

            reload(config_module)

            assert config_module.config.USE_LLM is True

        with patch.dict(os.environ, {"USE_LLM": "false"}):
            from importlib import reload

            reload(config_module)

            assert config_module.config.USE_LLM is False
