"""Головний файл для запуску AI агента Work.ua"""
import asyncio
import argparse
from agent import WorkUAAgent
from config import config
import sys


async def main(demo: bool = False, verbose: bool = False):
    """Головна функція"""
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║         🤖 Work.ua AI Agent - Розумна розсилка резюме      ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Валідація конфігурації
    try:
        config.validate()
    except ValueError as e:
        print(f"❌ Помилка конфігурації: {e}")
        print("\n💡 Підказка: Додайте API ключ в .env файл")
        print("   OPENAI_API_KEY=sk-your-key")
        print("   або")
        print("   ANTHROPIC_API_KEY=sk-ant-your-key")
        sys.exit(1)
        
    print("📋 Налаштування:")
    print(f"   Ключові слова: {', '.join(config.SEARCH_KEYWORDS)}")
    print(f"   Локації: {', '.join(config.LOCATIONS)}")
    print(f"   Модель: {config.MODEL_NAME}")
    print(f"   Headless: {config.HEADLESS}")
    
    if demo:
        print("\n🎮 DEMO режим: Буде проаналізовано лише перші 5 вакансій")
        # Обмежити кількість вакансій в demo режимі
        # Можна додати логіку обмеження
        
    print("\n" + "="*60)
    
    # Створити та запустити агента
    agent = WorkUAAgent()
    
    try:
        await agent.run()
        print("\n✅ Агент завершив роботу успішно!")
        
    except KeyboardInterrupt:
        print("\n\n⏸️ Робота агента перервана користувачем")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Критична помилка: {e}")
        import traceback
        if verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI агент для автоматичної розсилки резюме на Work.ua"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Запустити в demo режимі (обмежена кількість вакансій)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Детальні логи та помилки"
    )
    
    args = parser.parse_args()
    
    # Запуск
    asyncio.run(main(demo=args.demo, verbose=args.verbose))
