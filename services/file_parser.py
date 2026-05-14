import pandas as pd
import tempfile
from typing import TypedDict, Any

from services.fcs_parser import extract_fcs_metadata, fcs_metadata_to_text


class ParsedFile(TypedDict):
    text: str
    raw: dict[str, Any]


def extract_text(uploaded_file) -> ParsedFile:

    filename = uploaded_file.name.lower()
    ext = filename.rsplit(".", 1)[-1]
    prefix = f"File Name: {uploaded_file.name}\nFile Type: {ext}\n\n"

    if filename.endswith(".txt"):
        content = uploaded_file.read().decode("utf-8")
        return {
            "text": prefix + content,
            "raw": {"content": content},
        }

    elif filename.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        return {
            "text": prefix + df.to_string(),
            "raw": {
                "columns": list(df.columns),
                "dtypes": df.dtypes.astype(str).to_dict(),
                "shape": {"rows": df.shape[0], "columns": df.shape[1]},
            },
        }

    elif filename.endswith(".fcs"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".fcs") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        meta, _ = extract_fcs_metadata(tmp_path)
        return {
            "text": prefix + fcs_metadata_to_text(meta),
            "raw": dict(meta),
        }

    return {"text": "", "raw": {}}