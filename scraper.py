"""Web scraper для Work.ua використовуючи Playwright"""
import asyncio
import random
from playwright.async_api import async_playwright, Page, Browser
from playwright_stealth import Stealth
from typing import Optional, List, Dict
from dataclasses import dataclass
from config import config
from human_behavior import HumanBehavior
import json
import os


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
        
    async def start(self, headless: bool = False):
        """Запустити браузер з stealth режимом та реалістичними налаштуваннями"""
        self.playwright = await async_playwright().start()
        
        # Реалістичні User-Agent варіанти
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        ]
        
        # Запустити браузер з анти-детекцією
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--start-maximized',  # Максимізувати вікно
            ]
        )
        
        # Створити реалістичний контекст з меншим viewport
        self.context = await self.browser.new_context(
            no_viewport=True,  # Дозволити браузеру використовувати повний розмір вікна
            locale='uk-UA',
            timezone_id='Europe/Kyiv',
            user_agent=random.choice(user_agents),
            permissions=['geolocation'],
            geolocation={'latitude': 50.4501, 'longitude': 30.5234},  # Київ
            color_scheme='light',
            has_touch=False,
            is_mobile=False,
        )
        
        self.page = await self.context.new_page()
        
        # Застосувати stealth режим через клас Stealth
        stealth = Stealth()
        await stealth.apply_stealth_async(self.context)
        
        # Додаткові потужні скрипти для обходу FRONTEND детекції
        await self.page.add_init_script("""
            // 1. Видалити webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // 2. Замаскувати chrome
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // 3. Permissions API
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // 4. Plugins - зробити реалістичним
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // 5. Languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['uk-UA', 'uk', 'en-US', 'en']
            });
            
            // 6. Platform
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });
            
            // 7. Видалити __playwright та __pw_manual
            delete window.__playwright;
            delete window.__pw_manual;
            delete window.__PW_inspect;
            
            // 8. Видалити playwright з driver
            Object.defineProperty(navigator, 'driver', {
                get: () => undefined
            });
            
            // 9. Battery API - зробити realistic
            Object.defineProperty(navigator, 'getBattery', {
                get: () => async () => ({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1
                })
            });
            
            // 10. Connection API
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    downlink: 10,
                    rtt: 50
                })
            });
            
            // 11. Hardware Concurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            
            // 12. Memory (якщо є)
            if ('deviceMemory' in navigator) {
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8
                });
            }
            
            // 13. Приховати automation-controlled
            const originalEval = window.eval;
            window.eval = function() {
                return originalEval.apply(this, arguments);
            };
            
            // 14. toString override
            window.eval.toString = () => 'function eval() { [native code] }';
        """)
        
        # Завантажити збережені cookies якщо є
        cookies_loaded = await self.load_cookies()
        if not cookies_loaded:
            # Спробувати авторизуватись
            await self.auto_login()
        
    async def close(self):
        """Закрити браузер"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
    async def save_cookies(self, filepath: str = "cookies.json"):
        """Зберегти cookies"""
        if self.context:
            cookies = await self.context.cookies()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2)
                
    async def load_cookies(self, filepath: str = "cookies.json"):
        """Завантажити cookies"""
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            await self.context.add_cookies(cookies)
            self.is_logged_in = True
            return True
        return False
        
    async def check_login_status(self) -> bool:
        """Перевірити чи користувач авторизований"""
        await self.page.goto(config.WORKUA_BASE_URL)
        await self.page.wait_for_load_state('networkidle')
        await HumanBehavior.page_load_delay()
        
        # Шукаємо посилання "Мій розділ" - якщо є, то авторизовані
        try:
            my_section = self.page.locator('a:has-text("Мій розділ")')
            is_visible = await my_section.count() > 0
            self.is_logged_in = is_visible
        except:
            self.is_logged_in = False
            
        return self.is_logged_in
    
    async def auto_login(self) -> bool:
        """Автоматична авторизація через номер телефону з людиноподібною поведінкою"""
        print("\n🔐 Автоматична авторизація...")
        
        if not config.WORKUA_PHONE:
            print("❌ WORKUA_PHONE не налаштовано в .env")
            return False
            
        try:
            # Перейти на сторінку логіну для шукачів роботи
            await self.page.goto("https://www.work.ua/jobseeker/login/")
            await self.page.wait_for_load_state('networkidle')
            await HumanBehavior.page_load_delay()
            
            # Якщо перенаправило на особистий розділ - вже авторизовані
            if '/jobseeker/my/' in self.page.url:
                print("✅ Вже авторизовано!")
                self.is_logged_in = True
                await self.save_cookies()
                return True
            
            # Невеликий рух миші як людина
            await HumanBehavior.random_mouse_movement(self.page, num_movements=2)
            
            # Знайти поле для номера телефону (type="text", id="phone")
            print(f"📱 Вводжу номер: {config.WORKUA_PHONE}")
            phone_input = self.page.locator('#phone')
            
            if await phone_input.count() == 0:
                print("❌ Не знайдено поле для введення телефону")
                return False
            
            # Ввести номер телефону як людина
            await phone_input.click()
            await HumanBehavior.random_delay(0.3, 0.6)
            
            # Очистити поле спочатку (Ctrl+A + Delete)
            await phone_input.press('Control+A')
            await phone_input.press('Backspace')
            await HumanBehavior.random_delay(0.2, 0.4)
            
            # Посимвольне введення для обходу маски
            for char in config.WORKUA_PHONE:
                await phone_input.type(char, delay=random.uniform(50, 150))
            
            await HumanBehavior.random_delay(0.5, 0.9)
            
            # Пауза перед кліком на кнопку
            await HumanBehavior.random_delay(0.7, 1.2)
            
            # Натиснути "Увійти" або "Отримати код"
            submit_button = self.page.locator('button[type="submit"]')
            if await submit_button.count() > 0:
                await HumanBehavior.click_with_human_behavior(
                    self.page,
                    'button[type="submit"]',
                    scroll_into_view=False
                )
            
            print("\n⏳ Очікую введення SMS коду (60 секунд)...")
            print("👉 Введіть код на сайті вручну!\n")
            
            # Чекаємо авторизації (перенаправлення на /jobseeker/my/)
            try:
                await self.page.wait_for_url(
                    lambda url: '/jobseeker/my/' in url.lower() or 'login' not in url.lower(), 
                    timeout=60000
                )
                print("✅ Авторизація успішна!")
                
                # Додаткова затримка для стабілізації session
                await asyncio.sleep(2)
                
                # Зберегти cookies
                await self.save_cookies()
                self.is_logged_in = True
                
                print("💾 Cookies збережено")
                return True
            except:
                print("⏱️ Час вичерпано. Авторизуйтесь пізніше.")
                return False
            
        except Exception as e:
            print(f"❌ Помилка авторизації: {e}")
            return False
        
    async def search_jobs(
        self,
        keyword: str,
        location: Optional[str] = None,
        max_pages: int = 3,
        remote: bool = False
    ) -> List[JobListing]:
        """Пошук вакансій за ключовим словом з людиноподібною поведінкою
        
        Args:
            keyword: Ключове слово для пошуку (наприклад, "python developer")
            location: Місто або "Дистанційно" (опціонально)
            max_pages: Максимальна кількість сторінок для парсингу
            remote: True якщо шукаємо тільки дистанційну роботу
        """
        jobs = []
        
        for page_num in range(1, max_pages + 1):
            # Переходимо на сторінку пошуку
            if page_num == 1:
                # Перша сторінка
                if remote:
                    # Для remote вакансій використовуємо прямий URL з encoded keywords
                    # Формат: jobs-remote-keyword/ де ключові слова розділені +
                    from urllib.parse import quote_plus
                    # Замінити коми та пробіли на +
                    encoded_keyword = keyword.replace(',', '+').replace(' ', '+')
                    search_url = f'https://www.work.ua/jobs-remote-{encoded_keyword}/'
                    
                    # Додаємо фільтр мінімальної зарплати якщо вказано
                    if hasattr(config, 'MIN_SALARY') and config.MIN_SALARY > 0:
                        search_url += f'?salaryfrom={config.MIN_SALARY}'
                        print(f"💰 [REMOTE] Фільтр мін. зарплати: salaryfrom={config.MIN_SALARY}")
                    
                    print(f"🌐 [REMOTE] Перехід на URL: {search_url}")
                    await self.page.goto(search_url)
                    print(f"⏳ [REMOTE] Очікування завантаження сторінки...")
                    await self.page.wait_for_load_state('networkidle')
                    print(f"✅ [REMOTE] Сторінка завантажена")
                    await HumanBehavior.page_load_delay()
                    print(f"🖱️ [REMOTE] Рух миші")
                    # Невеликий рух миші
                    await HumanBehavior.random_mouse_movement(self.page, num_movements=1)
                    print(f"✅ [REMOTE] Готово до парсингу. URL: {self.page.url}")
                else:
                    print(f"🌐 [FORM] Перехід на сторінку пошуку: {config.WORKUA_SEARCH_URL}")
                    # Для звичайного пошуку використовуємо форму
                    await self.page.goto(config.WORKUA_SEARCH_URL)
                    await self.page.wait_for_load_state('networkidle')
                    await HumanBehavior.page_load_delay()
                    
                    # Заповнюємо форму
                    # Невеликі рухи миші як людина дивиться на сторінку
                    await HumanBehavior.random_mouse_movement(self.page, num_movements=2)
                    
                    # Знайти поле пошуку та очистити його
                    search_input = self.page.locator('input[name="search"], input[placeholder*="Посада"]').first
                    await search_input.click()
                    await HumanBehavior.random_delay(0.3, 0.5)
                    
                    # Очистити поле
                    await search_input.fill('')
                    await HumanBehavior.random_delay(0.2, 0.3)
                    
                    # Ввести текст через pressSequentially
                    await search_input.press_sequentially(keyword, delay=random.uniform(50, 120))
                    await HumanBehavior.random_delay(0.3, 0.5)
                    
                    # Закрити dropdown якщо з'явився
                    await self.page.keyboard.press('Escape')
                    await HumanBehavior.random_delay(0.2, 0.4)
                    
                    if location:
                        # Для звичайного пошуку вказуємо місто
                        await HumanBehavior.random_delay(0.3, 0.7)
                        
                        location_input = self.page.locator('input[placeholder*="Місто"]').first
                        await location_input.click()
                        await HumanBehavior.random_delay(0.2, 0.4)
                        
                        # Очистити поле локації
                        await location_input.fill('')
                        await HumanBehavior.random_delay(0.2, 0.3)
                        
                        # Ввести локацію
                        await location_input.press_sequentially(location, delay=random.uniform(50, 120))
                        await HumanBehavior.random_delay(0.2, 0.4)
                        
                        # Закрити dropdown
                        await self.page.keyboard.press('Escape')
                    
                    # Пауза перед пошуком
                    await HumanBehavior.random_delay(0.5, 1.0)
                    
                    # Клік на кнопку пошуку
                    await HumanBehavior.click_with_human_behavior(
                        self.page,
                        'button[type="submit"], button:has-text("Знайти")',
                        scroll_into_view=False
                    )
                    await self.page.wait_for_load_state('networkidle')
                    await HumanBehavior.page_load_delay()
            else:
                # Наступні сторінки - формуємо URL
                current_url = self.page.url
                if '?page=' in current_url:
                    url = current_url.rsplit('?page=', 1)[0] + f'?page={page_num}'
                else:
                    separator = '&' if '?' in current_url else '?'
                    url = current_url + f'{separator}page={page_num}'
                await self.page.goto(url)
                await self.page.wait_for_load_state('networkidle')
                await HumanBehavior.page_load_delay()
            
            print(f"🔍 Пошук сторінка {page_num}: {self.page.url}")
            
            # Прокрутити сторінку вниз як людина читає
            await HumanBehavior.scroll_page_human_like(self.page, scroll_distance=500)
            print(f"🔍 Пошук сторінка {page_num}: {self.page.url}")
            
            # Прокрутити сторінку вниз як людина читає
            print(f"📜 Прокрутка сторінки...")
            await HumanBehavior.scroll_page_human_like(self.page, scroll_distance=500)
            
            # Парсимо вакансії на сторінці
            print(f"🔎 Початок парсингу вакансій...")
            page_jobs = await self._parse_search_results()
            jobs.extend(page_jobs)
            
            print(f"✓ Знайдено {len(page_jobs)} вакансій на сторінці {page_num}")
            
            # Перевірка чи є наступна сторінка
            has_next = await self._has_next_page()
            if not has_next:
                print("ℹ️ Досягнуто останньої сторінки результатів")
                break
            
            # Пауза між сторінками як людина
            await HumanBehavior.random_delay(2.0, 4.0)
            
        return jobs
        
    async def _parse_search_results(self) -> List[JobListing]:
        """Парсинг результатів пошуку"""
        print(f"📋 Початок _parse_search_results()")
        jobs = []
        
        # Використовуємо role selector для заголовків level=2 (це вакансії)
        try:
            # Всі заголовки h2 на сторінці - це вакансії
            print(f"🔍 Пошук заголовків h2 (role=heading, level=2)...")
            job_headings = await self.page.get_by_role('heading', level=2).all()
            print(f"✅ Знайдено {len(job_headings)} заголовків h2")
            
            for idx, heading in enumerate(job_headings, 1):
                try:
                    print(f"\n--- Обробка вакансії {idx}/{len(job_headings)} ---")
                    # Отримати посилання з заголовка
                    link = heading.locator('a').first
                    
                    if not await link.count():
                        print(f"⚠️ Немає посилання в заголовку {idx}")
                        continue
                        
                    url = await link.get_attribute('href')
                    if not url or '/jobs/' not in url:
                        print(f"⚠️ Невалідний URL: {url}")
                        continue
                        
                    if url and not url.startswith('http'):
                        url = config.WORKUA_BASE_URL + url
                    
                    title = await link.text_content()
                    print(f"✅ Вакансія: {title}")
                    print(f"🔗 URL: {url}")
                    
                    # Перевірка чи є текст "Вже відгукнулися" на картці (в parent контейнері)
                    # Піднімаємося від h2 до батьківського generic контейнера вакансії
                    parent = heading.locator('xpath=ancestor::*[contains(@class, "") or position()=1]/../..').first
                    page_text = await parent.text_content() if await parent.count() > 0 else ""
                    if "вже відгукнул" in page_text.lower():
                        print("⏭️ Вже відгукувались (знайдено на картці) - пропускаю")
                        self.applied_jobs.add(url)
                        continue
                    
                    # Спрощено - створюємо вакансію з мінімальною інформацією
                    # Деталі завантажимо пізніше при переході на вакансію
                    job = JobListing(
                        url=url,
                        title=title.strip(),
                        company="",  # Завантажимо пізніше
                        location="",  # Завантажимо пізніше
                        salary=None  # Завантажимо пізніше
                    )
                    jobs.append(job)
                    print(f"✓ Додано в список")
                    
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
            url = await link.get_attribute('href')
            if url and not url.startswith('http'):
                url = config.WORKUA_BASE_URL + url
                
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
                salary=salary.strip() if salary else None
            )
        except Exception as e:
            print(f"⚠️ Помилка витягування даних: {e}")
            return None
            
    async def _has_next_page(self) -> bool:
        """Перевірити чи є наступна сторінка"""
        try:
            # Шукаємо посилання з rel="next"
            next_link = self.page.locator('a[rel="next"]')
            return await next_link.count() > 0
        except:
            return False
        
    async def get_job_details(self, job: JobListing) -> JobListing:
        """Отримати повні деталі вакансії з людиноподібною поведінкою"""
        print(f"📄 Завантаження деталей: {job.title}")
        
        await self.page.goto(job.url)
        await self.page.wait_for_load_state('networkidle')
        await HumanBehavior.page_load_delay()
        
        # Прокрутити сторінку як людина читає
        await HumanBehavior.scroll_page_human_like(self.page, scroll_distance=400)
        
        # Опис вакансії - знаходиться в секції з заголовком "Опис вакансії"
        try:
            # Шукаємо заголовок "Опис вакансії"
            desc_heading = self.page.get_by_role('heading', name='Опис вакансії')
            # Беремо наступний елемент після заголовка
            desc_elem = desc_heading.locator('xpath=following-sibling::*[1]')
            if await desc_elem.count():
                job.description = await desc_elem.text_content()
                job.description = job.description.strip()
                # Імітація читання тексту
                await HumanBehavior.reading_delay(len(job.description))
        except:
            # Fallback - весь main
            try:
                main_elem = self.page.locator('main').first
                if await main_elem.count():
                    job.description = await main_elem.text_content()
                    job.description = job.description.strip()
            except:
                pass
            
        return job
        
    async def apply_to_job(self, job: JobListing) -> bool:
        """Відгукнутися на вакансію в новій вкладці"""
        if not self.is_logged_in:
            print("❌ Неможливо відгукнутись - немає авторизації")
            return False
        
        # Перевірити чи вже не відгукувались на цю вакансію
        if job.url in self.applied_jobs:
            print(f"⏭️ Вже відгукувались на цю вакансію раніше - пропускаю")
            return False
            
        print(f"📤 Відгук на: {job.title}")
        print(f"🔗 URL: {job.url}")
        
        # Відкриваємо вакансію в новій вкладці
        new_page = None
        try:
            print("🆕 Відкриваю нову вкладку...")
            new_page = await self.context.new_page()
            await new_page.goto(job.url)
            await new_page.wait_for_load_state('networkidle')
            await HumanBehavior.page_load_delay()
            print("✅ Вкладка відкрита")
            
            # Перевіряємо чи вже є відгук
            print("🔍 Перевірка чи є відгук...")
            
            # Спочатку шукаємо текст "ви вже відгук" на всій сторінці
            page_text = await new_page.content()
            if "ви вже відгук" in page_text.lower() or "вже відгукнул" in page_text.lower():
                print("⏭️ Знайдено текст про існуючий відгук - пропускаю")
                self.applied_jobs.add(job.url)
                await new_page.close()
                return False
            
            # Також перевіряємо кнопки
            already_applied = new_page.locator('button:has-text("Переглянути резюме"), button:has-text("Ви відгукнулись")')
            if await already_applied.count() > 0:
                print("⏭️ Знайдено кнопку про існуючий відгук - пропускаю")
                self.applied_jobs.add(job.url)
                await new_page.close()
                return False
            
            print("✓ Відгуку немає, можна подавати")
                
            # Прокрутити до опису як людина читає
            print("📜 Прокручую сторінку...")
            await HumanBehavior.scroll_page_human_like(new_page, scroll_distance=300)
            
            # Рандомна пауза як людина думає чи відгукуватися
            await HumanBehavior.random_delay(1.0, 2.5)
            
            # Клік на кнопку "Відгукнутися"
            print("🖱️ Шукаю кнопку 'Відгукнутися'...")
            apply_button = new_page.locator('button:has-text("Відгукнутися")').first
            if await apply_button.count() == 0:
                print("❌ Не знайдено кнопку 'Відгукнутися'")
                await new_page.close()
                return False
            
            # Прокрутити до кнопки
            print("📜 Прокручую до кнопки...")
            await apply_button.scroll_into_view_if_needed()
            await HumanBehavior.random_delay(0.5, 1.0)
            
            print("🖱️ Клікаю 'Відгукнутися'...")
            await HumanBehavior.click_with_human_behavior(
                new_page,
                'button:has-text("Відгукнутися")',
                scroll_into_view=True
            )
            await new_page.wait_for_load_state('networkidle')
            print("✓ Кнопка натиснута")
            
            # Чекаємо появи dialog/modal з формою
            print("⏳ Чекаю модальне вікно...")
            await HumanBehavior.random_delay(0.8, 1.5)
            
            # Перевіряємо чи з'явилось модальне вікно з вибором резюме
            # Якщо користувач залогінений, повинна з'явитись кнопка "Надіслати"
            send_button = new_page.locator('button:has-text("Надіслати"), button:has-text("Продовжити")')
            if await send_button.count() == 0:
                print("⚠️ Не знайдено кнопку відправки резюме")
                await new_page.close()
                return False
            
            print("🖱️ Клікаю 'Надіслати'...")
            await send_button.first.click()
            await new_page.wait_for_load_state('networkidle')
            print("✓ Резюме відправлено")
            
            # Може з'явитися додатковий діалог про додавання локації
            await HumanBehavior.random_delay(0.5, 1.0)
            not_add_button = new_page.locator('button:has-text("Не додавати")')
            if await not_add_button.count() > 0:
                print("🖱️ Закриваю діалог локації...")
                await not_add_button.first.click()
                await new_page.wait_for_load_state('networkidle')
            
            # Перевіряємо чи успішно відгукнулись
            await HumanBehavior.random_delay(0.5, 1.0)
            success = False
            
            # Перевіряємо різні ознаки успіху
            if '/sent/' in new_page.url:
                success = True
            elif await new_page.locator('text=успішно, text=Дякуємо, text=відгукнулись').count() > 0:
                success = True
            elif await new_page.locator('button:has-text("Переглянути резюме")').count() > 0:
                success = True
            
            if success:
                print(f"✅ Успішно відгукнулись на: {job.title}")
                self.applied_jobs.add(job.url)  # Додаємо до списку
            else:
                print(f"⚠️ Невідомий статус відгуку (можливо, все ок)")
                # Додаємо все одно - щоб не спробувати ще раз
                self.applied_jobs.add(job.url)
            
            # Закриваємо вкладку
            print("🚪 Закриваю вкладку...")
            await new_page.close()
            print("✓ Вкладка закрита\n")
            
            return success
            
        except Exception as e:
            print(f"❌ Помилка при відгуку: {e}")
            if new_page:
                try:
                    await new_page.close()
                    print("🚪 Вкладка закрита (після помилки)")
                except:
                    pass
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
            print(f"\n📝 Опис вакансії (перші 300 символів):")
            print(detailed_job.description[:300] + "...")
            
    finally:
        await scraper.close()


if __name__ == "__main__":
    print("🧪 Тестування Work.ua Scraper\n")
    asyncio.run(test_scraper())
