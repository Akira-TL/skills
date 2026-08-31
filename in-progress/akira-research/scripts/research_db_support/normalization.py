from __future__ import annotations


def clean_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_doi(value: object) -> str | None:
    text = clean_optional_text(value)
    if text is None:
        return None
    lowered = text.lower()
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    ):
        if lowered.startswith(prefix):
            lowered = lowered[len(prefix) :].strip()
            break
    return lowered or None


def normalize_identifier(value: object) -> str | None:
    return clean_optional_text(value)
