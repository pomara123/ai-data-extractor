from fcsparser import parse
from typing import Dict, Any, Tuple


def extract_fcs_metadata(path: str) -> Tuple[Dict[str, Any], Any]:
    meta, data = parse(path)
    return meta, data


def fcs_metadata_to_text(meta: Dict[str, Any]) -> str:
    lines = [
        f"Instrument: {meta.get('$CYT', 'unknown')}",
        f"Total Events: {meta.get('$TOT', 'unknown')}",
        f"Parameters: {meta.get('$PAR', 'unknown')}",
    ]

    channels = [
        v for k, v in meta.items()
        if k.startswith("$P") and k.endswith("N") and isinstance(v, str)
    ]
    if channels:
        lines.append("Channels: " + ", ".join(channels))

    stains = [
        v for k, v in meta.items()
        if k.startswith("$P") and k.endswith("S") and isinstance(v, str) and v.strip()
    ]
    if stains:
        lines.append("Stain Names: " + ", ".join(stains))

    return "\n".join(lines)
