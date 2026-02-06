"""Tests for environment variable loading functionality"""

import pytest
import os
from unittest.mock import patch, mock_open


class TestFilterLoading:
    """Test filter loading from environment variables"""

    def test_filter_content_from_env(self):
        """Test loading filter content from FILTER_CONTENT environment variable"""
        filter_content = "Я шукаю Python розробника з зарплатою від 50000 грн"
        
        with patch.dict(os.environ, {"FILTER_CONTENT": filter_content}):
            from importlib import reload
            import config as config_module
            reload(config_module)
            
            assert config_module.config.FILTER_CONTENT == filter_content

    def test_filter_path_from_env(self):
        """Test loading filter path from FILTER_PATH environment variable"""
        filter_path = "./custom_filter.txt"
        
        with patch.dict(os.environ, {"FILTER_PATH": filter_path}):
            from importlib import reload
            import config as config_module
            reload(config_module)
            
            assert config_module.config.FILTER_PATH == filter_path

    def test_filter_content_and_path_both_set(self):
        """Test when both FILTER_CONTENT and FILTER_PATH are set"""
        filter_content = "Filter content"
        filter_path = "./filter.txt"
        
        with patch.dict(os.environ, {
            "FILTER_CONTENT": filter_content,
            "FILTER_PATH": filter_path
        }):
            from importlib import reload
            import config as config_module
            reload(config_module)
            
            # Both should be available
            assert config_module.config.FILTER_CONTENT == filter_content
            assert config_module.config.FILTER_PATH == filter_path


class TestCookiesLoading:
    """Test cookies loading from environment variables"""

    def test_cookies_from_env(self):
        """Test loading cookies from WORKUA_COOKIES environment variable"""
        cookies_json = '[{"name":"session","value":"test123","domain":".work.ua"}]'
        
        with patch.dict(os.environ, {"WORKUA_COOKIES": cookies_json}):
            from importlib import reload
            import config as config_module
            reload(config_module)
            
            assert config_module.config.WORKUA_COOKIES == cookies_json

    def test_phone_and_cookies_both_set(self):
        """Test when both WORKUA_PHONE and WORKUA_COOKIES are set"""
        phone = "+380123456789"
        cookies = '[{"name":"session","value":"test"}]'
        
        with patch.dict(os.environ, {
            "WORKUA_PHONE": phone,
            "WORKUA_COOKIES": cookies
        }):
            from importlib import reload
            import config as config_module
            reload(config_module)
            
            # Both should be available
            assert config_module.config.WORKUA_PHONE == phone
            assert config_module.config.WORKUA_COOKIES == cookies


