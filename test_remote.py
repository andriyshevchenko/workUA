"""Тест remote фільтру для Work.ua"""
import asyncio
from scraper import WorkUAScraper
from config import config


def print_section(title: str, width: int = 60):
    """Print a section header with decorative lines
    
    Args:
        title: Section title to display
        width: Width of the decorative line (default: 60)
    """
    print(f"\n{'='*width}")
    print(title)
    print(f"{'='*width}\n")


async def test_remote_search():
    """Тестуємо пошук дистанційних вакансій"""
    
    scraper = WorkUAScraper()
    await scraper.start(headless=False)
    
    print_section("🧪 ТЕСТ: Пошук ДИСТАНЦІЙНИХ вакансій (remote=True)")
    
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
    
    print_section("🧪 ТЕСТ: Пошук ЗВИЧАЙНИХ вакансій (remote=False)")
    
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
    
    print_section("✨ ТЕСТ ЗАВЕРШЕНО")


if __name__ == "__main__":
    asyncio.run(test_remote_search())
