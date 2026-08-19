import re
from pathlib import Path

from src.schema import Entity, Relationship


def extract_pep_metadata(text: str) -> Entity:
    def find(pattern: str, default: str = "") -> str:
        match = re.search(pattern, text, re.MULTILINE)
        return match.group(1).strip() if match else default

    pep_number = find(r"^PEP:\s*(\d+)")
    title = find(r"^Title:\s*(.+)")
    status = find(r"^Status:\s*(.+)")
    python_version = find(r"^Python-Version:\s*(.+)")
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
    lines = text[match.end() :].splitlines()
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


def _norm(text: str) -> str:
    text = text.replace("`", "")
    return re.sub(r"\s+", " ", text).strip().lower()


def _matches(body: str, phrases: tuple[str, ...]) -> bool:
    normalized = _norm(body)
    return all(phrase in normalized for phrase in phrases)


def _parse_sections(text: str) -> dict[str, str]: ### commit: parse_seciton before graph
    lines = text.split("\n")
    headers: list[int] = []
    for i in range(len(lines) - 1):
        if not lines[i].strip():
            continue
        if lines[i + 1] and re.fullmatch(r"[=\-~^+*#\"']{3,}", lines[i + 1]):
            headers.append(i)
    sections: dict[str, str] = {}
    for k, pos in enumerate(headers):
        end = headers[k + 1] if k + 1 < len(headers) else len(lines)
        sections[_norm(lines[pos])] = "\n".join(lines[pos + 2 : end])
    return sections


def _find_section(sections: dict[str, str], *keys: str) -> str | None:
    for title, body in sections.items():
        if any(k in title for k in keys):
            return body
    return None


def _pep_number_from_text(text: str) -> int:
    match = re.search(r"^PEP:\s*(\d+)", text, re.MULTILINE)
    if not match:
        raise ValueError("Could not extract PEP number")
    return int(match.group(1))


# (section title keys, required phrases, relation, target)
_PROPOSAL_RULES: list[tuple[tuple[str, ...], tuple[str, ...], str, str]] = [
    (
        ("abstract",),
        ("pattern matching statement",),
        "PROPOSES",
        "feature_pattern_matching",
    ),
    (("abstract",), ("switch statement",), "PROPOSES", "feature_switch_statement"),
    (
        ("some other token as wildcard",),
        ("ellipsis token",),
        "RAISES_QUESTION",
        "q1_wildcard_token",
    ),
    (
        ("instead of | for or patterns",),
        ("or keyword",),
        "RAISES_QUESTION",
        "q3_or_pattern_separator",
    ),
    (
        ("use a hard keyword",),
        ("hard keyword",),
        "RAISES_QUESTION",
        "q4_keyword_hardness",
    ),
    (
        ("dict-based dispatch",),
        ("schools of thought",),
        "RAISES_QUESTION",
        "q2_dispatch_semantics",
    ),
]


# A question's whole chain is emitted only if its discussion section exists
# in the document and contains the listed supporting phrases.
_DESIGN_CHAIN_RULES: list[dict] = [
    {
        "question": "q1_wildcard_token",
        "section_keys": ("some other token as wildcard",),
        "options": {
            "opt_q1_underscore": ("is already used as a throwaway target",),
            "opt_q1_ellipsis": ("ellipsis token",),
            "opt_q1_question_mark": ("another proposal was to use",),
        },
        "objections": [
            (
                "opt_q1_ellipsis",
                "obj_q1_ellipsis",
                ("more confusing in documentation",),
            ),
            (
                "opt_q1_question_mark",
                "obj_q1_question_mark",
                ("modifying the tokenizer",),
            ),
        ],
        "decision": {
            "id": "d1",
            "chose": "opt_q1_underscore",
            "chose_section_keys": ("wildcard pattern",),
            "chose_phrases": ("single underscore",),
            "rejected": {
                "opt_q1_ellipsis": ("ellipsis token",),
                "opt_q1_question_mark": ("modifying the tokenizer",),
            },
        },
    },
    {
        "question": "q2_dispatch_semantics",
        "section_keys": ("dict-based dispatch",),
        "options": {
            "opt_q2_if_elif": ("school i",),
            "opt_q2_dict_dispatch": ("school ii",),
        },
        "objections": [
            (
                "opt_q2_dict_dispatch",
                "obj_q2_dict_dispatch",
                ("optimized and unoptimized code may behave differently",),
            ),
        ],
        "decision": {
            "id": "d2",
            "chose": "opt_q2_dict_dispatch",
            "chose_section_keys": ("dict-based dispatch",),
            "chose_phrases": ("school ii",),
            "rejected": {
                "opt_q2_if_elif": ("my main objection against this school",),
            },
        },
    },
]


def extract_relationships(
    text: str, pep_number: int | None = None
) -> list[Relationship]:
    if pep_number is None:
        pep_number = _pep_number_from_text(text)
    pep_id = f"pep_{pep_number}"
    relationships: list[Relationship] = []
    sections = _parse_sections(text)

    for section_keys, phrases, relation, target in _PROPOSAL_RULES:
        body = _find_section(sections, *section_keys)
        if body is None or not _matches(body, phrases):
            continue
        relationships.append(Relationship(pep_id, relation, target))

    return relationships


def extract_design_relationships(
    text: str, pep_number: int | None = None
) -> list[Relationship]:
    if pep_number is None:
        pep_number = _pep_number_from_text(text)
    pep_id = f"pep_{pep_number}"
    relationships: list[Relationship] = []
    sections = _parse_sections(text)

    for rule in _DESIGN_CHAIN_RULES:
        body = _find_section(sections, *rule["section_keys"])
        if body is None:
            continue
        question = rule["question"]

        for option_id, phrases in rule["options"].items():
            if _matches(body, phrases):
                relationships.append(Relationship(question, "HAS_OPTION", option_id))

        for option_id, objection_id, phrases in rule["objections"]:
            if _matches(body, phrases):
                relationships.append(
                    Relationship(option_id, "HAS_OBJECTION", objection_id)
                )
                relationships.append(
                    Relationship(objection_id, "RAISED_IN", pep_id)
                )

        decision = rule["decision"]
        chose_body = _find_section(sections, *decision["chose_section_keys"])
        if chose_body is not None and _matches(chose_body, decision["chose_phrases"]):
            relationships.append(Relationship(question, "RESOLVED_BY", decision["id"]))
            relationships.append(
                Relationship(decision["id"], "CHOSE", decision["chose"])
            )
        for rejected_id, phrases in decision["rejected"].items():
            if _matches(body, phrases):
                relationships.append(
                    Relationship(decision["id"], "REJECTED", rejected_id)
                )

    return relationships