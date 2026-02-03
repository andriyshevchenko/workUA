"""Playwright browser для дослідження Work.ua"""
import asyncio
from playwright.async_api import async_playwright, Page, Browser
from typing import Optional
from config import config
import json
import os


class WorkUAExplorer:
    """Клас для дослідження структури Work.ua за допомогою Playwright"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.context = None
        
    async def start(self, headless: bool = False):
        """Запустити браузер"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            slow_mo=500  # Сповільнення для кращого спостереження
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='uk-UA'
        )
        self.page = await self.context.new_page()
        print("✓ Браузер запущено")
        
    async def close(self):
        """Закрити браузер"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("✓ Браузер закрито")

    async def _navigate_and_wait(self, url: str):
        """Перейти на URL та дочекатися завантаження сторінки."""
        await self.page.goto(url)
        await self.page.wait_for_load_state('networkidle')
        
    async def save_cookies(self, filepath: str = "cookies.json"):
        """Зберегти cookies для майбутнього використання"""
        if self.context:
            cookies = await self.context.cookies()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(cookies, f)
            print(f"✓ Cookies збережено в {filepath}")
            
    async def load_cookies(self, filepath: str = "cookies.json"):
        """Завантажити збережені cookies"""
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            await self.context.add_cookies(cookies)
            print(f"✓ Cookies завантажено з {filepath}")
            return True
        return False
    
    async def explore_main_page(self):
        """Дослідити головну сторінку"""
        print("\n=== ДОСЛІДЖЕННЯ ГОЛОВНОЇ СТОРІНКИ ===")
        await self._navigate_and_wait(config.WORKUA_BASE_URL)
        
        # Зробити скріншот
        await self.page.screenshot(path='screenshots/main_page.png', full_page=True)
        print("✓ Скріншот головної сторінки збережено")
        
        # Отримати основні елементи
        title = await self.page.title()
        print(f"Заголовок: {title}")
        
        # Шукаємо кнопку входу
        login_button = await self.page.query_selector('a[href*="login"]')
        if login_button:
            text = await login_button.text_content()
            print(f"Знайдено кнопку входу: '{text.strip()}'")
            
    async def explore_login_page(self):
        """Дослідити сторінку логіну"""
        print("\n=== ДОСЛІДЖЕННЯ СТОРІНКИ ЛОГІНУ ===")
        
        # Перейти на сторінку логіну через кнопку
        await self._navigate_and_wait(config.WORKUA_BASE_URL)
        
        # Клік на "Увійти" використовуючи role selector
        login_link = self.page.get_by_role('link', name='Увійти')
        await login_link.click()
        await self.page.wait_for_load_state('networkidle')
        
        await self.page.screenshot(path='screenshots/login_page.png', full_page=True)
        print("✓ Скріншот сторінки логіну збережено")
        
        # Знайти поле телефону через textbox role
        phone_field = self.page.get_by_role('textbox')
        login_button = self.page.get_by_role('button', name='Увійти')
        
        print(f"✓ Знайдено поле для номера телефону")
        print(f"✓ Знайдено кнопку 'Увійти'")
            
        print("\n⚠️ Браузер відкритий для дослідження")
        print("Структура авторизації: номер телефону -> SMS код")
    
    async def auto_login(self):
        """Автоматична авторизація через номер телефону"""
        print("\n=== АВТОМАТИЧНА АВТОРИЗАЦІЯ ===")
        
        if not config.WORKUA_PHONE:
            print("❌ WORKUA_PHONE не налаштовано в .env")
            print("Додайте: WORKUA_PHONE=+380XXXXXXXXX")
            return False
            
        # Перейти на головну
        await self._navigate_and_wait(config.WORKUA_BASE_URL)
        
        # Клік на "Увійти"
        print("📱 Натискаю 'Увійти'...")
        login_link = self.page.get_by_role('link', name='Увійти')
        await login_link.click()
        await self.page.wait_for_load_state('networkidle')
        
        # Ввести номер телефону
        print(f"📱 Вводжу номер телефону: {config.WORKUA_PHONE}")
        phone_field = self.page.get_by_role('textbox')
        await phone_field.clear()
        await phone_field.fill(config.WORKUA_PHONE)
        
        # Натиснути "Увійти"
        print("📱 Натискаю кнопку 'Увійти'...")
        login_button = self.page.get_by_role('button', name='Увійти')
        await login_button.click()
        
        # Чекаємо на SMS код від користувача
        print("\n" + "="*60)
        print("⏳ ОЧІКУВАННЯ SMS КОДУ")
        print("="*60)
        print("📱 SMS код надіслано на ваш телефон")
        print("\n👉 ВВЕДІТЬ КОД НА САЙТІ та натисніть 'Увійти'")
        print("\nЯ чекаю 120 секунд...\n")
        
        # Чекаємо поки користувач введе код і авторизується
        try:
            # Чекаємо поки URL зміниться (успішний логін)
            await self.page.wait_for_url(lambda url: 'login' not in url.lower(), timeout=120000)
            print("\n✅ АВТОРИЗАЦІЯ УСПІШНА!")
            await self.save_cookies()
            return True
        except:
            print("\n⏱️ Час вийшов або авторизація не пройшла")
            current_url = self.page.url
            if "login" not in current_url.lower():
                print("✅ Схоже авторизація все ж пройшла!")
                await self.save_cookies()
                return True
            return False
        
    async def manual_login_wait(self):
        """Чекати на ручну авторизацію користувача"""
        print("\n=== ОЧІКУВАННЯ РУЧНОЇ АВТОРИЗАЦІЇ ===")
        await self.explore_login_page()
        
        # Чекаємо на підтвердження
        await asyncio.sleep(60)  # Даємо 60 секунд на авторизацію
        
        # Перевіряємо чи авторизувались
        current_url = self.page.url
        if "login" not in current_url.lower():
            print("✓ Схоже, авторизація успішна!")
            await self.save_cookies()
            return True
        else:
            print("⚠️ Схоже, авторизація не пройшла")
            return False
            
    async def explore_search_page(self, keyword: str = "python developer"):
        """Дослідити сторінку пошуку вакансій"""
        print(f"\n=== ДОСЛІДЖЕННЯ ПОШУКУ: '{keyword}' ===")
        
        # Формуємо URL пошуку
        search_url = f"{config.WORKUA_SEARCH_URL}?search={keyword.replace(' ', '+')}"
        await self._navigate_and_wait(search_url)
        
        await self.page.screenshot(path='screenshots/search_page.png', full_page=True)
        print("✓ Скріншот сторінки пошуку збережено")
        
        # Знайти вакансії на сторінці
        jobs = await self.page.query_selector_all('.card.card-hover, .job-link, [class*="vacancy"]')
        print(f"✓ Знайдено елементів вакансій: {len(jobs)}")
        
        # Аналізувати перші 3 вакансії
        for i, job in enumerate(jobs[:3]):
            print(f"\n--- Вакансія {i+1} ---")
            
            # Заголовок
            title_elem = await job.query_selector('h2, .card-title, [class*="title"]')
            if title_elem:
                title = await title_elem.text_content()
                print(f"Назва: {title.strip()}")
            
            # Компанія
            company_elem = await job.query_selector('[class*="company"], [class*="employer"]')
            if company_elem:
                company = await company_elem.text_content()
                print(f"Компанія: {company.strip()}")
                
            # Локація
            location_elem = await job.query_selector('[class*="location"], [class*="city"]')
            if location_elem:
                location = await location_elem.text_content()
                print(f"Локація: {location.strip()}")
                
    async def explore_job_page(self):
        """Дослідити сторінку конкретної вакансії"""
        print("\n=== ДОСЛІДЖЕННЯ СТОРІНКИ ВАКАНСІЇ ===")
        
        # Спочатку йдемо на пошук
        search_url = f"{config.WORKUA_SEARCH_URL}?search=python+developer"
        await self._navigate_and_wait(search_url)
        
        # Клікаємо на першу вакансію
        first_job = await self.page.query_selector('.card.card-hover a, .job-link')
        if first_job:
            await first_job.click()
            await self.page.wait_for_load_state('networkidle')
            
            await self.page.screenshot(path='screenshots/job_page.png', full_page=True)
            print("✓ Скріншот сторінки вакансії збережено")
            
            # Шукаємо кнопку відгуку
            apply_button = await self.page.query_selector('button:has-text("Відгукнутись"), a:has-text("Відгукнутись"), [class*="respond"], [class*="apply"]')
            if apply_button:
                button_text = await apply_button.text_content()
                print(f"✓ Знайдено кнопку відгуку: '{button_text.strip()}'")
                
            # Отримати опис вакансії
            description = await self.page.query_selector('[class*="description"], .card-body, [class*="content"]')
            if description:
                desc_text = await description.text_content()
                print(f"Опис (перші 200 символів): {desc_text.strip()[:200]}...")
                
    async def full_exploration(self):
        """Повне дослідження сайту"""
        try:
            # Створити папку для скріншотів
            os.makedirs('screenshots', exist_ok=True)
            
            await self.start(headless=config.HEADLESS)
            
            await self.explore_main_page()
            await asyncio.sleep(2)
            
            # Спробувати завантажити збережені cookies
            cookies_loaded = await self.load_cookies()
            
            if not cookies_loaded:
                print("\n🔐 Потрібна авторизація для повного доступу")
                success = await self.auto_login()
                if not success:
                    print("\n⚠️ Авторизація не пройшла")
                    print("Перевірте номер телефону в .env: WORKUA_PHONE=+380XXXXXXXXX")
                    return
            
            await self.explore_search_page("python developer")
            await asyncio.sleep(2)
            
            await self.explore_job_page()
            await asyncio.sleep(2)
            
            print("\n✅ Дослідження завершено!")
            print("Перегляньте папку 'screenshots' для збережених зображень")
            
            # Залишаємо браузер відкритим для ручного огляду
            if not config.HEADLESS:
                print("\n⏸️ Браузер залишено відкритим для огляду")
                print("Натисніть Enter для завершення...")
                await asyncio.sleep(30)
            
        except Exception as e:
            print(f"❌ Помилка: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.close()


async def main():
    """Головна функція для запуску дослідження"""
    explorer = WorkUAExplorer()
    await explorer.full_exploration()


if __name__ == "__main__":
    print("🔍 Запуск дослідження Work.ua з Playwright...")
    print("=" * 60)
    asyncio.run(main())
