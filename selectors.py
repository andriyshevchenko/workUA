"""UI selectors for Work.ua website"""


class WorkUASelectors:
    """Centralized selectors for Work.ua UI elements"""

    # URLs
    BASE_URL = "https://www.work.ua"
    LOGIN_URL = "https://www.work.ua/jobseeker/login/"
    SEARCH_URL = "https://www.work.ua/jobs/"

    # Login Page
    PHONE_INPUT = '#phone'
    SUBMIT_BUTTON = 'button[type="submit"]'

    # Navigation
    MY_SECTION_LINK = 'a:has-text("Мій розділ")'

    # Search Form
    SEARCH_INPUT = 'input[name="search"], input[placeholder*="Посада"]'
    LOCATION_INPUT = 'input[placeholder*="Місто"]'
    SEARCH_BUTTON = 'button[type="submit"], button:has-text("Знайти")'

    # Search Results
    JOB_HEADINGS_LEVEL = 2  # h2 elements are job listings

    # Job Details Page
    APPLY_BUTTON = 'button:has-text("Відгукнутися")'
    REVIEW_RESUME_BUTTON = 'button:has-text("Переглянути резюме")'
    ALREADY_APPLIED_TEXT = 'p:has-text("Ви вже відгукалися")'

    # Apply Dialog
    SEND_BUTTON = 'button:has-text("Надіслати"), button:has-text("Продовжити")'
    CONFIRM_REAPPLY_BUTTON = 'button:has-text("Так, відгукнутися")'
    NOT_ADD_BUTTON = 'button:has-text("Не додавати")'

    # Success Indicators
    SUCCESS_TEXT_PATTERNS = ['успішно', 'Дякуємо', 'відгукнулись']

    # Pagination
    NEXT_PAGE_LINK = 'a[rel="next"]'


class UserAgents:
    """List of realistic user agents for anti-detection"""

    CHROME_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    ]