class TestConfigValidation:
    """Test configuration validation"""

    def test_validate_missing_phone_and_cookies(self, tmp_path, monkeypatch):
        """Test validation fails when neither WORKUA_PHONE nor WORKUA_COOKIES is set"""
        # Run in an isolated temporary directory with no cookies.json present
        monkeypatch.chdir(tmp_path)
        
        with patch.dict(os.environ, {
            "SEARCH_KEYWORDS": "python developer",
            "LOCATIONS": "Київ"
        }, clear=True):
            from importlib import reload
            import config as config_module
            reload(config_module)
            
            with pytest.raises(ValueError, match="WORKUA_PHONE, WORKUA_COOKIES, or cookies.json"):
                config_module.config.validate()

    def test_validate_missing_search_keywords(self):
        """Test validation fails when SEARCH_KEYWORDS is empty"""
        with patch.dict(os.environ, {
            "WORKUA_PHONE": "+380123456789",
            "SEARCH_KEYWORDS": "",
            "LOCATIONS": "Київ"
        }, clear=True):
            from importlib import reload
            import config as config_module
            reload(config_module)
            
            with pytest.raises(ValueError, match="SEARCH_KEYWORDS"):
                config_module.config.validate()

    def test_validate_llm_enabled_missing_api_key(self):
        """Test validation fails when LLM is enabled but API key is missing"""
        with patch.dict(os.environ, {
            "WORKUA_PHONE": "+380123456789",
            "SEARCH_KEYWORDS": "python",
            "LOCATIONS": "Київ",
            "USE_LLM": "true"
        }, clear=True):
            from importlib import reload
            import config as config_module
            reload(config_module)
            
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                config_module.config.validate()

    def test_validate_llm_enabled_missing_filter(self):
        """Test validation fails when LLM is enabled but filter is missing"""
        with patch.dict(os.environ, {
            "WORKUA_PHONE": "+380123456789",
            "SEARCH_KEYWORDS": "python",
            "LOCATIONS": "Київ",
            "USE_LLM": "true",
            "OPENAI_API_KEY": "test-key"
        }, clear=True):
            from importlib import reload
            import config as config_module
            reload(config_module)
            
            with pytest.raises(ValueError, match="FILTER_PATH or FILTER_CONTENT"):
                config_module.config.validate()

    def test_validate_success_with_phone(self):
        """Test validation succeeds with required fields"""
        with patch.dict(os.environ, {
            "WORKUA_PHONE": "+380123456789",
            "SEARCH_KEYWORDS": "python developer",
            "LOCATIONS": "Київ"
        }, clear=True):
            from importlib import reload
            import config as config_module
            reload(config_module)
            
            # Should not raise
            assert config_module.config.validate() is True

    def test_validate_success_with_cookies(self):
        """Test validation succeeds with cookies instead of phone"""
        with patch.dict(os.environ, {
            "WORKUA_COOKIES": '[{"name":"test"}]',
            "SEARCH_KEYWORDS": "python developer",
            "LOCATIONS": "Київ"
        }, clear=True):
            from importlib import reload
            import config as config_module
            reload(config_module)
            
            # Should not raise
            assert config_module.config.validate() is True

    def test_validate_success_with_llm_and_filter_content(self):
        """Test validation succeeds with LLM enabled and filter content"""
        with patch.dict(os.environ, {
            "WORKUA_PHONE": "+380123456789",
            "SEARCH_KEYWORDS": "python",
            "LOCATIONS": "Київ",
            "USE_LLM": "true",
            "OPENAI_API_KEY": "test-key",
            "FILTER_CONTENT": "Test filter"
        }, clear=True):
            from importlib import reload
            import config as config_module
            reload(config_module)
            
            # Should not raise
            assert config_module.config.validate() is True


class TestLLMServiceFilterLoading:
    """Test LLM service filter loading"""

    def test_load_filter_from_content(self):
        """Test loading filter from FILTER_CONTENT"""
        filter_text = "Тестовий фільтр"
        with patch.dict(os.environ, {"FILTER_CONTENT": filter_text}, clear=False):
            # Patch the config values directly
            with patch("llm_service.config") as mock_config:
                mock_config.FILTER_CONTENT = filter_text
                mock_config.FILTER_PATH = None
                
                from llm_service import load_filter_content
                result = load_filter_content()
                assert result == filter_text

    def test_load_filter_from_file(self):
        """Test loading filter from FILTER_PATH"""
        filter_text = "File filter content"
        filter_path = "./test_filter.txt"
        
        with patch("llm_service.config") as mock_config:
            mock_config.FILTER_CONTENT = None
            mock_config.FILTER_PATH = filter_path
            
            with patch("os.path.exists", return_value=True):
                with patch("builtins.open", mock_open(read_data=filter_text)):
                    from llm_service import load_filter_content
                    result = load_filter_content()
                    assert result == filter_text

    def test_load_filter_priority_content_over_file(self):
        """Test that FILTER_CONTENT has priority over FILTER_PATH"""
        content = "Content from env"
        path = "./test.txt"
        
        with patch("llm_service.config") as mock_config:
            mock_config.FILTER_CONTENT = content
            mock_config.FILTER_PATH = path
            
            from llm_service import load_filter_content
            result = load_filter_content()
            assert result == content

    def test_load_filter_file_not_found(self):
        """Test error when filter file doesn't exist"""
        with patch("llm_service.config") as mock_config:
            mock_config.FILTER_CONTENT = None
            mock_config.FILTER_PATH = "./nonexistent.txt"
            
            with patch("os.path.exists", return_value=False):
                from llm_service import load_filter_content
                with pytest.raises(FileNotFoundError, match="Filter file not found"):
                    load_filter_content()

    def test_load_filter_no_config(self):
        """Test error when no filter is configured"""
        with patch("llm_service.config") as mock_config:
            mock_config.FILTER_CONTENT = None
            mock_config.FILTER_PATH = None
            
            from llm_service import load_filter_content
            with pytest.raises(ValueError, match="Filter not configured"):
                load_filter_content()
