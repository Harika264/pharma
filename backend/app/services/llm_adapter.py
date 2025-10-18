import hashlib
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import httpx
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings
from app.utils.cache import cache_manager
from app.models.schemas import Reference
import logging

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    BOLT = "bolt"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class GroundingChecker:
    @staticmethod
    def check_grounding(text: str, references: List[Reference]) -> Tuple[bool, float]:
        if not references or len(references) == 0:
            return False, 0.2

        evidence_count = sum(1 for ref in references if ref.evidence_found)
        if evidence_count == 0:
            return False, 0.2

        confidence = min(0.5 + (evidence_count * 0.1), 0.95)
        return True, confidence

    @staticmethod
    def annotate_claims(text: str, references: List[Reference]) -> Dict[str, Any]:
        is_grounded, confidence = GroundingChecker.check_grounding(text, references)

        return {
            "text": text,
            "is_grounded": is_grounded,
            "confidence": confidence,
            "references": [ref.dict() for ref in references],
            "annotation": "verified" if is_grounded else "no_evidence_found"
        }


class LLMAdapter:
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self.bolt_endpoint = settings.BOLT_LLM_ENDPOINT
        self.bolt_api_key = settings.BOLT_LLM_API_KEY

        if settings.OPENAI_API_KEY:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        if settings.ANTHROPIC_API_KEY:
            self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        self.grounding_checker = GroundingChecker()

    def _compute_prompt_hash(self, prompt: str, model: str) -> str:
        content = f"{prompt}:{model}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _should_use_bolt(self, sensitive: bool, has_internal_docs: bool, content_type: Optional[str] = None) -> bool:
        if sensitive or has_internal_docs:
            return True

        if content_type == "internal_doc":
            return True

        return False

    async def _get_cached_response(self, prompt_hash: str) -> Optional[Dict[str, Any]]:
        if not settings.CACHE_ENABLED:
            return None

        cached = await cache_manager.get(f"llm:{prompt_hash}")
        return cached

    async def _cache_response(self, prompt_hash: str, response: Dict[str, Any]):
        if not settings.CACHE_ENABLED:
            return

        await cache_manager.set(f"llm:{prompt_hash}", response, ttl=settings.CACHE_TTL_SECONDS)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _call_bolt_llm(self, prompt: str, model: str = "bolt-default") -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            response = await client.post(
                f"{self.bolt_endpoint}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.bolt_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
            )
            response.raise_for_status()
            return response.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _call_openai(self, prompt: str, model: str = "gpt-4-turbo-preview") -> Dict[str, Any]:
        if not self.openai_client:
            raise ValueError("OpenAI client not configured")

        response = await self.openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )

        return {
            "choices": [{
                "message": {
                    "content": response.choices[0].message.content
                }
            }],
            "usage": {
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _call_anthropic(self, prompt: str, model: str = "claude-3-sonnet-20240229") -> Dict[str, Any]:
        if not self.anthropic_client:
            raise ValueError("Anthropic client not configured")

        response = await self.anthropic_client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "choices": [{
                "message": {
                    "content": response.content[0].text
                }
            }],
            "usage": {
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }
        }

    async def generate(
        self,
        prompt: str,
        sensitive: bool = False,
        has_internal_docs: bool = False,
        content_type: Optional[str] = None,
        references: Optional[List[Reference]] = None,
        preferred_provider: Optional[LLMProvider] = None
    ) -> Dict[str, Any]:
        start_time = time.time()

        use_bolt = self._should_use_bolt(sensitive, has_internal_docs, content_type)

        if use_bolt:
            provider = LLMProvider.BOLT
        elif preferred_provider:
            provider = preferred_provider
        else:
            provider = LLMProvider(settings.DEFAULT_LLM_PROVIDER)

        prompt_hash = self._compute_prompt_hash(prompt, provider.value)

        cached_response = await self._get_cached_response(prompt_hash)
        if cached_response:
            logger.info(f"Cache hit for prompt_hash: {prompt_hash}")
            return {
                **cached_response,
                "cache_hit": True,
                "provider": provider.value
            }

        try:
            if provider == LLMProvider.BOLT:
                response = await self._call_bolt_llm(prompt)
            elif provider == LLMProvider.OPENAI:
                try:
                    response = await self._call_openai(prompt)
                except Exception as e:
                    logger.warning(f"OpenAI failed, falling back to Anthropic: {e}")
                    if self.anthropic_client:
                        response = await self._call_anthropic(prompt)
                        provider = LLMProvider.ANTHROPIC
                    else:
                        raise
            elif provider == LLMProvider.ANTHROPIC:
                response = await self._call_anthropic(prompt)
            else:
                raise ValueError(f"Unknown provider: {provider}")

            content = response["choices"][0]["message"]["content"]

            if references:
                grounding_result = self.grounding_checker.annotate_claims(content, references)
            else:
                grounding_result = self.grounding_checker.annotate_claims(content, [])

            result = {
                "content": content,
                "grounding": grounding_result,
                "provider": provider.value,
                "tokens_used": response.get("usage", {}).get("total_tokens", 0),
                "response_time_ms": int((time.time() - start_time) * 1000),
                "cache_hit": False,
                "prompt_hash": prompt_hash
            }

            await self._cache_response(prompt_hash, result)

            return result

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise


llm_adapter = LLMAdapter()
