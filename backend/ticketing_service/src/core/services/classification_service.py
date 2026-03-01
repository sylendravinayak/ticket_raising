from dataclasses import dataclass
from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.constants.enum import Priority
from src.data.models.postgres.keyword_rule import KeywordRule
from src.constants.enum import Priority, Severity
from src.config import get_settings
import httpx
import json

settings = get_settings()


@dataclass
class ClassificationResult:
    priority: Priority
    severity: Severity
    confidence: Literal["HIGH", "LOW"]
    method: Literal["KEYWORD", "LLM", "DEFAULT"]


class ClassificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def classify(self, title: str, description: str) -> ClassificationResult:
        text = f"{title} {description}".lower()

        # 1. Keyword-based (fast path)
        result = await self.db.execute(
            select(KeywordRule).where(KeywordRule.is_active == True)
        )
        rules = result.scalars().all()

        for rule in rules:
            if any(kw.lower() in text for kw in rule.keywords):
                return ClassificationResult(
                    priority=rule.priority,
                    severity=rule.severity,
                    confidence="HIGH",
                    method="KEYWORD",
                )

        # 2. LLM fallback
        if settings.ANTHROPIC_API_KEY:
            try:
                return await self._classify_with_llm(title, description)
            except Exception:
                pass

        # 3. Default
        return ClassificationResult(
            priority=Priority.MEDIUM,
            severity=Severity.S3,
            confidence="LOW",
            method="DEFAULT",
        )

    async def _classify_with_llm(self, title: str, description: str) -> ClassificationResult:
        prompt = f"""Classify this support ticket. Respond ONLY with JSON, no extra text.

Title: {title}
Description: {description}

JSON format:
{{
  "priority": "LOW|MEDIUM|HIGH|CRITICAL",
  "severity": "S1|S2|S3|S4",
  "confidence": "HIGH|LOW"
}}

S1=system down, S2=major broken, S3=minor issue, S4=cosmetic
CRITICAL=business stopped, HIGH=major impact, MEDIUM=moderate, LOW=minor"""

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 100,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            parsed = json.loads(data["content"][0]["text"])

        return ClassificationResult(
            priority=Priority(parsed["priority"]),
            severity=Severity(parsed["severity"]),
            confidence=parsed["confidence"],
            method="LLM",
        )