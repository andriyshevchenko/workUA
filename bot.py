"""Простий бот для автоматичного відгуку на вакансії Work.ua"""
import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from openai import OpenAI
from scraper import WorkUAScraper, JobListing
from config import config


# Налаштування логування
def setup_logging():
    """Налаштувати логування в консоль та файл"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"workua_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Формат логів
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Консольний handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Файловий handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Налаштування root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


class WorkUABot:
    """Бот для автоматичного відгуку на вакансії"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.scraper = None
        self.client = None
        self.use_llm = config.OPENAI_API_KEY and hasattr(config, 'USE_LLM') and config.USE_LLM
        self.resume_text = self._load_resume()
        
        if self.use_llm:
            try:
                self.client = OpenAI(api_key=config.OPENAI_API_KEY)
                self.logger.info("✅ LLM аналіз увімкнено (GPT-4o)")
            except Exception as e:
                self.logger.warning(f"⚠️ Не вдалось ініціалізувати OpenAI: {e}")
                self.use_llm = False
        else:
            self.logger.info("ℹ️ LLM аналіз вимкнено - брут форс режим")
    
    def _load_resume(self) -> str:
        """Завантажити резюме користувача"""
        resume_path = "resume_Osipov_Ernest.txt"
        try:
            with open(resume_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.warning(f"⚠️ Не вдалось завантажити резюме: {e}")
            # Fallback до короткого опису
            return """
            Менеджер з продажу з досвідом роботи в B2B-сегменті.
            
            Досвід:
            - Активні продажі в B2B (IT-рішення, SaaS)
            - Робота з холодними контактами та теплими заявками
            - СПІН продажів, робота з запереченнями
            - CRM, Binotel, Bitrix24
            
            Шукаю: Менеджер з продажу позиції
            Локація: Дистанційно
            """
    
    def analyze_job(self, job: JobListing) -> tuple[bool, int, str]:
        """
        Проаналізувати вакансію
        
        Returns:
            (should_apply, score, reason)
        """
        if not self.use_llm:
            # Брут форс - всі вакансії підходять
            return True, 10, "Брут форс режим - відгукуємось на всі"
        
        try:
            prompt = f"""Ти HR асистент. Проаналізуй чи підходить ця вакансія кандидату.

РЕЗЮМЕ КАНДИДАТА:
{self.resume_text}

ВАКАНСІЯ:
Назва: {job.title}
Компанія: {job.company}
Локація: {job.location}
Зарплата: {job.salary or 'Не вказано'}
Опис: {job.description[:1000] if job.description else 'Немає опису'}

ЗАВДАННЯ:
1. Оціни відповідність від 1 до 10 (10 = ідеально підходить)
2. Поясни чому

ФОРМАТ ВІДПОВІДІ (JSON):
{{
  "score": 8,
  "reason": "Коротке пояснення (1-2 речення)"
}}
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Ти HR аналітик. Відповідай JSON форматі."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            score = result.get("score", 0)
            reason = result.get("reason", "")
            
            # Поріг для відгуку (можна в config)
            min_score = getattr(config, 'MIN_SCORE', 7)
            should_apply = score >= min_score
            
            return should_apply, score, reason
            
        except Exception as e:
            self.logger.error(f"❌ Помилка LLM аналізу: {e}")
            # Якщо LLM не працює - пропускаємо
            return False, 0, f"Помилка аналізу: {e}"
    
    async def run(self, max_applications: int = 10):
        """Запустити бот"""
        self.logger.info("="*70)
        self.logger.info("🤖 WORK.UA BOT - Автоматичний пошук роботи")
        self.logger.info("="*70)
        
        # Ініціалізація
        self.scraper = WorkUAScraper()
        await self.scraper.start(headless=config.HEADLESS)
        
        # Якщо auto_login виконався в start(), то is_logged_in вже True
        if not self.scraper.is_logged_in:
            # Перевірка авторизації тільки якщо auto_login не виконувався
            is_logged_in = await self.scraper.check_login_status()
            if not is_logged_in:
                self.logger.error("❌ Не авторизовано! Додайте WORKUA_PHONE в .env")
                await self.scraper.close()
                return
        
        self.logger.info("✅ Авторізація успішна")
        
        # Налаштування пошуку
        keywords = config.SEARCH_KEYWORDS
        remote_only = config.REMOTE_ONLY
        locations = config.LOCATIONS if not remote_only else []
        
        self.logger.info(f"🔍 Ключові слова ({len(keywords)}): {', '.join(keywords)}")
        if remote_only:
            self.logger.info("🌍 Режим: Тільки дистанційна робота")
        else:
            self.logger.info(f"📍 Локації: {', '.join(locations)}")
        self.logger.info(f"🎯 Мета: {max_applications} відгуків")
        self.logger.info("="*70)
        
        # Лічильники
        total_scanned = 0
        total_applied = 0
        total_skipped = 0
        max_vacancies = config.MAX_VACANCIES
        
        # Максимум сторінок для сканування
        max_pages_to_scan = 50  # Work.ua підтримує просто ?page=N
        
        try:
            # Об'єднуємо всі ключові слова в один запит
            combined_keyword = ' '.join(keywords)
            self.logger.info(f"🔎 Ключові слова об'єднано: '{combined_keyword}'")
            self.logger.info(f"📊 Мета: {max_applications} відгуків")
            self.logger.info(f"📄 Сканування до {max_pages_to_scan} сторінок")
            self.logger.info(f"{'='*70}")
            
            # Цільова кількість вакансій (x2 тільки якщо LLM фільтр увімкнено)
            if config.USE_PRE_APPLY_LLM_CHECK:
                target_jobs = max_applications * 2
                self.logger.info(f"🎯 Ціль сканування: {target_jobs} вакансій (x2 від мети, бо LLM фільтр увімкнено)")
            else:
                target_jobs = max_applications
                self.logger.info(f"🎯 Ціль сканування: {target_jobs} вакансій (LLM вимкнено, збираємо точну кількість)")
            
            # Отримати всі вакансії (scraper сам пройде по сторінках)
            if remote_only:
                jobs = await self.scraper.search_jobs(
                    keyword=combined_keyword,
                    remote=True,
                    max_pages=max_pages_to_scan,
                    target_jobs=target_jobs
                )
            else:
                all_jobs = []
                for location in locations:
                    jobs_in_loc = await self.scraper.search_jobs(
                        keyword=combined_keyword,
                        location=location,
                        max_pages=max_pages_to_scan,
                        target_jobs=target_jobs
                    )
                    all_jobs.extend(jobs_in_loc)
                jobs = all_jobs
            
            if not jobs:
                self.logger.warning("⚠️ Вакансій не знайдено")
            else:
                self.logger.info(f"📋 Знайдено {len(jobs)} вакансій загалом")
            
            # Обробка кожної вакансії
            for idx, job in enumerate(jobs, 1):
                if total_applied >= max_applications:
                    self.logger.info(f"🎯 Досягнуто мету: {total_applied}/{max_applications} відгуків")
                    break
                
                if total_scanned >= max_vacancies:
                    self.logger.warning(f"⚠️ Досягнуто ліміт перегляду: {max_vacancies} вакансій")
                    break
                
                total_scanned += 1
                self.logger.info(f"\n--- Вакансія {idx}/{len(jobs)} (Всього оброблено: {total_scanned}) ---")
                self.logger.info(f"📌 {job.title}")
                self.logger.info(f"🏢 {job.company}")
                self.logger.info(f"📍 {job.location}")
                if job.salary:
                    self.logger.info(f"💰 {job.salary}")
                
                # Аналіз через LLM (якщо увімкнено) - без деталей, бо відгукуємось одразу
                should_apply, score, reason = self.analyze_job(job)
                
                if self.use_llm:
                    self.logger.info(f"🤖 LLM оцінка: {score}/10")
                    self.logger.info(f"💭 Причина: {reason}")
                
                if should_apply:
                    # Спроба відгукнутись
                    try:
                        success = await self.scraper.apply_to_job(job)
                        if success:
                            total_applied += 1
                            self.logger.info(f"✅ Відгукнулись! ({total_applied}/{max_applications})")
                        else:
                            total_skipped += 1
                            self.logger.warning("⚠️ Не вдалось відгукнутись")
                        
                        # Пауза між відгуками
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        self.logger.error(f"❌ Помилка відгуку: {e}")
                        total_skipped += 1
                else:
                    total_skipped += 1
                    self.logger.info(f"⏭️ Пропускаємо (оцінка {score} < мінімум)")
        
        except Exception as e:
            self.logger.error(f"❌ Критична помилка: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        
        finally:
            # Фінальна статистика
            self.logger.info("\n" + "="*70)
            self.logger.info("📊 ПІДСУМКИ")
            self.logger.info("="*70)
            self.logger.info(f"🔍 Всього переглянуто: {total_scanned}")
            self.logger.info(f"✅ Відгукнулись: {total_applied}")
            self.logger.info(f"⏭️ Пропущено: {total_skipped}")
            self.logger.info("="*70)
            
            await self.scraper.close()
            self.logger.info("👋 Завершено!")


async def main():
    """Головна функція"""
    setup_logging()
    
    # Кількість відгуків (можна з config)
    max_apps = getattr(config, 'MAX_APPLICATIONS', 10)
    
    bot = WorkUABot()
    await bot.run(max_applications=max_apps)


if __name__ == "__main__":
    asyncio.run(main())
