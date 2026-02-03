"""Unit tests for llm_service module"""

from unittest.mock import Mock, patch
from llm_service import LLMAnalysisService


class TestLLMAnalysisService:
    """Test cases for LLMAnalysisService class"""

    def test_initialization_without_api_key(self):
        """Test service initialization without API key"""
        with patch("llm_service.config.OPENAI_API_KEY", None):
            service = LLMAnalysisService()

            assert service.use_llm is False
            assert service.client is None

    def test_initialization_with_api_key(self):
        """Test service initialization with API key"""
        with patch("llm_service.config.OPENAI_API_KEY", "test-key"):
            with patch("llm_service.config.USE_LLM", True):
                with patch("llm_service.OpenAI") as mock_openai:
                    service = LLMAnalysisService()

                    assert service.use_llm is True
                    mock_openai.assert_called_once_with(api_key="test-key")

    def test_load_resume_success(self, tmp_path):
        """Test loading resume from file successfully"""
        service = LLMAnalysisService()

        # Create a temporary resume file
        resume_file = tmp_path / "test_resume.txt"
        resume_content = "Test Resume Content\nPython Developer"
        resume_file.write_text(resume_content, encoding="utf-8")

        result = service.load_resume(str(resume_file))

        assert result == resume_content
        assert service.resume_text == resume_content

    def test_load_resume_file_not_found(self):
        """Test loading resume when file doesn't exist"""
        service = LLMAnalysisService()

        result = service.load_resume("nonexistent_file.txt")

        # Should return fallback resume
        assert "Sales Manager" in result or "B2B" in result
        assert service.resume_text != ""

    def test_analyze_job_brute_force_mode(self):
        """Test job analysis in brute force mode (no LLM)"""
        service = LLMAnalysisService()
        service.use_llm = False

        should_apply, score, reason = service.analyze_job(
            "Python Developer", "Tech Corp", "Kyiv", "$50k", "We need a Python developer"
        )

        assert should_apply is True
        assert score == 10
        assert "brute force" in reason.lower()

    def test_analyze_job_with_llm_success(self):
        """Test job analysis with LLM when successful"""
        service = LLMAnalysisService()
        service.use_llm = True
        service.resume_text = "Python Developer with 5 years experience"

        # Mock the OpenAI client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"score": 8, "reason": "Good match"}'))]
        mock_client.chat.completions.create.return_value = mock_response
        service.client = mock_client

        with patch("llm_service.config.MIN_SCORE", 7):
            should_apply, score, reason = service.analyze_job(
                "Python Developer", "Tech Corp", "Kyiv", "$50k", "We need a Python developer"
            )

        assert should_apply is True
        assert score == 8
        assert reason == "Good match"

    def test_analyze_job_with_llm_low_score(self):
        """Test job analysis with LLM when score is too low"""
        service = LLMAnalysisService()
        service.use_llm = True
        service.resume_text = "Python Developer"

        # Mock the OpenAI client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"score": 3, "reason": "Poor match"}'))]
        mock_client.chat.completions.create.return_value = mock_response
        service.client = mock_client

        with patch("llm_service.config.MIN_SCORE", 7):
            should_apply, score, reason = service.analyze_job(
                "Senior Java Architect",
                "Enterprise Corp",
                "London",
                "$200k",
                "We need 15 years of Java experience",
            )

        assert should_apply is False
        assert score == 3

    def test_analyze_job_with_llm_error(self):
        """Test job analysis when LLM throws an error"""
        service = LLMAnalysisService()
        service.use_llm = True

        # Mock the OpenAI client to raise an exception
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        service.client = mock_client

        should_apply, score, reason = service.analyze_job(
            "Python Developer", "Tech Corp", "Kyiv", "$50k", "We need a Python developer"
        )

        assert should_apply is False
        assert score == 0
        assert "error" in reason.lower()

    def test_build_analysis_prompt(self):
        """Test building the analysis prompt"""
        service = LLMAnalysisService()
        service.resume_text = "Test Resume"

        prompt = service._build_analysis_prompt(
            "Python Developer", "Tech Corp", "Kyiv", "$50k", "Job description here"
        )

        assert "Test Resume" in prompt
        assert "Python Developer" in prompt
        assert "Tech Corp" in prompt
        assert "Kyiv" in prompt
        assert "$50k" in prompt

    def test_analyze_job_match_without_llm(self):
        """Test analyze_job_match when LLM is not available"""
        service = LLMAnalysisService()
        service.use_llm = False

        probability, explanation = service.analyze_job_match("Job description")

        assert probability == 50
        assert "not available" in explanation.lower()

    def test_analyze_job_match_with_llm_success(self):
        """Test analyze_job_match with successful LLM response"""
        service = LLMAnalysisService()
        service.use_llm = True
        service.resume_text = "Test Resume"

        # Mock the OpenAI client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="PROBABILITY: 75%\nEXPLANATION: Good skills match"))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        service.client = mock_client

        probability, explanation = service.analyze_job_match("Job description")

        assert probability == 75
        assert "Good skills match" in explanation
