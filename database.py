"""База даних для відстеження вакансій на які вже відгукувались"""

import csv
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path
import logging
from config import config


class VacancyDatabase:
    """Base class for vacancy database - factory pattern"""
    
    @staticmethod
    def create(db_type: Optional[str] = None):
        """Factory method to create appropriate database instance
        
        Args:
            db_type: Type of database ('csv', 'supabase', or None for auto-detect)
            
        Returns:
            Database instance (CSVVacancyDatabase or SupabaseVacancyDatabase)
            
        Raises:
            ValueError: If db_type is invalid
        """
        # Auto-detect based on environment variables
        if db_type is None:
            if config.SUPABASE_URL and config.SUPABASE_KEY:
                db_type = 'supabase'
            else:
                db_type = 'csv'
        
        if db_type == 'supabase':
            return SupabaseVacancyDatabase()
        elif db_type == 'csv':
            return CSVVacancyDatabase()
        else:
            raise ValueError(
                f"Unsupported db_type: {db_type!r}. Allowed values are 'csv', 'supabase', or None."
            )
    
    @staticmethod
    def calculate_months_between(from_date: datetime, to_date: datetime) -> int:
        """Calculate the number of months between two dates

        Args:
            from_date: Earlier date
            to_date: Later date

        Returns:
            Number of months between the two dates
        """
        return (to_date.year - from_date.year) * 12 + (to_date.month - from_date.month)


