"""База даних для відстеження вакансій на які вже відгукувались"""

import csv
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path
import logging


class VacancyDatabase:
    """Робота з базою даних відгуків"""

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
