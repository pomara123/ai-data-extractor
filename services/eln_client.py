import json
import os

ELN_DATA_DIR = "sample_files/ELN_data"


def list_experiments() -> list[dict]:
    """Return [{filename, id, title}] for all experiments in ELN_DATA_DIR."""
    result = []
    for f in sorted(os.listdir(ELN_DATA_DIR)):
        if not f.endswith(".json"):
            continue
        path = os.path.join(ELN_DATA_DIR, f)
        with open(path) as fp:
            data = json.load(fp)
        exp = data.get("experiment", {})
        result.append({
            "filename": f.replace(".json", ""),
            "id": exp.get("id", ""),
            "title": exp.get("title", f.replace(".json", "")),
        })
    return result


def get_eln_data(filename: str) -> dict:
    """Load ELN JSON by filename stem."""
    path = os.path.join(ELN_DATA_DIR, f"{filename}.json")
    with open(path) as f:
        return json.load(f)