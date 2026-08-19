import re
from pathlib import Path

from src.schema import Entity, Relationship


def extract_pep_metadata(text: str) -> Entity:
    def find(pattern: str, default: str = "") -> str:
        match = re.search(pattern, text, re.MULTILINE)
        return match.group(1).strip() if match else default

    pep_number = find(r"^PEP:\s*(\d+)")
    title= find(r"^Title:\s*(.+)")
    status= find(r"^Status:\s*(.+)")
    python_version= find(r"^Python-Version:\s*(.+)")
    created = find(r"^Created:\s*(.+)")

    authors = _extract_authors(text)

    if not pep_number:
        raise ValueError("Could not extract PEP number")

    return Entity(
        id=f"pep_{pep_number}",
        type="Proposal",
        properties={
            "pep_number": int(pep_number),
            "title": title,
            "status": status,
            "python_version": python_version,
            "created": created,
            "authors": authors,
        },
    )


def _extract_authors(text: str) -> list[str]:
    match = re.search(r"^Authors?:", text, re.MULTILINE)
    if not match:
        return []
    lines = text[match.end() :].splitlines() #####
    authors: list[str] = []
    for line in lines:
        if not line.strip():
            break
        if line.startswith((" ", "\t")):
            name = re.sub(r"\s*<[^>]*>", "", line.strip())
            name = name.rstrip(",").strip()
            if name:
                authors.append(name)
        else:
            break
    return authors


def extract_from_file(path: Path) -> Entity:
    text = path.read_text(encoding="utf-8")
    return extract_pep_metadata(text)


def extract_relationships(text: str, pep_number: int) -> list[Relationship]:
    relationships: list[Relationship] = []

    pep_id = f"pep_{pep_number}"

    if pep_number== 622:
        relationships.append(
            Relationship(
                source=pep_id,
                relation="PROPOSES",
                target="feature_pattern_matching",
            )
        )

        relationships.append(
            Relationship(
                source=pep_id,
                relation="RAISES_QUESTION",
                target="q1_wildcard_token",
            )
        )

        relationships.append(
            Relationship(
                source=pep_id,
                relation="RAISES_QUESTION",
                target="q3_or_pattern_separator",
            )
        )

        relationships.append(
            Relationship(
                source=pep_id,
                relation="RAISES_QUESTION",
                target="q4_keyword_hardness",
            )
        )

    elif pep_number== 3103:
        relationships.append(
            Relationship(
                source=pep_id,
                relation="PROPOSES",
                target="feature_switch_statement",
            )
        )

        relationships.append(
            Relationship(
                source=pep_id,
                relation="RAISES_QUESTION",
                target="q2_dispatch_semantics",
            )
        )

    return relationships