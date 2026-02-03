"""Web scraper для Work.ua використовуючи Playwright"""

import asyncio
import random
from playwright.async_api import async_playwright, Page, Browser
from playwright_stealth import Stealth
from typing import Optional, List
from dataclasses import dataclass
import json
import os
import logging

from config import config
from human_behavior import HumanBehavior
from database import VacancyDatabase
from ui_selectors import WorkUASelectors, UserAgents
from anti_detection import BrowserAntiDetection
from llm_service import LLMAnalysisService


@dataclass
class JobListing:
    """Модель вакансії"""

    url: str
    title: str
    company: str
    location: str
    salary: Optional[str] = None
    description: str = ""
    requirements: List[str] = None
    responsibilities: List[str] = None

    def __post_init__(self):
        if self.requirements is None:
            self.requirements = []
        if self.responsibilities is None:
            self.responsibilities = []


class WorkUAScraper:
    """Scraper для витягування вакансій з Work.ua"""

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.context = None
        self.is_logged_in = False
        self.applied_jobs = set()  # Множина URL вакансій на які вже відгукнулись
        self.db = VacancyDatabase()  # База даних відгуків
        self.llm_service = LLMAnalysisService()  # LLM analysis service

        # Ініціалізація логера
        self.logger = logging.getLogger(__name__)

        # Load resume for LLM analysis
        if self.llm_service.use_llm:
            from llm_service import resolve_resume_path

            resume_path = resolve_resume_path()
            self.llm_service.load_resume(resume_path)

    async def start(self, headless: bool = False):
        """Запустити браузер з stealth режимом та реалістичними налаштуваннями"""
        self.playwright = await async_playwright().start()

        # Launch browser with anti-detection
        self.browser = await self._launch_browser(headless)

        # Create realistic context
        self.context = await self._create_browser_context()
        self.page = await self.context.new_page()

        # Apply stealth mode
        await self._apply_stealth_mode()

        # Load cookies if available
        cookies_loaded = await self.load_cookies()
        if cookies_loaded:
            print("🍪 Cookies завантажено, перевіряю авторизацію...")
            is_logged_in = await self.check_login_status()
            if not is_logged_in:
                print("⚠️ Cookies застаріли, спробую авторизуватись знову...")
                await self.auto_login()
        else:
            await self.auto_login()

    async def _launch_browser(self, headless: bool) -> Browser:
        """Launch browser with anti-detection settings

        Args:
            headless: Whether to run in headless mode

        Returns:
            Browser instance
        """
        return await self.playwright.chromium.launch(
            headless=headless, args=BrowserAntiDetection.BROWSER_ARGS
        )

    async def _create_browser_context(self):
        """Create browser context with realistic settings

        Returns:
            Browser context
        """
        context_config = BrowserAntiDetection.CONTEXT_CONFIG.copy()
        context_config["user_agent"] = random.choice(UserAgents.CHROME_AGENTS)
        return await self.browser.new_context(**context_config)

    async def _apply_stealth_mode(self):
        """Apply stealth mode to avoid detection"""
        # Apply stealth through Stealth class
        stealth = Stealth()
        await stealth.apply_stealth_async(self.context)

        # Add powerful anti-detection scripts
        await self.page.add_init_script(BrowserAntiDetection.get_init_script())

    async def close(self):
        """Закрити браузер"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def _wait_for_page_load(self, timeout: Optional[int] = None):
        """Helper method to wait for page load with human-like delay

        Args:
            timeout: Optional timeout in milliseconds for wait_for_load_state
        """
        if timeout:
            await self.page.wait_for_load_state("networkidle", timeout=timeout)
        else:
            await self.page.wait_for_load_state("networkidle")
        await HumanBehavior.page_load_delay()

    async def save_cookies(self, filepath: str = "cookies.json"):
        """Зберегти cookies"""
        if self.context:
            cookies = await self.context.cookies()
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2)

    async def load_cookies(self, filepath: str = "cookies.json"):
        """Завантажити cookies"""
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            await self.context.add_cookies(cookies)
            self.is_logged_in = True
            return True
        return False

    async def check_login_status(self) -> bool:
        """Перевірити чи користувач авторизований"""
        await self.page.goto(WorkUASelectors.BASE_URL)
        await self._wait_for_page_load()

        # Look for "My Section" link - if exists, then authorized
        try:
            my_section = self.page.locator(WorkUASelectors.MY_SECTION_LINK)
            is_visible = await my_section.count() > 0
            self.is_logged_in = is_visible
        except Exception:
            self.is_logged_in = False

        return self.is_logged_in

    async def auto_login(self) -> bool:
        """Автоматична авторизація через номер телефону з людиноподібною поведінкою"""
        print("\n🔐 Автоматична авторизація...")

        if not config.WORKUA_PHONE:
            print("❌ WORKUA_PHONE не налаштовано в .env")
            return False

        try:
            # Go to login page for job seekers
            await self.page.goto(WorkUASelectors.LOGIN_URL)
            await self._wait_for_page_load()

            # If redirected to personal section - already authorized
            if "/jobseeker/my/" in self.page.url:
                print("✅ Вже авторизовано!")
                self.is_logged_in = True
                await self.save_cookies()
                return True

            # Random mouse movement like a human
            await HumanBehavior.random_mouse_movement(self.page, num_movements=2)

            # Find phone number field
            print(f"📱 Вводжу номер: {config.WORKUA_PHONE}")
            phone_input = self.page.locator(WorkUASelectors.PHONE_INPUT)

            if await phone_input.count() == 0:
                print("❌ Не знайдено поле для введення телефону")
                return False

            # Enter phone number like a human
            await self._enter_phone_number(phone_input)

            # Click "Login" or "Get code"
            submit_button = self.page.locator(WorkUASelectors.SUBMIT_BUTTON)
            if await submit_button.count() > 0:
                await HumanBehavior.click_with_human_behavior(
                    self.page, WorkUASelectors.SUBMIT_BUTTON, scroll_into_view=False
                )

            print("\n⏳ Очікую введення SMS коду (60 секунд)...")
            print("👉 Введіть код на сайті вручну!\n")

            # Wait for authorization (redirect to /jobseeker/my/)
            return await self._wait_for_authorization()

        except Exception as e:
            print(f"❌ Помилка авторизації: {e}")
            return False

    async def _enter_phone_number(self, phone_input):
        """Enter phone number with human-like behavior

        Args:
            phone_input: Phone input locator
        """
        await phone_input.click()
        await HumanBehavior.random_delay(0.3, 0.6)

        # Clear field first (Ctrl+A + Delete)
        await phone_input.press("Control+A")
        await phone_input.press("Backspace")
        await HumanBehavior.random_delay(0.2, 0.4)

        # Character-by-character input to bypass mask
        for char in config.WORKUA_PHONE:
            await phone_input.type(char, delay=random.uniform(50, 150))

        await HumanBehavior.random_delay(0.5, 0.9)
        await HumanBehavior.random_delay(0.7, 1.2)

    async def _wait_for_authorization(self) -> bool:
        """Wait for authorization to complete

        Returns:
            True if authorization successful, False otherwise
        """
        try:
            # Poll for successful authorization by checking URL
            timeout_ms = 60000
            check_interval_sec = 0.5
            deadline = asyncio.get_event_loop().time() + timeout_ms / 1000

            while True:
                current_url = self.page.url.lower()
                if "/jobseeker/my/" in current_url or "login" not in current_url:
                    print("✅ Авторизація успішна!")

                    # Additional delay for session stabilization
                    await asyncio.sleep(2)

                    # Save cookies
                    await self.save_cookies()
                    self.is_logged_in = True

                    print("💾 Cookies збережено")
                    return True

                if asyncio.get_event_loop().time() >= deadline:
                    print("⏱️ Час вичерпано: не вдалося дочекатися авторизації")
                    return False

                await asyncio.sleep(check_interval_sec)

        except Exception as e:
            print(f"⏱️ Помилка авторизації: {e}")
            return False

    async def search_jobs(
        self,
        keyword: str,
        location: Optional[str] = None,
        max_pages: int = 3,
        remote: bool = False,
        target_jobs: Optional[int] = None,
    ) -> List[JobListing]:
        """Пошук вакансій за ключовим словом з людиноподібною поведінкою

        Args:
            keyword: Ключове слово для пошуку (наприклад, "python developer")
            location: Місто або "Дистанційно" (опціонально)
            max_pages: Максимальна кількість сторінок для парсингу
            remote: True якщо шукаємо тільки дистанційну роботу
            target_jobs: Ціль кількості вакансій (зупинимось коли досягнемо)
        """
        jobs = []
        self.logger.info(f"🔍 Пошук за запитом: {keyword}")
        self.logger.info(f"🔄 Початок сканування до {max_pages} сторінок...")

        for page_num in range(1, max_pages + 1):
            self.logger.info(f"📄 Обробка сторінки {page_num}/{max_pages}...")
            # Переходимо на сторінку пошуку
            if page_num == 1:
                # Перша сторінка
                if remote:
                    # Для remote вакансій використовуємо прямий URL
                    # Work.ua очікує пробіли замінені на плюс: jobs-remote-менеджер+з+продажу/
                    encoded_keyword = keyword.strip().replace(" ", "+")
                    search_url = f"https://www.work.ua/jobs-remote-{encoded_keyword}/"

                    # Додаємо фільтр мінімальної зарплати якщо вказано
                    if hasattr(config, "MIN_SALARY") and config.MIN_SALARY > 0:
                        search_url += f"?salaryfrom={config.MIN_SALARY}"
                        print(f"💰 [REMOTE] Фільтр мін. зарплати: salaryfrom={config.MIN_SALARY}")

                    print(f"🌐 [REMOTE] Перехід на URL: {search_url}")
                    await self.page.goto(search_url)
                    print("⏳ [REMOTE] Очікування завантаження сторінки...")
                    await self._wait_for_page_load()
                    print("✅ [REMOTE] Сторінка завантажена")
                    print("🖱️ [REMOTE] Рух миші")
                    # Невеликий рух миші
                    await HumanBehavior.random_mouse_movement(self.page, num_movements=1)
                    print(f"✅ [REMOTE] Готово до парсингу. URL: {self.page.url}")
                else:
                    print(f"🌐 [FORM] Перехід на сторінку пошуку: {WorkUASelectors.SEARCH_URL}")
                    # Для звичайного пошуку використовуємо форму
                    await self.page.goto(WorkUASelectors.SEARCH_URL)
                    await self._wait_for_page_load()

                    # Заповнюємо форму
                    # Невеликі рухи миші як людина дивиться на сторінку
                    await HumanBehavior.random_mouse_movement(self.page, num_movements=2)

                    # Знайти поле пошуку та очистити його
                    search_input = self.page.locator(WorkUASelectors.SEARCH_INPUT).first
                    await search_input.click()
                    await HumanBehavior.random_delay(0.3, 0.5)

                    # Очистити поле
                    await search_input.fill("")
                    await HumanBehavior.random_delay(0.2, 0.3)

                    # Ввести текст через pressSequentially
                    await search_input.press_sequentially(keyword, delay=random.uniform(50, 120))
                    await HumanBehavior.random_delay(0.3, 0.5)

                    # Закрити dropdown якщо з'явився
                    await self.page.keyboard.press("Escape")
                    await HumanBehavior.random_delay(0.2, 0.4)

                    if location:
                        # Для звичайного пошуку вказуємо місто
                        await HumanBehavior.random_delay(0.3, 0.7)

                        location_input = self.page.locator(WorkUASelectors.LOCATION_INPUT).first
                        await location_input.click()
                        await HumanBehavior.random_delay(0.2, 0.4)

                        # Очистити поле локації
                        await location_input.fill("")
                        await HumanBehavior.random_delay(0.2, 0.3)

                        # Ввести локацію
                        await location_input.press_sequentially(
                            location, delay=random.uniform(50, 120)
                        )
                        await HumanBehavior.random_delay(0.2, 0.4)

                        # Закрити dropdown
                        await self.page.keyboard.press("Escape")

                    # Пауза перед пошуком
                    await HumanBehavior.random_delay(0.5, 1.0)

                    # Клік на кнопку пошуку
                    await HumanBehavior.click_with_human_behavior(
                        self.page, WorkUASelectors.SEARCH_BUTTON, scroll_into_view=False
                    )
                    await self._wait_for_page_load()
            else:
                # Наступні сторінки - додаємо ?page=N або &page=N
                current_url = self.page.url.split("?")[0]  # Базовий URL без параметрів

                # Перевіряємо чи є salaryfrom в оригінальному URL
                if "?salaryfrom=" in self.page.url:
                    salary = self.page.url.split("?salaryfrom=")[1].split("&")[0]
                    url = f"{current_url}?salaryfrom={salary}&page={page_num}"
                else:
                    url = f"{current_url}?page={page_num}"

                print(f"📄 Перехід на сторінку {page_num}: {url}")
                await self.page.goto(url)
                await self._wait_for_page_load()

            print(f"🔍 Пошук сторінка {page_num}: {self.page.url}")

            # Прокрутити сторінку вниз як людина читає
            await HumanBehavior.scroll_page_human_like(self.page, scroll_distance=500)
            print(f"🔍 Пошук сторінка {page_num}: {self.page.url}")

            # Прокрутити сторінку вниз як людина читає
            print("📜 Прокрутка сторінки...")
            await HumanBehavior.scroll_page_human_like(self.page, scroll_distance=500)

            # Парсимо вакансії на сторінці
            self.logger.info(f"🔎 Парсинг вакансій на сторінці {page_num}...")
            page_jobs = await self._parse_search_results()

            # Додаємо знайдені вакансії (навіть якщо 0 - продовжуємо далі)
            if page_jobs:
                jobs.extend(page_jobs)
                self.logger.info(
                    f"✅ Знайдено {len(page_jobs)} вакансій на сторінці {page_num}. Всього: {len(jobs)}"
                )
            else:
                self.logger.info(
                    f"⚠️ Сторінка {page_num}: 0 нових вакансій (всі вже переглянуті). Продовжуємо далі..."
                )

            # Перевірка чи зібрали достатньо вакансій
            if target_jobs and len(jobs) >= target_jobs:
                self.logger.info(
                    f"🎯 Зібрано достатньо: {len(jobs)}/{target_jobs} вакансій. Зупиняємо сканування."
                )
                break

            # Пауза між сторінками як людина
            await HumanBehavior.random_delay(2.0, 4.0)

        self.logger.info(
            f"🏁 Сканування завершено. Знайдено {len(jobs)} вакансій на {page_num} сторінках"
        )
        return jobs

    async def _parse_search_results(self) -> List[JobListing]:
        """Парсинг результатів пошуку"""
        self.logger.debug("📋 Початок _parse_search_results()")
        jobs = []

        # Використовуємо role selector для заголовків level=2 (це вакансії)
        try:
            # Всі заголовки h2 на сторінці - це вакансії
            self.logger.debug("🔍 Пошук заголовків h2 (role=heading, level=2)...")
            job_headings = await self.page.get_by_role(
                "heading", level=WorkUASelectors.JOB_HEADINGS_LEVEL
            ).all()
            self.logger.info(f"📊 Знайдено {len(job_headings)} заголовків h2 на сторінці")

            for idx, heading in enumerate(job_headings, 1):
                try:
                    print(f"\n--- Обробка вакансії {idx}/{len(job_headings)} ---")
                    # Отримати посилання з заголовка
                    link = heading.locator("a").first

                    if not await link.count():
                        print(f"⚠️ Немає посилання в заголовку {idx}")
                        continue

                    url = await link.get_attribute("href")
                    if not url or "/jobs/" not in url:
                        print(f"⚠️ Невалідний URL: {url}")
                        continue

                    if url and not url.startswith("http"):
                        url = WorkUASelectors.BASE_URL + url

                    title = await link.text_content()
                    self.logger.debug(f"✅ Вакансія: {title}")
                    self.logger.debug(f"🔗 URL: {url}")

                    # ПЕРЕВІРКА БД перед додаванням в список
                    self.logger.debug(f"🗄️ Перевіряю БД для {url[:50]}...")
                    if not self.db.should_reapply(url, config.REAPPLY_AFTER_MONTHS):
                        months = self.db.get_months_since_application(url)
                        self.logger.debug(
                            f"⏭️ БД: Відгукувались {months} міс. тому - ПРОПУСКАЮ при зборі"
                        )
                        continue

                    # Спрощено - створюємо вакансію з мінімальною інформацією
                    # Деталі завантажимо пізніше при переході на вакансію
                    job = JobListing(
                        url=url,
                        title=title.strip(),
                        company="",  # Завантажимо пізніше
                        location="",  # Завантажимо пізніше
                        salary=None,  # Завантажимо пізніше
                    )
                    jobs.append(job)
                    print("✓ Додано в список")

                except Exception as e:
                    print(f"⚠️ Помилка парсингу вакансії: {e}")
                    continue

        except Exception as e:
            print(f"⚠️ Помилка пошуку вакансій: {e}")

        print(f"✅ Парсинг завершено. Всього знайдено: {len(jobs)}")
        return jobs

    async def _extract_job_from_element(self, element) -> Optional[JobListing]:
        """Витягти дані вакансії з елемента"""
        try:
            # URL вакансії
            link = await element.query_selector('a[href*="/jobs/"]')
            if not link:
                return None
            url = await link.get_attribute("href")
            if url and not url.startswith("http"):
                url = WorkUASelectors.BASE_URL + url

            # Назва
            title_elem = await element.query_selector('h2, .card-title, [class*="title"]')
            title = await title_elem.text_content() if title_elem else "Без назви"

            # Компанія
            company_elem = await element.query_selector('[class*="company"], [class*="employer"]')
            company = await company_elem.text_content() if company_elem else "Невідома компанія"

            # Локація
            location_elem = await element.query_selector('[class*="location"], [class*="city"]')
            location = await location_elem.text_content() if location_elem else ""

            # Зарплата
            salary_elem = await element.query_selector('[class*="salary"], [class*="price"]')
            salary = await salary_elem.text_content() if salary_elem else None

            return JobListing(
                url=url,
                title=title.strip(),
                company=company.strip(),
                location=location.strip(),
                salary=salary.strip() if salary else None,
            )
        except Exception as e:
            print(f"⚠️ Помилка витягування даних: {e}")
            return None

    async def _has_next_page(self) -> bool:
        """Перевірити чи є наступна сторінка"""
        try:
            # Шукаємо посилання з rel="next"
            next_link = self.page.locator(WorkUASelectors.NEXT_PAGE_LINK)
            return await next_link.count() > 0
        except Exception:
            return False

    async def get_job_details(self, job: JobListing) -> JobListing:
        """Отримати повні деталі вакансії з людиноподібною поведінкою"""
        print(f"📄 Завантаження деталей: {job.title}")

        await self.page.goto(job.url)
        await self._wait_for_page_load()

        # Опис вакансії - знаходиться в секції з заголовком "Опис вакансії"
        try:
            # Шукаємо заголовок "Опис вакансії"
            desc_heading = self.page.get_by_role("heading", name="Опис вакансії")
            # Беремо наступний елемент після заголовка
            desc_elem = desc_heading.locator("xpath=following-sibling::*[1]")
            if await desc_elem.count():
                job.description = await desc_elem.text_content()
                job.description = job.description.strip()
                # Імітація читання тексту
                await HumanBehavior.reading_delay(len(job.description))
        except Exception:
            # Fallback - весь main
            try:
                main_elem = self.page.locator("main").first
                if await main_elem.count():
                    job.description = await main_elem.text_content()
                    job.description = job.description.strip()
            except Exception:
                # Fallback failed - main element not found or inaccessible
                # Continue with empty description rather than blocking the workflow
                pass

        return job

    async def apply_to_job(self, job: JobListing) -> bool:
        """Відгукнутися на вакансію в новій вкладці"""
        if not self.is_logged_in:
            self.logger.warning("❌ Неможливо відгукнутись - немає авторизації")
            return False

        self.logger.info(f"📤 Відгук на: {job.title}")
        self.logger.info(f"🔗 URL: {job.url}")

        # ПЕРЕВІРКА 1: База даних - чи вже відгукувались і чи пройшов термін
        self.logger.debug("🗄️ Перевіряю базу даних...")
        if not self.db.should_reapply(job.url, config.REAPPLY_AFTER_MONTHS):
            months = self.db.get_months_since_application(job.url)
            self.logger.debug(
                f"⏭️ БД: Відгукувались {months} міс. тому (потрібно {config.REAPPLY_AFTER_MONTHS}+) - пропускаю"
            )
            self.applied_jobs.add(job.url)
            return False

        # Переходимо на вакансію в основній вкладці
        try:
            self.logger.debug("🌐 Переходжу на сторінку вакансії...")
            await self.page.goto(job.url, timeout=60000)  # Збільшено до 60 секунд
            await self._wait_for_page_load(timeout=30000)
            self.logger.debug("✅ Сторінка завантажена")

            # ПЕРЕВІРКА 2: Сторінка вакансії - чи є мітка "Ви вже відгукалися"
            self.logger.debug("🔍 Перевірка чи є відгук на сторінці...")
            # Шукаємо параграф з текстом "Ви вже відгукалися на цю вакансію"
            already_sent = self.page.locator(WorkUASelectors.ALREADY_APPLIED_TEXT)

            if await already_sent.count() > 0:
                try:
                    text = await already_sent.first.text_content()
                    self.logger.debug(f"📅 Знайдено: {text}")

                    # Парсимо дату з формату "Ви вже відгукалися на цю вакансію DD.MM.YYYY"
                    import re
                    from datetime import datetime

                    date_match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", text)
                    if date_match:
                        day, month, year = date_match.groups()
                        applied_date = datetime(int(year), int(month), int(day))
                        now = datetime.now()
                        months_passed = self.db.calculate_months_between(applied_date, now)

                        self.logger.debug(
                            f"📆 Дата відгуку: {applied_date.strftime('%d.%m.%Y')} (минуло {months_passed} міс.)"
                        )

                        # Оновлюємо базу даних з датою зі сторінки
                        db_date = applied_date.strftime("%Y-%m-%d")
                        self.db.add_or_update(job.url, db_date, job.title, job.company)
                        self.logger.debug(f"💾 Оновлено БД з датою {db_date}")

                        if months_passed < config.REAPPLY_AFTER_MONTHS:
                            self.logger.debug(
                                f"⏭️ Відгукувались {months_passed} міс. тому (потрібно {config.REAPPLY_AFTER_MONTHS}+) - пропускаю"
                            )
                            self.applied_jobs.add(job.url)
                            return False
                        else:
                            self.logger.debug(
                                f"🔄 Минуло {months_passed} міс. - можна відправити повторно"
                            )
                    else:
                        self.logger.debug("⚠️ Не вдалось розпарсити дату, продовжую")
                except Exception as e:
                    self.logger.debug(f"⚠️ Помилка перевірки already-sent: {e}, продовжую")

            # LLM аналіз перед відгуком (якщо увімкнено)
            if config.USE_PRE_APPLY_LLM_CHECK:
                self.logger.debug("🤖 LLM аналіз вакансії...")
                # Витягуємо весь текст вакансії
                try:
                    main_content = self.page.locator("main").first
                    if await main_content.count() > 0:
                        job_text = await main_content.text_content()

                        # Analyze through LLM
                        probability, explanation = await self.llm_service.analyze_job_match(
                            job_text
                        )
                        self.logger.debug(f"📊 Ймовірність прийняття: {probability}%")
                        self.logger.debug(f"💭 {explanation}")

                        if probability < config.MIN_MATCH_PROBABILITY:
                            self.logger.debug(
                                f"⏭️ Ймовірність ({probability}%) нижче мінімуму ({config.MIN_MATCH_PROBABILITY}%) - пропускаю"
                            )
                            self.applied_jobs.add(job.url)
                            return False
                        else:
                            self.logger.debug("✓ Ймовірність достатня - продовжую відгук")
                except Exception as e:
                    self.logger.debug(f"⚠️ Помилка LLM аналізу: {e}, продовжую без перевірки")

            self.logger.debug("✓ Перевірки пройдені, можна подавати")

            # Прокрутити сторінку вниз щоб завантажити всі елементи
            self.logger.debug("📜 Прокручую сторінку...")
            await HumanBehavior.scroll_page_human_like(self.page, scroll_distance=300)

            # Рандомна пауза як людина думає чи відгукуватися
            await HumanBehavior.random_delay(1.0, 2.5)

            # Клік на кнопку "Відгукнутися" або "Переглянути резюме" (якщо вже відгукувались)
            self.logger.debug("🖱️ Шукаю кнопку відгуку...")
            apply_button = self.page.locator(WorkUASelectors.APPLY_BUTTON).first

            # Якщо не знайдено "Відгукнутися", шукаємо "Переглянути резюме" (для повторного відгуку)
            if await apply_button.count() == 0:
                self.logger.debug(
                    "🔄 Кнопка 'Відгукнутися' не знайдена, шукаю 'Переглянути резюме'..."
                )
                apply_button = self.page.locator(WorkUASelectors.REVIEW_RESUME_BUTTON).first

                if await apply_button.count() == 0:
                    self.logger.debug("❌ Не знайдено жодної кнопки для відгуку")
                    return False
                else:
                    self.logger.debug(
                        "✓ Знайдено кнопку 'Переглянути резюме' - це повторний відгук"
                    )

            # Прокрутити до кнопки щоб вона стала видимою
            self.logger.debug("📜 Прокручую до кнопки...")
            try:
                await apply_button.scroll_into_view_if_needed(timeout=10000)
            except Exception as e:
                self.logger.debug(f"⚠️ Помилка прокрутки: {e}, пробую без прокрутки")

            # Пауза перед кліком
            await HumanBehavior.random_delay(0.5, 1.0)

            self.logger.debug("🖱️ Клікаю кнопку...")
            try:
                # Спочатку пробуємо звичайний клік з очікуванням видимості
                await apply_button.click(timeout=15000)
            except Exception as e:
                self.logger.debug(f"⚠️ Звичайний клік не вдався: {e}")
                try:
                    # Якщо не вдалось - force click (клік навіть якщо не видимий)
                    self.logger.debug("🔄 Пробую force click...")
                    await apply_button.click(force=True, timeout=5000)
                except Exception as e2:
                    self.logger.debug(f"❌ Force click теж не вдався: {e2}")
                    # Якщо обидва кліки не вдались - пропускаємо вакансію
                    return False

            await self._wait_for_page_load(timeout=30000)
            self.logger.debug("✓ Кнопка натиснута")

            # Чекаємо появи dialog/modal з формою
            self.logger.debug("⏳ Чекаю модальне вікно...")
            await HumanBehavior.random_delay(0.8, 1.5)

            # Перевіряємо чи з'явилось модальне вікно з вибором резюме
            # Якщо користувач залогінений, повинна з'явитись кнопка "Надіслати"
            send_button = self.page.locator(WorkUASelectors.SEND_BUTTON)
            if await send_button.count() == 0:
                self.logger.debug("⚠️ Не знайдено кнопку відправки резюме")
                return False

            self.logger.debug("🖱️ Клікаю 'Надіслати'...")
            await send_button.first.click()
            await self._wait_for_page_load()
            await HumanBehavior.random_delay(0.5, 1.0)

            # Перевіряємо чи з'явився діалог підтвердження повторного відгуку
            confirm_reapply = self.page.locator(WorkUASelectors.CONFIRM_REAPPLY_BUTTON)
            if await confirm_reapply.count() > 0:
                self.logger.debug("🔄 Підтвердження повторного відгуку...")
                await confirm_reapply.first.click()
                await self._wait_for_page_load()
                self.logger.debug("✓ Підтверджено повторний відгук")
            else:
                self.logger.debug("✓ Резюме відправлено")

            # Може з'явитися додатковий діалог про додавання локації
            await HumanBehavior.random_delay(0.5, 1.0)
            not_add_button = self.page.locator(WorkUASelectors.NOT_ADD_BUTTON)
            if await not_add_button.count() > 0:
                self.logger.debug("🖱️ Закриваю діалог локації...")
                await not_add_button.first.click()
                await self._wait_for_page_load()

            # Перевіряємо чи успішно відгукнулись
            await HumanBehavior.random_delay(0.5, 1.0)
            success = False

            # Перевіряємо різні ознаки успіху
            if "/sent/" in self.page.url:
                success = True
            elif (
                await self.page.locator("text=успішно").count() > 0
                or await self.page.locator("text=Дякуємо").count() > 0
                or await self.page.locator("text=відгукнулись").count() > 0
            ):
                success = True
            elif await self.page.locator(WorkUASelectors.REVIEW_RESUME_BUTTON).count() > 0:
                success = True

            if success:
                self.logger.debug(f"✅ Успішно відгукнулись на: {job.title}")
                self.applied_jobs.add(job.url)  # Додаємо до списку

                # Оновлюємо базу даних з поточною датою
                from datetime import datetime

                today = datetime.now().strftime("%Y-%m-%d")
                self.db.add_or_update(job.url, today, job.title, job.company)
                self.logger.debug(f"💾 Збережено в БД: {today}")
            else:
                self.logger.debug("⚠️ Невідомий статус відгуку - НЕ оновлюю БД")

            return success

        except Exception as e:
            self.logger.error(f"❌ Помилка при відгуку: {e}")
            return False


async def test_scraper():
    """Тестування scraper"""
    scraper = WorkUAScraper()

    try:
        await scraper.start(headless=False)

        # Перевірка авторизації
        is_logged_in = await scraper.check_login_status()
        print(f"Статус авторизації: {'✓ Авторизовано' if is_logged_in else '✗ Не авторизовано'}")

        # Пошук вакансій
        jobs = await scraper.search_jobs("python developer", max_pages=2)
        print(f"\n📊 Знайдено всього: {len(jobs)} вакансій")

        # Вивести перші 3
        for i, job in enumerate(jobs[:3], 1):
            print(f"\n{i}. {job.title}")
            print(f"   Компанія: {job.company}")
            print(f"   Локація: {job.location}")
            print(f"   Зарплата: {job.salary or 'Не вказано'}")
            print(f"   URL: {job.url}")

        # Отримати деталі першої вакансії
        if jobs:
            detailed_job = await scraper.get_job_details(jobs[0])
            print("\n📝 Опис вакансії (перші 300 символів):")
            print(detailed_job.description[:300] + "...")

    finally:
        await scraper.close()


if __name__ == "__main__":
    print("🧪 Тестування Work.ua Scraper\n")
    asyncio.run(test_scraper())
