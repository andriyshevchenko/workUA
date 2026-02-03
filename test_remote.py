"""Тест remote фільтра для Work.ua"""
import asyncio
from scraper import WorkUAScraper
from utils import separator_line


async def test_remote_search():
    """Тестуємо пошук дистанційних вакансій"""
    
    scraper = WorkUAScraper()
    await scraper.start(headless=False)
    
    print("\n" + separator_line())
    print("🧪 ТЕСТ: Пошук ДИСТАНЦІЙНИХ вакансій (remote=True)")
    print(separator_line() + "\n")
    
    jobs = await scraper.search_jobs(
        keyword="python developer",
        remote=True,
        max_pages=1
    )
    
    print(f"\n✅ Знайдено {len(jobs)} дистанційних вакансій:\n")
    
    for i, job in enumerate(jobs[:5], 1):  # Показуємо перші 5
        print(f"{i}. {job.title}")
        print(f"   🏢 {job.company}")
        print(f"   📍 {job.location}")
        print(f"   🔗 {job.url}")
        print()
    
    print("\n" + separator_line())
    print("🧪 ТЕСТ: Пошук ЗВИЧАЙНИХ вакансій (remote=False)")
    print(separator_line() + "\n")
    
    jobs_normal = await scraper.search_jobs(
        keyword="python developer",
        location="Київ",
        remote=False,
        max_pages=1
    )
    
    print(f"\n✅ Знайдено {len(jobs_normal)} звичайних вакансій:\n")
    
    for i, job in enumerate(jobs_normal[:5], 1):
        print(f"{i}. {job.title}")
        print(f"   🏢 {job.company}")
        print(f"   📍 {job.location}")
        print(f"   🔗 {job.url}")
        print()
    
    await scraper.close()
    
    print("\n" + separator_line())
    print("✨ ТЕСТ ЗАВЕРШЕНО")
    print(separator_line())


if __name__ == "__main__":
    asyncio.run(test_remote_search())
