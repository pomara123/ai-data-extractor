import json
from models.metadata_models import Metadata


def build_prompt(vocab: dict, text: str, eln_data: dict | None = None) -> str:
    fields = list(Metadata.model_fields.keys())
    vocab_json = json.dumps(vocab, indent=2)

    eln_section = ""
    if eln_data:
        eln_section = f"""
ELN EXPERIMENT DATA (use this alongside the file content to inform your extraction):
{json.dumps(eln_data, indent=2)}
"""

    return f"""You are a scientific metadata extraction assistant.

Your task: extract metadata from the sources below.

RULES:
1. Return ONLY a valid JSON object — no explanation, no markdown, no code fences.
2. Use ONLY values from the controlled vocabulary. If you are unsure, use null.
3. For the "marker" field, return a JSON array of strings (e.g. ["CD3", "CD4"]).
4. All other fields are strings or null.
5. Every key in the JSON must be one of the listed field names — no extras.

FIELDS TO EXTRACT:
{json.dumps(fields, indent=2)}

CONTROLLED VOCABULARY (allowed values per field):
{vocab_json}
{eln_section}
FILE CONTENT:
{text}
"""
