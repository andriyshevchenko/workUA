"""LangGraph AI агент для розумного відгуку на вакансії"""
from typing import TypedDict, Annotated, List, Optional
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from scraper import JobListing, WorkUAScraper
from config import config
import json


class AgentState(TypedDict):
    """Стан агента"""
    resume_text: str  # Текст резюме користувача
    search_keywords: List[str]  # Ключові слова для пошуку
    locations: List[str]  # Локації
    found_jobs: List[JobListing]  # Знайдені вакансії
    analyzed_jobs: List[dict]  # Проаналізовані вакансії з оцінками
    applied_jobs: List[JobListing]  # Вакансії на які відгукнулись
    rejected_jobs: List[JobListing]  # Відхилені вакансії
    current_job_index: int  # Поточний індекс вакансії
    error: Optional[str]  # Помилки якщо є
    scraper: Optional[WorkUAScraper]  # Екземпляр scraper


class WorkUAAgent:
    """AI Агент для автоматичної розсилки резюме"""
    
    def __init__(self):
        self.llm = self._init_llm()
        self.graph = self._build_graph()
        
    def _init_llm(self):
        """Ініціалізувати LLM"""
        if config.OPENAI_API_KEY:
            return ChatOpenAI(
                model=config.MODEL_NAME,
                temperature=config.TEMPERATURE,
                api_key=config.OPENAI_API_KEY
            )
        else:
            raise ValueError("Потрібен OPENAI_API_KEY")
            
    def _build_graph(self) -> StateGraph:
        """Побудувати LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Додати ноди
        workflow.add_node("load_resume", self.load_resume_node)
        workflow.add_node("search_jobs", self.search_jobs_node)
        workflow.add_node("analyze_job", self.analyze_job_node)
        workflow.add_node("apply_job", self.apply_job_node)
        workflow.add_node("finalize", self.finalize_node)
        
        # Визначити потік
        workflow.add_edge(START, "load_resume")
        workflow.add_edge("load_resume", "search_jobs")
        workflow.add_edge("search_jobs", "analyze_job")
        
        # Умовний перехід після аналізу
        workflow.add_conditional_edges(
            "analyze_job",
            self.should_continue_analyzing,
            {
                "apply": "apply_job",
                "skip": "analyze_job",
                "done": "finalize"
            }
        )
        
        workflow.add_edge("apply_job", "analyze_job")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
        
    # ============ NODES ============
    
    async def load_resume_node(self, state: AgentState) -> AgentState:
        """Завантажити резюме користувача"""
        print("📄 Завантаження резюме...")
        
        # Тут можна додати читання PDF/DOCX
        # Поки що використаємо placeholder
        resume_text = """
        Досвідчений Python розробник з 3+ роками досвіду.
        Навички: Python, Django, FastAPI, PostgreSQL, Docker, AWS.
        Досвід роботи з AI/ML проектами, REST API, веб-скрапінг.
        """
        
        state["resume_text"] = resume_text
        state["current_job_index"] = 0
        state["applied_jobs"] = []
        state["rejected_jobs"] = []
        state["analyzed_jobs"] = []
        
        print("✓ Резюме завантажено")
        return state
        
    async def search_jobs_node(self, state: AgentState) -> AgentState:
        """Пошук вакансій"""
        print("🔍 Пошук вакансій...")
        
        scraper = WorkUAScraper()
        await scraper.start(headless=config.HEADLESS)
        
        # Перевірити авторизацію
        is_logged_in = await scraper.check_login_status()
        if not is_logged_in:
            print("⚠️ УВАГА: Не авторизовано. Відгуки можуть не працювати.")
            print("Запустіть explorer.py для авторизації")
            
        all_jobs = []
        
        # Пошук за кожним ключовим словом
        for keyword in state["search_keywords"]:
            if config.REMOTE_ONLY:
                # Якщо шукаємо тільки remote, ігноруємо locations
                jobs = await scraper.search_jobs(
                    keyword=keyword,
                    remote=True,
                    max_pages=2
                )
                all_jobs.extend(jobs)
            else:
                # Звичайний пошук з locations
                for location in state.get("locations", [None]):
                    jobs = await scraper.search_jobs(
                        keyword=keyword,
                        location=location,
                        max_pages=2
                    )
                    all_jobs.extend(jobs)
                
        # Видалити дублікати за URL
        unique_jobs = {job.url: job for job in all_jobs}.values()
        state["found_jobs"] = list(unique_jobs)
        state["scraper"] = scraper
        
        print(f"✓ Знайдено {len(state['found_jobs'])} унікальних вакансій")
        return state
        
    async def analyze_job_node(self, state: AgentState) -> AgentState:
        """Аналіз вакансії через LLM"""
        idx = state["current_job_index"]
        
        if idx >= len(state["found_jobs"]):
            return state
            
        job = state["found_jobs"][idx]
        print(f"\n🤔 Аналіз вакансії [{idx + 1}/{len(state['found_jobs'])}]: {job.title}")
        
        # Отримати повні деталі вакансії
        scraper = state["scraper"]
        job = await scraper.get_job_details(job)
        
        # Аналіз через LLM
        analysis = await self._llm_analyze_job(state["resume_text"], job)
        
        state["analyzed_jobs"].append({
            "job": job,
            "score": analysis["score"],
            "reason": analysis["reason"],
            "should_apply": analysis["should_apply"]
        })
        
        print(f"📊 Оцінка: {analysis['score']}/10")
        print(f"💭 Причина: {analysis['reason']}")
        
        if not analysis["should_apply"]:
            state["rejected_jobs"].append(job)
            print("❌ Вакансія не підходить - пропускаємо")
            
        return state
        
    async def apply_job_node(self, state: AgentState) -> AgentState:
        """Відгукнутися на вакансію"""
        idx = state["current_job_index"]
        job = state["found_jobs"][idx]
        
        print(f"📤 Відгук на вакансію: {job.title}")
        
        scraper = state["scraper"]
        success = await scraper.apply_to_job(job)
        
        if success:
            state["applied_jobs"].append(job)
            print("✅ Успішно відгукнулись!")
        else:
            print("❌ Не вдалося відгукнутись")
            
        return state
        
    async def finalize_node(self, state: AgentState) -> AgentState:
        """Фінальний звіт"""
        print("\n" + "="*60)
        print("📊 ФІНАЛЬНИЙ ЗВІТ")
        print("="*60)
        
        print(f"\n✅ Успішно відгукнулись: {len(state['applied_jobs'])}")
        for job in state["applied_jobs"]:
            print(f"   - {job.title} в {job.company}")
            
        print(f"\n❌ Відхилено: {len(state['rejected_jobs'])}")
        for job in state["rejected_jobs"][:5]:
            print(f"   - {job.title} в {job.company}")
            
        print(f"\n📈 Всього проаналізовано: {len(state['analyzed_jobs'])}")
        print(f"📊 Співвідношення: {len(state['applied_jobs'])}/{len(state['found_jobs'])}")
        
        # Закрити scraper
        scraper = state["scraper"]
        if scraper:
            await scraper.close()
            
        # Зберегти звіт
        self._save_report(state)
        
        return state
        
    # ============ HELPERS ============
    
    def should_continue_analyzing(self, state: AgentState) -> str:
        """Визначити наступний крок після аналізу"""
        idx = state["current_job_index"]
        
        # Перевірити чи є ще вакансії
        if idx >= len(state["found_jobs"]):
            return "done"
            
        # Отримати результат аналізу
        if state["analyzed_jobs"]:
            last_analysis = state["analyzed_jobs"][-1]
            state["current_job_index"] += 1
            
            if last_analysis["should_apply"]:
                return "apply"
            else:
                return "skip"
                
        return "done"
        
    async def _llm_analyze_job(self, resume: str, job: JobListing) -> dict:
        """Аналіз вакансії через LLM"""
        
        system_prompt = """Ти експерт з підбору вакансій. Проаналізуй наскільки вакансія підходить кандидату.

