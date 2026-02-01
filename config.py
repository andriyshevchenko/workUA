"""Конфігурація для AI агента Work.ua"""
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Config:
    """Налаштування додатку"""
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    
    # Work.ua credentials
    WORKUA_PHONE: Optional[str] = os.getenv("WORKUA_PHONE")
    
    # Налаштування пошуку
    RESUME_PATH: str = os.getenv("RESUME_PATH", "./my_resume.pdf")
    SEARCH_KEYWORDS: list[str] = os.getenv("SEARCH_KEYWORDS", "python developer").split(",")
    LOCATIONS: list[str] = os.getenv("LOCATIONS", "Київ").split(",")
    REMOTE_ONLY: bool = os.getenv("REMOTE_ONLY", "false").lower() == "true"
    MIN_SALARY: int = int(os.getenv("MIN_SALARY", "0"))  # 0=без фільтра, 2=10k, 3=15k, 4=20k, 5=30k, 6=40k, 7=50k, 8=100k
    
    # Налаштування бота
    MAX_APPLICATIONS: int = int(os.getenv("MAX_APPLICATIONS", "10"))
    MAX_VACANCIES: int = int(os.getenv("MAX_VACANCIES", "500"))  # Максимум вакансій для сканування (щоб набрати потрібну кількість відгуків)
    USE_LLM: bool = os.getenv("USE_LLM", "false").lower() == "true"
    MIN_SCORE: int = int(os.getenv("MIN_SCORE", "7"))
    
    # LLM перевірка перед відгуком
    USE_PRE_APPLY_LLM_CHECK: bool = os.getenv("USE_PRE_APPLY_LLM_CHECK", "false").lower() == "true"
    MIN_MATCH_PROBABILITY: int = int(os.getenv("MIN_MATCH_PROBABILITY", "10"))  # Мінімальна ймовірність (%) для відгуку
    
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
        if not cls.OPENAI_API_KEY:
            raise ValueError("Потрібен OPENAI_API_KEY в .env файлі")
        return True

config = Config()
