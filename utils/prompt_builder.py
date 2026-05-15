import json


def build_prompt(vocab: dict, text: str, eln_data: dict | None = None) -> str:
    vocab_json = json.dumps(vocab, indent=2)

    eln_section = ""
    if eln_data:
        eln_section = f"""
ELN EXPERIMENT DATA (use this alongside the file content to inform your extraction):
{json.dumps(eln_data, indent=2)}
"""

    return f"""Extract scientific metadata from the sources below.

Use ONLY values from the controlled vocabulary. If you are unsure, use null.

CONTROLLED VOCABULARY (allowed values per field):
{vocab_json}
{eln_section}
FILE CONTENT:
{text}
"""
