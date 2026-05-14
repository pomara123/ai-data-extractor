import json
import re
import logging
from typing import Dict, Any

from services.openai_client import client
from utils.prompt_builder import build_prompt
from models.metadata_models import Metadata

logger = logging.getLogger(__name__)


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if the LLM adds them despite instructions."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_metadata(text: str, vocab: dict, eln_data: dict | None = None) -> Dict[str, Any]:
    """
    Call the LLM to extract metadata, validate against the Pydantic model,
    and return a plain dict. Falls back to empty dict on any failure.
    """

    prompt = build_prompt(vocab, text, eln_data)

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

        # Validate + coerce via Pydantic — unknown keys are silently dropped
        validated = Metadata(**parsed)
        return validated.model_dump(exclude_none=False)

    except json.JSONDecodeError as e:
        logger.error("LLM returned non-JSON: %s", e)
        return {}

    except Exception as e:
        logger.error("Metadata extraction failed: %s", e)
        return {}
