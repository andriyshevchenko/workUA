"""Service for LLM-based job analysis"""

import json
import logging
import os
import re
from typing import Optional, Tuple
from openai import AsyncOpenAI
from config import config


def resolve_filter_path() -> str:
    """Resolve filter path with fallback to bundled filter

    Returns:
        Path to filter file (configured or fallback)
    """
    filter_path = getattr(config, "FILTER_PATH", "./my_filter.txt")
    if not os.path.exists(filter_path):
        fallback_path = "filter_example.txt"
        if os.path.exists(fallback_path):
            logging.getLogger(__name__).warning(
                "Configured filter path '%s' not found, using bundled '%s'",
                filter_path,
                fallback_path,
            )
            return fallback_path
        else:
            logging.getLogger(__name__).warning(
                "Neither configured filter path '%s' nor fallback '%s' exist",
                filter_path,
                fallback_path,
            )
    return filter_path


class LLMAnalysisService:
    """Service for analyzing job listings using LLM"""

    def __init__(self):
        """Initialize the LLM analysis service"""
        self.logger = logging.getLogger(__name__)
        self.client: Optional[AsyncOpenAI] = None
        self.use_llm = False
        self.filter_text = ""

        # Initialize client if any LLM feature is enabled
        llm_enabled = (hasattr(config, "USE_LLM") and config.USE_LLM) or (
            hasattr(config, "USE_PRE_APPLY_LLM_CHECK") and config.USE_PRE_APPLY_LLM_CHECK
        )

        if config.OPENAI_API_KEY and llm_enabled:
            try:
                self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
                self.use_llm = True
                self.logger.info("✅ LLM analysis enabled (GPT-4o)")
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to initialize OpenAI: {e}")
                self.use_llm = False
        else:
            self.logger.info("ℹ️ LLM analysis disabled - brute force mode")

    def load_filter(self, filter_path: str) -> str:
        """Load user filter from file

        Args:
            filter_path: Path to filter file

        Returns:
            Filter text content or fallback text
        """
        try:
            with open(filter_path, "r", encoding="utf-8") as f:
                filter_text = f.read()
            self.filter_text = filter_text
            return filter_text
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to load filter: {e}")
            # Fallback to default filter in Ukrainian
            fallback_filter = """
            Я шукаю вакансії 'менеджер з продажу' або 'sales manager'.
            Мінімальна зарплата: 25000 гривень.
            Вакансії від ФОП чи без верифікації work.ua - не влаштовують.
            Сумнівні фірми які займаються езотерикою чи торгують сумнівними товарами - не влаштовують.
            """
            self.filter_text = fallback_filter
            return fallback_filter

    async def analyze_job(
        self,
        job_title: str,
        company: str,
        location: str,
        salary: Optional[str],
        description: str,
    ) -> Tuple[bool, int, str]:
        """Analyze if a job matches the user's filter criteria

        Args:
            job_title: Job title
            company: Company name
            location: Job location
            salary: Salary information
            description: Job description

        Returns:
            Tuple of (should_apply, score, reason)
        """
        if not self.use_llm:
            # Brute force - all jobs are suitable
            return True, 10, "Brute force mode - applying to all"

        try:
            prompt = self._build_analysis_prompt(job_title, company, location, salary, description)

            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an HR analyst. Respond in JSON format.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            score = result.get("score", 0)
            reason = result.get("reason", "")

            # Threshold for applying (can be in config)
            min_score = getattr(config, "MIN_SCORE", 7)
            should_apply = score >= min_score

            return should_apply, score, reason

        except Exception as e:
            self.logger.error(f"❌ LLM analysis error: {e}")
            # If LLM fails - skip the job
            return False, 0, f"Analysis error: {e}"

    def _build_analysis_prompt(
        self,
        job_title: str,
        company: str,
        location: str,
        salary: Optional[str],
        description: str,
    ) -> str:
        """Build the analysis prompt for LLM

        Args:
            job_title: Job title
            company: Company name
            location: Job location
            salary: Salary information
            description: Job description

        Returns:
            Formatted prompt string
        """
        return f"""You are an HR assistant. Analyze this job posting.

JOB POSTING:
Title: {job_title}
Company: {company}
Location: {location}
Salary: {salary or 'Not specified'}
Description: {description[:1000] if description else 'No description'}

TASK:
1. Rate the overall quality and clarity from 1 to 10 (10 = excellent job posting)
2. Explain why

RESPONSE FORMAT (JSON):
{{
  "score": 8,
  "reason": "Brief explanation (1-2 sentences)"
}}
"""

    async def analyze_job_match(self, job_description: str) -> Tuple[int, str]:
        """Analyze job match probability with LLM based on user filter

        Args:
            job_description: Full job description text

        Returns:
            Tuple of (probability 0-100%, explanation)
        """
        if not self.use_llm or not self.client:
            return 50, "LLM analysis not available"

        try:
            prompt = f"""Проаналізуй цю вакансію та оціни її якість та привабливість.

ОПИС ВАКАНСІЇ:
{job_description}

Дай відповідь у форматі:
PROBABILITY: [число від 0 до 100]%
EXPLANATION: [коротке пояснення чому така ймовірність]

Врахуй:
- Чіткість опису позиції та обов'язків
- Чи вказана зарплата та чи вона конкурентна
- Репутація та надійність компанії (верифікація, тип компанії)
- Загальна привабливість пропозиції
- Якість та повнота опису вакансії
"""

            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Ти - експерт з аналізу вакансій. Відповідай українською мовою.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )

            result = response.choices[0].message.content

            # Parse the response
            probability_match = re.search(r"PROBABILITY:\s*(\d+)", result)
            explanation_match = re.search(r"EXPLANATION:\s*(.+)", result, re.DOTALL)

            if probability_match:
                probability = int(probability_match.group(1))
                explanation = explanation_match.group(1).strip() if explanation_match else result
                return probability, explanation
            else:
                # If parsing failed, return default values
                return 50, result

        except Exception as e:
            self.logger.error(f"⚠️ LLM analysis error: {e}")
            return 50, f"Analysis error: {e}"
