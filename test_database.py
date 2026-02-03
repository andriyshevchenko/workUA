"""Unit tests for database module"""

import pytest
from datetime import datetime
from database import VacancyDatabase


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing"""
    db_path = tmp_path / "test_applied_jobs.csv"
    db = VacancyDatabase(str(db_path))
    return db


class TestVacancyDatabase:
    """Test cases for VacancyDatabase class"""

    def test_db_creation(self, temp_db):
        """Test database file creation"""
        assert temp_db.db_path.exists()

    def test_calculate_months_between(self):
        """Test month calculation between dates"""
        from_date = datetime(2023, 1, 15)
        to_date = datetime(2023, 6, 15)

        months = VacancyDatabase.calculate_months_between(from_date, to_date)
        assert months == 5

    def test_calculate_months_between_same_month(self):
        """Test month calculation for same month"""
        from_date = datetime(2023, 5, 1)
        to_date = datetime(2023, 5, 31)

        months = VacancyDatabase.calculate_months_between(from_date, to_date)
        assert months == 0

    def test_calculate_months_between_year_boundary(self):
        """Test month calculation across year boundary"""
        from_date = datetime(2022, 11, 1)
        to_date = datetime(2023, 2, 1)

        months = VacancyDatabase.calculate_months_between(from_date, to_date)
        assert months == 3

    def test_add_new_application(self, temp_db):
        """Test adding a new application"""
        url = "https://www.work.ua/jobs/12345/"
        date = "2023-05-15"
        title = "Python Developer"
        company = "Tech Corp"

        temp_db.add_or_update(url, date, title, company)

        record = temp_db.get_application(url)
        assert record is not None
        assert record["url"] == url
        assert record["date_applied"] == date
        assert record["title"] == title
        assert record["company"] == company

    def test_update_existing_application(self, temp_db):
        """Test updating an existing application"""
        url = "https://www.work.ua/jobs/12345/"
        date1 = "2023-05-15"
        date2 = "2023-10-20"
        title = "Python Developer"
        company = "Tech Corp"

        # Add first
        temp_db.add_or_update(url, date1, title, company)

        # Update
        temp_db.add_or_update(url, date2, title, company)

        record = temp_db.get_application(url)
        assert record["date_applied"] == date2

    def test_get_nonexistent_application(self, temp_db):
        """Test getting application that doesn't exist"""
        url = "https://www.work.ua/jobs/99999/"

        record = temp_db.get_application(url)
        assert record is None

    def test_should_reapply_not_in_db(self, temp_db):
        """Test should_reapply for URL not in database"""
        url = "https://www.work.ua/jobs/12345/"

        result = temp_db.should_reapply(url, months_threshold=2)
        assert result is True

    def test_should_reapply_too_recent(self, temp_db):
        """Test should_reapply when application is too recent"""
        url = "https://www.work.ua/jobs/12345/"

        # Add application from 1 month ago
        one_month_ago = datetime.now()
        if one_month_ago.month == 1:
            one_month_ago = one_month_ago.replace(year=one_month_ago.year - 1, month=12)
        else:
            one_month_ago = one_month_ago.replace(month=one_month_ago.month - 1)
        date = one_month_ago.strftime("%Y-%m-%d")

        temp_db.add_or_update(url, date, "Test Job", "Test Company")

        # Should not reapply (threshold is 2 months)
        result = temp_db.should_reapply(url, months_threshold=2)
        assert result is False

    def test_should_reapply_enough_time_passed(self, temp_db):
        """Test should_reapply when enough time has passed"""
        url = "https://www.work.ua/jobs/12345/"

        # Add application from 3 months ago
        three_months_ago = datetime.now()
        if three_months_ago.month <= 3:
            three_months_ago = three_months_ago.replace(
                year=three_months_ago.year - 1, month=three_months_ago.month + 12 - 3
            )
        else:
            three_months_ago = three_months_ago.replace(month=three_months_ago.month - 3)
        date = three_months_ago.strftime("%Y-%m-%d")

        temp_db.add_or_update(url, date, "Test Job", "Test Company")

        # Should reapply (threshold is 2 months)
        result = temp_db.should_reapply(url, months_threshold=2)
        assert result is True

    def test_get_months_since_application(self, temp_db):
        """Test getting months since last application"""
        url = "https://www.work.ua/jobs/12345/"

        # Add application from 2 months ago
        two_months_ago = datetime.now()
        if two_months_ago.month <= 2:
            two_months_ago = two_months_ago.replace(
                year=two_months_ago.year - 1, month=two_months_ago.month + 12 - 2
            )
        else:
            two_months_ago = two_months_ago.replace(month=two_months_ago.month - 2)
        date = two_months_ago.strftime("%Y-%m-%d")

        temp_db.add_or_update(url, date, "Test Job", "Test Company")

        months = temp_db.get_months_since_application(url)
        assert months == 2

    def test_get_months_since_application_not_in_db(self, temp_db):
        """Test getting months for URL not in database"""
        url = "https://www.work.ua/jobs/99999/"

        months = temp_db.get_months_since_application(url)
        assert months is None
