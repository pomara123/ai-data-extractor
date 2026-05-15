import json
import re
import logging
from typing import Dict, Any, TypedDict

from services.openai_client import client
from utils.prompt_builder import build_prompt
from models.metadata_models import Metadata

logger = logging.getLogger(__name__)

# gpt-4.1-mini pricing (USD per 1M tokens)
_PRICE_INPUT_PER_M  = 0.40
_PRICE_OUTPUT_PER_M = 1.60


class ExtractionResult(TypedDict):
    metadata: Dict[str, Any]
    usage: Dict[str, Any]


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_metadata(text: str, vocab: dict, eln_data: dict | None = None) -> ExtractionResult:
    prompt = build_prompt(vocab, text, eln_data)

    empty: ExtractionResult = {"metadata": {}, "usage": {}}

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise scientific metadata extractor. "
                        "Always return valid JSON only — no prose, no markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )

        raw = response.choices[0].message.content
        cleaned = _strip_fences(raw)
        parsed = json.loads(cleaned)

        validated = Metadata(**parsed)

        usage = response.usage
        prompt_tokens     = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        cost = (
            prompt_tokens     / 1_000_000 * _PRICE_INPUT_PER_M +
            completion_tokens / 1_000_000 * _PRICE_OUTPUT_PER_M
        )

        return {
            "metadata": validated.model_dump(exclude_none=False),
            "usage": {
                "prompt_tokens":     prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens":      usage.total_tokens,
                "cost_usd":          round(cost, 6),
            },
        }

    except json.JSONDecodeError as e:
        logger.error("LLM returned non-JSON: %s", e)
        return empty

    except Exception as e:
        logger.error("Metadata extraction failed: %s", e)
        return empty