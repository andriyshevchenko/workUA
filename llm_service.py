"""Service for LLM-based job analysis"""
import json
import logging
import re
from typing import Optional, Tuple
from openai import OpenAI
from config import config


class LLMAnalysisService:
    """Service for analyzing job listings using LLM"""

    def __init__(self):
        """Initialize the LLM analysis service"""
        self.logger = logging.getLogger(__name__)
        self.client: Optional[OpenAI] = None
        self.use_llm = False
        self.resume_text = ""

        if config.OPENAI_API_KEY and hasattr(config, 'USE_LLM') and config.USE_LLM:
            try:
                self.client = OpenAI(api_key=config.OPENAI_API_KEY)
                self.use_llm = True
                self.logger.info("✅ LLM analysis enabled (GPT-4o)")
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to initialize OpenAI: {e}")
                self.use_llm = False
        else:
            self.logger.info("ℹ️ LLM analysis disabled - brute force mode")

    def load_resume(self, resume_path: str) -> str:
        """Load user resume from file
        
        Args:
            resume_path: Path to resume file
            
        Returns:
            Resume text content or fallback text
        """
        try:
            with open(resume_path, 'r', encoding='utf-8') as f:
                resume_text = f.read()
            self.resume_text = resume_text
            return resume_text
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to load resume: {e}")
            # Fallback to short description
            fallback_resume = """
            Sales Manager with B2B experience.
            
            Experience:
            - Active B2B sales (IT solutions, SaaS)
            - Cold contacts and warm leads
            - SPIN selling, objection handling
            - CRM, Binotel, Bitrix24
            
            Looking for: Sales Manager position
            Location: Remote
            """
            self.resume_text = fallback_resume
            return fallback_resume

    def analyze_job(
        self,
        job_title: str,
        company: str,
        location: str,
        salary: Optional[str],
        description: str,
    ) -> Tuple[bool, int, str]:
        """Analyze if a job matches the candidate's profile
        
        Args:
            job_title: Job title
            company: Company name
            location: Job location
            salary: Salary information
            description: Job description
            
        Returns:
            Tuple of (should_apply, score, reason)
        """
        if not self.use_llm:
            # Brute force - all jobs are suitable
            return True, 10, "Brute force mode - applying to all"

        try:
            prompt = self._build_analysis_prompt(
                job_title, company, location, salary, description
            )

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an HR analyst. Respond in JSON format.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            score = result.get("score", 0)
            reason = result.get("reason", "")

            # Threshold for applying (can be in config)
            min_score = getattr(config, 'MIN_SCORE', 7)
            should_apply = score >= min_score

            return should_apply, score, reason

        except Exception as e:
            self.logger.error(f"❌ LLM analysis error: {e}")
            # If LLM fails - skip the job
            return False, 0, f"Analysis error: {e}"

    def _build_analysis_prompt(
        self,
        job_title: str,
        company: str,
        location: str,
        salary: Optional[str],
        description: str,
    ) -> str:
        """Build the analysis prompt for LLM
        
        Args:
            job_title: Job title
            company: Company name
            location: Job location
            salary: Salary information
            description: Job description
            
        Returns:
            Formatted prompt string
        """
        return f"""You are an HR assistant. Analyze if this job matches the candidate.

CANDIDATE RESUME:
{self.resume_text}

JOB POSTING:
Title: {job_title}
Company: {company}
Location: {location}
Salary: {salary or 'Not specified'}
Description: {description[:1000] if description else 'No description'}

TASK:
1. Rate the match from 1 to 10 (10 = perfect match)
2. Explain why

RESPONSE FORMAT (JSON):
{{
  "score": 8,
  "reason": "Brief explanation (1-2 sentences)"
}}
"""

    def analyze_job_match(self, job_description: str) -> Tuple[int, str]:
        """Analyze job match probability with LLM
        
        Args:
            job_description: Full job description text
            
        Returns:
            Tuple of (probability 0-100%, explanation)
        """
        if not self.use_llm or not self.client:
            return 50, "LLM analysis not available"

        try:
            prompt = f"""Analyze how well my resume matches this job posting.

MY RESUME:
{self.resume_text}

JOB DESCRIPTION:
{job_description}

Provide your answer in the format:
PROBABILITY: [number from 0 to 100]%
EXPLANATION: [brief explanation why this probability]

Consider:
- Skills and experience match
- Education requirements match
- Language requirements match
- Whether experience can compensate for missing formal requirements
"""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an HR expert and resume analyst.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )

            result = response.choices[0].message.content

            # Parse the response
            probability_match = re.search(r'PROBABILITY:\s*(\d+)', result)
            explanation_match = re.search(r'EXPLANATION:\s*(.+)', result, re.DOTALL)

            if probability_match:
                probability = int(probability_match.group(1))
                explanation = (
                    explanation_match.group(1).strip()
                    if explanation_match
                    else result
                )
                return probability, explanation
            else:
                # If parsing failed, return default values
                return 50, result

        except Exception as e:
            self.logger.error(f"⚠️ LLM analysis error: {e}")
            return 50, f"Analysis error: {e}"
