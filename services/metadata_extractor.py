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


def extract_metadata(text: str, vocab: dict, eln_data: dict | None = None) -> ExtractionResult:
    prompt = build_prompt(vocab, text, eln_data)

    empty: ExtractionResult = {"metadata": {}, "usage": {}}

    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise scientific metadata extractor.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format=Metadata,
            temperature=0,
        )

        validated = response.choices[0].message.parsed

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

    except Exception as e:
        logger.error("Metadata extraction failed: %s", e)
        return empty
