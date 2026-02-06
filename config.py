"""Конфігурація для AI агента Work.ua"""

import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class Config:
    """Налаштування додатку"""

    # API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    # Work.ua credentials
    WORKUA_PHONE: Optional[str] = os.getenv("WORKUA_PHONE")
    WORKUA_COOKIES: Optional[str] = os.getenv("WORKUA_COOKIES")

    # Налаштування пошуку
    FILTER_PATH: Optional[str] = os.getenv("FILTER_PATH")
    FILTER_CONTENT: Optional[str] = os.getenv("FILTER_CONTENT")
    SEARCH_KEYWORDS: list[str] = [
        kw.strip()
        for kw in os.getenv("SEARCH_KEYWORDS", "").split(",")
        if kw.strip()
    ]
    LOCATIONS: list[str] = [
        loc.strip() for loc in os.getenv("LOCATIONS", "").split(",") if loc.strip()
    ]
    REMOTE_ONLY: bool = os.getenv("REMOTE_ONLY", "false").lower() == "true"
    MIN_SALARY: int = int(
        os.getenv("MIN_SALARY", "0")
    )  # 0=без фільтра, 2=10k, 3=15k, 4=20k, 5=30k, 6=40k, 7=50k, 8=100k

    # Налаштування бота
    MAX_APPLICATIONS: int = int(os.getenv("MAX_APPLICATIONS", "10"))
    MAX_VACANCIES: int = int(
        os.getenv("MAX_VACANCIES", "500")
    )  # Максимум вакансій для сканування (щоб набрати потрібну кількість відгуків)
    VACANCY_MULTIPLIER: int = int(
        os.getenv("VACANCY_MULTIPLIER", "10")
    )  # Множник для збору вакансій (x10 = збираємо в 10 разів більше для запасу)
    USE_LLM: bool = os.getenv("USE_LLM", "false").lower() == "true"
    MIN_SCORE: int = int(os.getenv("MIN_SCORE", "7"))
    REAPPLY_AFTER_MONTHS: int = int(
        os.getenv("REAPPLY_AFTER_MONTHS", "2")
    )  # Через скільки місяців можна відправити резюме повторно

    # LLM перевірка перед відгуком
    USE_PRE_APPLY_LLM_CHECK: bool = os.getenv("USE_PRE_APPLY_LLM_CHECK", "false").lower() == "true"
    MIN_MATCH_PROBABILITY: int = int(
        os.getenv("MIN_MATCH_PROBABILITY", "90")
    )  # Мінімальна ймовірність (%) для відгуку

    # Playwright налаштування
    HEADLESS: bool = os.getenv("HEADLESS", "false").lower() == "true"
    BROWSER_TYPE: str = os.getenv("BROWSER_TYPE", "chromium")

    # URL
    WORKUA_BASE_URL: str = "https://www.work.ua"
    WORKUA_LOGIN_URL: str = "https://www.work.ua/ua/login/"
    WORKUA_SEARCH_URL: str = "https://www.work.ua/jobs/"

    # LLM налаштування
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o")
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.3"))

    @classmethod
    def validate(cls) -> bool:
        """Перевірити чи є необхідні налаштування"""
        errors = []

        # Check required fields
        if not cls.WORKUA_PHONE and not cls.WORKUA_COOKIES:
            errors.append("WORKUA_PHONE or WORKUA_COOKIES is required")

        if not cls.SEARCH_KEYWORDS:
            errors.append("SEARCH_KEYWORDS is required")

        # Check LLM-specific requirements
        llm_enabled = cls.USE_LLM or cls.USE_PRE_APPLY_LLM_CHECK
        if llm_enabled:
            if not cls.OPENAI_API_KEY:
                errors.append("OPENAI_API_KEY is required when USE_LLM or USE_PRE_APPLY_LLM_CHECK is enabled")
            if not cls.FILTER_PATH and not cls.FILTER_CONTENT:
                errors.append("FILTER_PATH or FILTER_CONTENT is required when USE_LLM or USE_PRE_APPLY_LLM_CHECK is enabled")

        if errors:
            raise ValueError("Configuration errors:\n  - " + "\n  - ".join(errors))

        return True


config = Config()
