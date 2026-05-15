import pandas as pd
import tempfile
import xml.etree.ElementTree as ET
from typing import TypedDict, Any

from services.fcs_parser import extract_fcs_metadata, fcs_metadata_to_text


class ParsedFile(TypedDict):
    text: str
    raw: dict[str, Any]


def extract_text(uploaded_file) -> ParsedFile:

    filename = uploaded_file.name.lower()
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "unknown"
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

    elif filename.endswith(".xlsx"):
        sheets = pd.read_excel(uploaded_file, sheet_name=None)
        lines = []
        raw_sheets = {}
        for sheet_name, df in sheets.items():
            lines.append(f"Sheet: {sheet_name}")
            lines.append(df.to_string())
            lines.append("")
            raw_sheets[sheet_name] = {
                "columns": list(df.columns),
                "shape": {"rows": df.shape[0], "columns": df.shape[1]},
            }
        return {
            "text": prefix + "\n".join(lines),
            "raw": {"sheets": raw_sheets},
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

    elif filename.endswith(".pzfx"):
        return _parse_pzfx(uploaded_file, prefix)

    else:
        return _read_generic(uploaded_file, prefix, ext)


def _strip_ns(root: ET.Element) -> ET.Element:
    """Return a copy of the tree with all namespace prefixes removed from tags."""
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def _parse_pzfx(uploaded_file, prefix: str) -> ParsedFile:
    raw_bytes = uploaded_file.getvalue()
    root = _strip_ns(ET.fromstring(raw_bytes.decode("utf-8", errors="replace")))

    lines = []

    # File-level info — real data is in MostRecentVersion, not Created
    for version_tag in ("MostRecentVersion", "OriginalVersion"):
        ver = root.find(f".//{version_tag}")
        if ver is not None and ver.get("DateTime"):
            lines.append(f"{version_tag}: {ver.get('DateTime')}  login={ver.get('Login', '')}  version={ver.get('CreatedByVersion', '')}")
            break

    # Info blocks — user-fillable metadata fields (Name/Value Constants)
    for info in root.findall(".//Info"):
        info_title = info.findtext("Title") or ""
        notes = info.findtext("Notes") or ""
        constants = []
        for const in info.findall("Constant"):
            name = const.findtext("Name")
            value = const.findtext("Value")
            if name and value and value.strip():
                constants.append(f"{name}: {value}")
        if constants or (notes and notes.strip()):
            lines.append(f"\nInfo block: {info_title}")
            if notes.strip():
                lines.append(f"  Notes: {notes.strip()}")
            for c in constants:
                lines.append(f"  {c}")

    # Tables — titles and column headers only, no <d> data values
    table_names = []
    for table in root.findall(".//Table"):
        title = table.findtext("Title") or ""
        table_type = table.get("TableType", "")
        table_names.append(title)
        lines.append(f"\nTable: {title}  (type: {table_type})")

        seen_col_titles = set()
        for col in table.findall("XColumn") + table.findall("YColumn") + table.findall("XAdvancedColumn") + table.findall("RowTitlesColumn"):
            col_title = col.findtext("Title")
            if col_title and col_title.strip() and col_title not in seen_col_titles:
                seen_col_titles.add(col_title)
                lines.append(f"  Column: {col_title.strip()}")

        row_col = table.find("RowTitlesColumn")
        if row_col is not None:
            row_labels = [d.text for d in row_col.findall(".//d") if d.text and d.text.strip()]
            if row_labels:
                lines.append(f"  Row labels: {', '.join(row_labels[:20])}")

    # FloatingNotes — only include if they look like user-written content
    boilerplate = "only the values entered into column a"
    for note in root.findall(".//FloatingNote"):
        text = "".join(note.itertext()).strip()
        if text and boilerplate not in text.lower():
            lines.append(f"\nNote: {text}")

    return {
        "text": prefix + "\n".join(lines),
        "raw": {
            "prism_version": root.get("PrismXMLVersion", "unknown"),
            "tables": table_names,
        },
    }


def _read_generic(uploaded_file, prefix: str, ext: str) -> ParsedFile:
    raw_bytes = uploaded_file.getvalue()
    size_kb = round(len(raw_bytes) / 1024, 1)

    for encoding in ("utf-8", "latin-1"):
        try:
            content = raw_bytes.decode(encoding)
            return {
                "text": prefix + content,
                "raw": {"encoding": encoding, "size_kb": size_kb},
            }
        except UnicodeDecodeError:
            continue

    return {
        "text": prefix + f"[Binary file — {size_kb} KB. Content cannot be decoded as text.]",
        "raw": {"encoding": "binary", "size_kb": size_kb},
    }