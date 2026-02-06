"""Простий бот для автоматичного відгуку на вакансії Work.ua"""

import asyncio
import logging
from typing import List, Tuple

from scraper import WorkUAScraper, JobListing
from config import config
from logging_config import setup_logging
from llm_service import LLMAnalysisService


class WorkUABot:
    """Бот для автоматичного відгуку на вакансії"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.scraper = None
        self.llm_service = LLMAnalysisService()

        # Load filter only if LLM features are enabled
        if self.llm_service.use_llm:
            self.llm_service.load_filter()

    async def analyze_job(self, job: JobListing) -> Tuple[bool, int, str]:
        """Проаналізувати вакансію

        Returns:
            (should_apply, score, reason)
        """
        return self.llm_service.analyze_job(
            job.title, job.company, job.location, job.salary, job.description
        )

    async def run(self, max_applications: int = 10):
        """Запустити бот"""
        self._log_header()

        # Initialize scraper
        self.scraper = WorkUAScraper()
        await self.scraper.start(headless=config.HEADLESS)

        # Check authorization
        if not await self._check_authorization():
            return

        # Get search configuration
        search_config = self._get_search_config(max_applications)
        self._log_search_config(search_config)

        # Initialize counters
        stats = {"scanned": 0, "applied": 0, "skipped": 0}

        try:
            # Get all jobs
            jobs = await self._search_jobs(search_config)

            if not jobs:
                self.logger.warning("⚠️ Вакансій не знайдено")
                return

            self.logger.info(f"📋 Знайдено {len(jobs)} вакансій загалом")

            # Process each job
            await self._process_jobs(jobs, max_applications, search_config["max_vacancies"], stats)

        except Exception as e:
            self.logger.error(f"❌ Критична помилка: {e}")
            import traceback

            self.logger.error(traceback.format_exc())

        finally:
            self._log_final_stats(stats)
            await self.scraper.close()
            self.logger.info("👋 Завершено!")

    def _log_header(self):
        """Log the bot header"""
        self.logger.info("=" * 70)
        self.logger.info("🤖 WORK.UA BOT - Автоматичний пошук роботи")
        self.logger.info("=" * 70)

    async def _check_authorization(self) -> bool:
        """Check if user is authorized

        Returns:
            True if authorized, False otherwise
        """
        if not self.scraper.is_logged_in:
            is_logged_in = await self.scraper.check_login_status()
            if not is_logged_in:
                self.logger.error("❌ Не авторизовано! Додайте WORKUA_PHONE в .env")
                # Don't close here - let run() handle cleanup in finally block
                return False

        self.logger.info("✅ Авторізація успішна")
        return True

    def _get_search_config(self, max_applications: int) -> dict:
        """Get search configuration

        Args:
            max_applications: Maximum number of applications

        Returns:
            Dictionary with search configuration
        """
        return {
            "keywords": config.SEARCH_KEYWORDS,
            "remote_only": config.REMOTE_ONLY,
            "locations": config.LOCATIONS if not config.REMOTE_ONLY else [],
            "max_applications": max_applications,
            "max_vacancies": config.MAX_VACANCIES,
            "max_pages": 50,
            "target_jobs": max_applications * config.VACANCY_MULTIPLIER,
        }

    def _log_search_config(self, search_config: dict):
        """Log search configuration

        Args:
            search_config: Search configuration dictionary
        """
        keywords = search_config["keywords"]
        remote_only = search_config["remote_only"]
        locations = search_config["locations"]
        max_applications = search_config["max_applications"]

        self.logger.info(f"🔍 Ключові слова ({len(keywords)}): {', '.join(keywords)}")
        if remote_only:
            self.logger.info("🌍 Режим: Тільки дистанційна робота")
        else:
            self.logger.info(f"📍 Локації: {', '.join(locations)}")
        self.logger.info(f"🎯 Мета: {max_applications} відгуків")
        self.logger.info("=" * 70)

    async def _search_jobs(self, search_config: dict) -> List[JobListing]:
        """Search for jobs based on configuration

        Args:
            search_config: Search configuration dictionary

        Returns:
            List of job listings
        """
        combined_keyword = " ".join(search_config["keywords"])
        self.logger.info(f"🔎 Ключові слова об'єднано: '{combined_keyword}'")
        self.logger.info(f"📊 Мета: {search_config['max_applications']} відгуків")
        self.logger.info(f"📄 Сканування до {search_config['max_pages']} сторінок")
        self.logger.info(f"{'='*70}")

        target_jobs = search_config["target_jobs"]
        self.logger.info(
            f"🎯 Ціль сканування: {target_jobs} вакансій (x{config.VACANCY_MULTIPLIER} від мети для запасу)"
        )

        if search_config["remote_only"]:
            return await self.scraper.search_jobs(
                keyword=combined_keyword,
                remote=True,
                max_pages=search_config["max_pages"],
                target_jobs=target_jobs,
            )
        else:
            all_jobs = []
            for location in search_config["locations"]:
                jobs_in_loc = await self.scraper.search_jobs(
                    keyword=combined_keyword,
                    location=location,
                    max_pages=search_config["max_pages"],
                    target_jobs=target_jobs,
                )
                all_jobs.extend(jobs_in_loc)
            return all_jobs

    async def _process_jobs(
        self, jobs: List[JobListing], max_applications: int, max_vacancies: int, stats: dict
    ):
        """Process job listings

        Args:
            jobs: List of job listings
            max_applications: Maximum number of applications
            max_vacancies: Maximum number of vacancies to scan
            stats: Statistics dictionary to update
        """
        for idx, job in enumerate(jobs, 1):
            if stats["applied"] >= max_applications:
                self.logger.info(
                    f"🎯 Досягнуто мету: {stats['applied']}/{max_applications} відгуків"
                )
                break

            if stats["scanned"] >= max_vacancies:
                self.logger.warning(f"⚠️ Досягнуто ліміт перегляду: {max_vacancies} вакансій")
                break

            stats["scanned"] += 1
            self._log_job_info(idx, len(jobs), stats["scanned"], job)

            # Analyze job
            should_apply, score, reason = await self.analyze_job(job)

            if self.llm_service.use_llm:
                self.logger.info(f"🤖 LLM оцінка: {score}/10")
                self.logger.info(f"💭 Причина: {reason}")

            if should_apply:
                await self._apply_to_job(job, stats, max_applications)
            else:
                stats["skipped"] += 1
                self.logger.info(f"⏭️ Пропускаємо (оцінка {score} < мінімум)")

    def _log_job_info(self, idx: int, total: int, scanned: int, job: JobListing):
        """Log job information

        Args:
            idx: Current job index
            total: Total number of jobs
            scanned: Number of jobs scanned
            job: Job listing
        """
        self.logger.info("")
        self.logger.info(f"--- Вакансія {idx}/{total} (Всього оброблено: {scanned}) ---")
        self.logger.info(f"📌 {job.title}")
        self.logger.info(f"🏢 {job.company if job.company else '(не вказано)'}")
        self.logger.info(f"📍 {job.location if job.location else '(не вказано)'}")
        if job.salary:
            self.logger.info(f"💰 {job.salary}")

    async def _apply_to_job(self, job: JobListing, stats: dict, max_applications: int):
        """Apply to a job

        Args:
            job: Job listing
            stats: Statistics dictionary to update
            max_applications: Maximum number of applications
        """
        try:
            success = await self.scraper.apply_to_job(job)
            if success:
                stats["applied"] += 1
                self.logger.info(f"✅ Відгукнулись! ({stats['applied']}/{max_applications})")
            else:
                stats["skipped"] += 1
                self.logger.warning("⚠️ Не вдалось відгукнутись")

            # Pause between applications
            await asyncio.sleep(2)

        except Exception as e:
            self.logger.error(f"❌ Помилка відгуку: {e}")
            stats["skipped"] += 1

    def _log_final_stats(self, stats: dict):
        """Log final statistics

        Args:
            stats: Statistics dictionary
        """
        self.logger.info("\n" + "=" * 70)
        self.logger.info("📊 ПІДСУМКИ")
        self.logger.info("=" * 70)
        self.logger.info(f"🔍 Всього переглянуто: {stats['scanned']}")
        self.logger.info(f"✅ Відгукнулись: {stats['applied']}")
        self.logger.info(f"⏭️ Пропущено: {stats['skipped']}")
        self.logger.info("=" * 70)


async def main():
    """Головна функція"""
    # Validate configuration at startup to fail fast
    config.validate()

    setup_logging()

    # Кількість відгуків (можна з config)
    max_apps = getattr(config, "MAX_APPLICATIONS", 10)

    bot = WorkUABot()
    await bot.run(max_applications=max_apps)


if __name__ == "__main__":
    asyncio.run(main())