Оцініть за шкалою від 1 до 10, де:
- 1-3: Зовсім не підходить
- 4-6: Частково підходить
- 7-8: Добре підходить
- 9-10: Ідеально підходить

Відповідай ТІЛЬКИ у форматі JSON:
{
    "score": <число від 1 до 10>,
    "reason": "<коротке пояснення українською>",
    "should_apply": <true або false>
}

Критерії оцінки:
- Відповідність навичок
- Рівень досвіду
- Локація
- Тип зайнятості
"""
        
        user_prompt = f"""
РЕЗЮМЕ КАНДИДАТА:
{resume}

ВАКАНСІЯ:
Назва: {job.title}
Компанія: {job.company}
Локація: {job.location}
Зарплата: {job.salary or 'Не вказано'}
Опис: {job.description[:1000]}

Проаналізуй відповідність та дай оцінку.
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            # Парсинг JSON відповіді
            result = json.loads(response.content)
            
            # Валідація
            if not isinstance(result.get("score"), (int, float)):
                result["score"] = 5
            if not isinstance(result.get("should_apply"), bool):
                result["should_apply"] = result["score"] >= 7
                
            return result
        except json.JSONDecodeError:
            # Якщо LLM не повернув валідний JSON
            print("⚠️ Помилка парсингу відповіді LLM")
            return {
                "score": 5,
                "reason": "Не вдалося проаналізувати",
                "should_apply": False
            }
            
    def _save_report(self, state: AgentState):
        """Зберегти звіт у файл"""
        report = {
            "total_found": len(state["found_jobs"]),
            "total_analyzed": len(state["analyzed_jobs"]),
            "applied": [
                {
                    "title": job.title,
                    "company": job.company,
                    "url": job.url
                }
                for job in state["applied_jobs"]
            ],
            "rejected": [
                {
                    "title": job.title,
                    "company": job.company,
                    "score": next(
                        (a["score"] for a in state["analyzed_jobs"] if a["job"].url == job.url),
                        0
                    )
                }
                for job in state["rejected_jobs"]
            ]
        }
        
        with open("report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        print("\n💾 Звіт збережено у report.json")
        
    async def run(self, resume_text: Optional[str] = None):
        """Запустити агента"""
        initial_state = {
            "resume_text": resume_text or "",
            "search_keywords": config.SEARCH_KEYWORDS,
            "locations": config.LOCATIONS,
            "found_jobs": [],
            "analyzed_jobs": [],
            "applied_jobs": [],
            "rejected_jobs": [],
            "current_job_index": 0,
            "error": None,
            "scraper": None
        }
        
        print("🤖 Запуск AI Агента для Work.ua")
        print("="*60)
        
        final_state = await self.graph.ainvoke(initial_state)
        
        return final_state


# Тестування
async def test_agent():
    """Тест агента"""
    agent = WorkUAAgent()
    await agent.run()


if __name__ == "__main__":
    import asyncio
    print("🧪 Тестування WorkUA Agent\n")
    asyncio.run(test_agent())
