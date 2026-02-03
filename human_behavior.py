"""Функції для емуляції людиноподібної поведінки в браузері"""
import asyncio
import random
import math
from playwright.async_api import Page


class HumanBehavior:
    """Емуляція людської поведінки в браузері"""
    
    @staticmethod
    def _get_viewport_size(page: Page) -> dict:
        """Get viewport size with fallback to default
        
        Args:
            page: Playwright page
            
        Returns:
            Dict with 'width' and 'height' keys
        """
        viewport_size = page.viewport_size
        if viewport_size is None:
            return {'width': 1920, 'height': 1080}
        return viewport_size
    
    @staticmethod
    async def random_delay(min_seconds: float = 0.5, max_seconds: float = 2.0):
        """Рандомна затримка для емуляції людини"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    @staticmethod
    async def typing_delay():
        """Затримка між натисканнями клавіш (50-150ms)"""
        delay = random.uniform(0.05, 0.15)
        await asyncio.sleep(delay)
    
    @staticmethod
    async def reading_delay(text_length: int):
        """
        Затримка для "читання" тексту
        Приблизно 200-300 слів на хвилину = 200-300ms на слово
        """
        words = text_length / 5  # приблизно 5 символів на слово
        reading_time = words * random.uniform(0.2, 0.3)
        # Мінімум 1 секунда, максимум 10 секунд
        reading_time = max(1.0, min(10.0, reading_time))
        await asyncio.sleep(reading_time)
    
    @staticmethod
    async def page_load_delay():
        """Затримка після завантаження сторінки"""
        await asyncio.sleep(random.uniform(1.0, 3.0))
    
    @staticmethod
    def bezier_curve(t: float) -> float:
        """
        Bezier крива для плавного руху миші
        Cubic bezier (0.25, 0.1, 0.25, 1)
        """
        return 3 * (1 - t) ** 2 * t * 0.25 + 3 * (1 - t) * t ** 2 * 0.25 + t ** 3
    
    @staticmethod
    async def move_mouse_human_like(
        page: Page, 
        target_x: int, 
        target_y: int, 
        steps: int = 50
    ):
        """
        Плавний рух миші з Bezier кривою та jitter
        
        Args:
            page: Playwright page
            target_x: Цільова X координата
            target_y: Цільова Y координата  
            steps: Кількість кроків для руху
        """
        # Отримати поточну позицію (припускаємо центр екрану)
        viewport_size = HumanBehavior._get_viewport_size(page)
        
        start_x = viewport_size['width'] / 2
        start_y = viewport_size['height'] / 2
        
        for i in range(steps + 1):
            t = i / steps
            progress = HumanBehavior.bezier_curve(t)
            
            # Поточна позиція з Bezier інтерполяцією
            x = start_x + (target_x - start_x) * progress
            y = start_y + (target_y - start_y) * progress
            
            # Додати jitter (невеликі відхилення)
            jitter_x = random.uniform(-3, 3)
            jitter_y = random.uniform(-3, 3)
            
            x += jitter_x
            y += jitter_y
            
            # Переміщення миші
            await page.mouse.move(x, y)
            
            # Мікро-затримка між кроками
            await asyncio.sleep(random.uniform(0.01, 0.03))
        
        # Фінальна позиція без jitter
        await page.mouse.move(target_x, target_y)
    
    @staticmethod
    async def scroll_page_human_like(
        page: Page,
        scroll_distance: int = 300,
        direction: str = "down"
    ):
        """
        Плавне прокручування сторінки з паузами
        
        Args:
            page: Playwright page
            scroll_distance: Відстань прокручування в пікселях
            direction: 'down' або 'up'
        """
        scroll_amount = scroll_distance if direction == "down" else -scroll_distance
        steps = random.randint(3, 6)  # 3-6 кроків прокручування
        step_size = scroll_amount / steps
        
        for _ in range(steps):
            # Прокрутити частину
            await page.evaluate(f"window.scrollBy(0, {step_size})")
            # Пауза як людина
            await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Пауза після прокручування (людина читає)
        await asyncio.sleep(random.uniform(0.5, 1.5))
    
    @staticmethod
    async def click_with_human_behavior(
        page: Page,
        selector: str,
        scroll_into_view: bool = True
    ):
        """
        Клік з людиноподібною поведінкою:
        1. Прокрутити до елемента
        2. Рухати мишу до елемента
        3. Невелика пауза
        4. Клікнути
        
        Args:
            page: Playwright page
            selector: CSS selector елемента
            scroll_into_view: Чи прокручувати до елемента
        """
        element = page.locator(selector).first
        
        # Прокрутити до елемента якщо потрібно
        if scroll_into_view:
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(random.uniform(0.3, 0.7))
        
        # Отримати координати елемента
        box = await element.bounding_box()
        if box:
            # Клікнути в центр елемента з невеликим відхиленням
            center_x = box['x'] + box['width'] / 2 + random.uniform(-5, 5)
            center_y = box['y'] + box['height'] / 2 + random.uniform(-5, 5)
            
            # Плавно рухати мишу до елемента
            await HumanBehavior.move_mouse_human_like(page, center_x, center_y)
            
            # Пауза перед кліком
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Клікнути
            await element.click()
        else:
            # Якщо не вдалось отримати координати, просто клікнути
            await element.click()
    
    @staticmethod
    async def type_like_human(page: Page, selector: str, text: str):
        """
        Друкувати текст як людина з випадковими затримками
        
        Args:
            page: Playwright page
            selector: CSS selector поля вводу
            text: Текст для вводу
        """
        element = page.locator(selector).first
        await element.click()
        
        # Затримка перед початком друку
        await asyncio.sleep(random.uniform(0.2, 0.5))
        
        for char in text:
            await element.type(char)
            # Випадкова затримка між символами
            delay = random.uniform(0.05, 0.15)
            # Іноді робити довші паузи (як людина думає)
            if random.random() < 0.1:
                delay += random.uniform(0.2, 0.5)
            await asyncio.sleep(delay)
        
        # Затримка після введення
        await asyncio.sleep(random.uniform(0.3, 0.7))
    
    @staticmethod
    async def random_mouse_movement(page: Page, num_movements: int = 3):
        """
        Випадкові рухи миші по сторінці (як людина читає)
        
        Args:
            page: Playwright page
            num_movements: Кількість рухів
        """
        viewport_size = HumanBehavior._get_viewport_size(page)
        
        for _ in range(num_movements):
            # Випадкова точка в межах вікна
            x = random.randint(100, viewport_size['width'] - 100)
            y = random.randint(100, viewport_size['height'] - 100)
            
            # Плавно рухати мишу
            await HumanBehavior.move_mouse_human_like(page, x, y, steps=30)
            
            # Пауза
            await asyncio.sleep(random.uniform(0.5, 1.5))
