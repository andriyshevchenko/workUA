"""Тест процесу відгуку на вакансію"""
import asyncio
from scraper import WorkUAScraper, JobListing
from config import config


async def test_apply_workflow():
    """Тестуємо повний процес відгуку на вакансію"""
    
    scraper = WorkUAScraper()
    await scraper.start(headless=False)
    
    # Перевірка авторизації
    is_logged_in = await scraper.check_login_status()
    print(f"\n{'='*60}")
    print(f"Статус авторизації: {'✅ Авторизовано' if is_logged_in else '❌ Не авторизовано'}")
    print(f"{'='*60}\n")
    
    if not is_logged_in:
        print("⚠️ Потрібна авторизація. Запустіть explorer.py спочатку.")
        await scraper.close()
        return
    
    # Шукаємо remote вакансії
    print("🔍 Пошук дистанційних вакансій...\n")
    jobs = await scraper.search_jobs(
        keyword="python developer",
        remote=True,
        max_pages=1
    )
    
    if not jobs:
        print("❌ Не знайдено вакансій")
        await scraper.close()
        return
    
    # Беремо першу вакансію для тесту
    test_job = jobs[0]
    print(f"\n{'='*60}")
    print(f"📋 Тестова вакансія:")
    print(f"   Назва: {test_job.title}")
    print(f"   Компанія: {test_job.company}")
    print(f"   Локація: {test_job.location}")
    print(f"   URL: {test_job.url}")
    print(f"{'='*60}\n")
    
    # Завантажуємо деталі
    print("📄 Завантаження деталей вакансії...\n")
    test_job = await scraper.get_job_details(test_job)
    
    # Показуємо частину опису
    if test_job.description:
        desc_preview = test_job.description[:200] + "..."
        print(f"📝 Опис (перші 200 символів):\n{desc_preview}\n")
    
    # Питаємо користувача чи відгукуватися
    print(f"{'='*60}")
    response = input("❓ Відгукнутися на цю вакансію? (y/n): ")
    print(f"{'='*60}\n")
    
    if response.lower() == 'y':
        print("🚀 Починаємо процес відгуку...\n")
        success = await scraper.apply_to_job(test_job)
        
        if success:
            print(f"\n{'='*60}")
            print("🎉 ТЕСТ УСПІШНИЙ! Відгук надіслано!")
            print(f"{'='*60}\n")
        else:
            print(f"\n{'='*60}")
            print("❌ ТЕСТ ПРОВАЛЕНИЙ! Не вдалось надіслати відгук")
            print(f"{'='*60}\n")
    else:
        print("⏭️ Пропускаємо відгук (тест не виконано)\n")
    
    # Чекаємо трохи перед закриттям щоб побачити результат
    print("⏳ Чекаємо 5 секунд перед закриттям...")
    await asyncio.sleep(5)
    
    await scraper.close()
    print("\n✅ Тест завершено")


if __name__ == "__main__":
    asyncio.run(test_apply_workflow())