class CSVVacancyDatabase(VacancyDatabase):
    """CSV-based vacancy database (original implementation)"""

    def __init__(self, db_path: str = "applied_jobs.csv"):
        self.db_path = Path(db_path)
        self.fieldnames = ["url", "date_applied", "title", "company"]
        self.logger = logging.getLogger(__name__)
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Створити файл БД якщо не існує"""
        if not self.db_path.exists():
            self.logger.debug(f"📂 Створюю нову БД: {self.db_path}")
            with open(self.db_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
        else:
            self.logger.debug(f"✓ БД існує: {self.db_path}")

    def get_application(self, url: str) -> Optional[Dict[str, str]]:
        """Отримати запис про відгук за URL"""
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["url"] == url:
                        self.logger.debug(
                            f"🔍 Знайдено в БД: {row['date_applied']} - {row['title']}"
                        )
                        return row
            self.logger.debug("🔍 Не знайдено в БД")
        except Exception as e:
            self.logger.debug(f"⚠️ Помилка читання БД: {e}")
        return None

    def add_or_update(self, url: str, date_applied: str, title: str = "", company: str = ""):
        """Додати або оновити запис про відгук"""
        # Читаємо всі записи
        rows = []
        existing = False

        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["url"] == url:
                        # Оновлюємо існуючий запис
                        old_date = row["date_applied"]
                        row["date_applied"] = date_applied
                        if title:
                            row["title"] = title
                        if company:
                            row["company"] = company
                        existing = True
                        self.logger.debug(f"♻️ Оновлено: {old_date} → {date_applied}")
                    rows.append(row)
        except Exception as e:
            self.logger.debug(f"⚠️ Помилка читання для update: {e}")

        # Якщо не знайшли - додаємо новий
        if not existing:
            rows.append(
                {"url": url, "date_applied": date_applied, "title": title, "company": company}
            )
            self.logger.debug(f"➕ Новий запис: {date_applied} - {title}")

        # Записуємо назад
        try:
            with open(self.db_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            self.logger.debug(f"💾 БД збережено ({len(rows)} записів)")
        except Exception as e:
            self.logger.error(f"❌ Помилка запису БД: {e}")

    def should_reapply(self, url: str, months_threshold: int) -> bool:
        """
        Перевірити чи можна повторно відгукнутись

        Returns:
            True - якщо можна відгукуватись (немає в БД або пройшло достатньо часу)
            False - якщо не можна (є в БД і не пройшло достатньо часу)
        """
        record = self.get_application(url)
        if not record:
            self.logger.debug("✓ Немає в БД - можна відгукуватись")
            return True  # Немає в БД - можна відгукуватись

        try:
            # Парсимо дату
            date_applied = datetime.strptime(record["date_applied"], "%Y-%m-%d")
            now = datetime.now()
            months_passed = self.calculate_months_between(date_applied, now)

            can_apply = months_passed >= months_threshold
            if can_apply:
                self.logger.debug(f"✓ Минуло {months_passed} міс. >= {months_threshold} - можна")
            else:
                self.logger.debug(f"✗ Минуло {months_passed} міс. < {months_threshold} - рано")
            return can_apply
        except Exception as e:
            # Якщо помилка парсингу - дозволяємо відгук
            self.logger.debug(f"⚠️ Помилка парсингу дати: {e} - дозволяю відгук")
            return True

    def get_months_since_application(self, url: str) -> Optional[int]:
        """Отримати скільки місяців минуло з останнього відгуку"""
        record = self.get_application(url)
        if not record:
            return None

        try:
            date_applied = datetime.strptime(record["date_applied"], "%Y-%m-%d")
            now = datetime.now()
            months_passed = self.calculate_months_between(date_applied, now)
            return months_passed
        except Exception:
            return None


class SupabaseVacancyDatabase(VacancyDatabase):
    """Supabase-based vacancy database"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Validate configuration
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise ValueError(
                "Supabase configuration missing. Please set SUPABASE_URL and SUPABASE_KEY "
                "environment variables."
            )
        
        try:
            from supabase import create_client, Client
            self.client: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
            self.table_name = "applied_jobs"
            self.logger.info("✅ Supabase database initialized")
        except ImportError as e:
            raise ImportError(
                "Supabase library not installed. Install with: pip install supabase"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Supabase client: {e}") from e

    def get_application(self, url: str) -> Optional[Dict[str, str]]:
        """Отримати запис про відгук за URL"""
        try:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("url", url)
                .execute()
            )
            
            if response.data and len(response.data) > 0:
                record = response.data[0]
                self.logger.debug(
                    f"🔍 Знайдено в БД: {record['date_applied']} - {record.get('title', '')}"
                )
                return {
                    "url": record["url"],
                    "date_applied": record["date_applied"],
                    "title": record.get("title", ""),
                    "company": record.get("company", ""),
                }
            
            self.logger.debug("🔍 Не знайдено в БД")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Помилка читання з Supabase: {e}")
            return None

    def add_or_update(self, url: str, date_applied: str, title: str = "", company: str = ""):
        """Додати або оновити запис про відгук
        
        Uses atomic upsert to avoid race conditions with concurrent bot instances.
        """
        try:
            data = {
                "url": url,
                "date_applied": date_applied,
                "title": title,
                "company": company,
            }
            
            # Atomic upsert on URL field to prevent race conditions
            self.client.table(self.table_name).upsert(data, on_conflict="url").execute()
            self.logger.debug(f"💾 Upsert запису: {date_applied} - {title}")
                
        except Exception as e:
            self.logger.error(f"❌ Помилка запису в Supabase: {e}")

    def should_reapply(self, url: str, months_threshold: int) -> bool:
        """
        Перевірити чи можна повторно відгукнутись

        Returns:
            True - якщо можна відгукуватись (немає в БД або пройшло достатньо часу)
            False - якщо не можна (є в БД і не пройшло достатньо часу)
        """
        record = self.get_application(url)
        if not record:
            self.logger.debug("✓ Немає в БД - можна відгукуватись")
            return True

        try:
            # Supabase returns date_applied as string in YYYY-MM-DD format
            date_str = record["date_applied"]
            # Handle both string and date objects for compatibility
            if not isinstance(date_str, str):
                date_str = str(date_str)
            
            date_applied = datetime.strptime(date_str, "%Y-%m-%d")
            now = datetime.now()
            months_passed = self.calculate_months_between(date_applied, now)

            can_apply = months_passed >= months_threshold
            if can_apply:
                self.logger.debug(f"✓ Минуло {months_passed} міс. >= {months_threshold} - можна")
            else:
                self.logger.debug(f"✗ Минуло {months_passed} міс. < {months_threshold} - рано")
            return can_apply
        except Exception as e:
            # Якщо помилка парсингу - дозволяємо відгук
            self.logger.debug(f"⚠️ Помилка парсингу дати: {e} - дозволяю відгук")
            return True

    def get_months_since_application(self, url: str) -> Optional[int]:
        """Отримати скільки місяців минуло з останнього відгуку"""
        record = self.get_application(url)
        if not record:
            return None

        try:
            # Supabase returns date_applied as string in YYYY-MM-DD format
            date_str = record["date_applied"]
            # Handle both string and date objects for compatibility
            if not isinstance(date_str, str):
                date_str = str(date_str)
                
            date_applied = datetime.strptime(date_str, "%Y-%m-%d")
            now = datetime.now()
            months_passed = self.calculate_months_between(date_applied, now)
            return months_passed
        except Exception:
            return None
