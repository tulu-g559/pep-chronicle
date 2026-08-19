from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

from src import curated
from src.extract import (
    extract_design_relationships,
    extract_pep_metadata,
    extract_pep_structure_relationships,
    extract_relationships,
)
from src.schema import Entity, KnowledgeState, Relationship, validate_knowledge

PEP_FILE_RE = re.compile(r"^pep-(\d{4})\.rst$", re.IGNORECASE)


def normalize_text(text: str) -> str:
    if text.startswith("\ufeff"):
        text = text[1:]
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def load_raw_document(path: Path) -> dict:
    match = PEP_FILE_RE.match(path.name)
    if not match:
        raise ValueError(f"not a PEP file: {path}")
    return {
        "pep_number": int(match.group(1)),
        "text": normalize_text(path.read_text(encoding="utf-8")),
    }


def load_raw_documents(input_dir: str | Path = "data/raw") -> list[dict]:
    directory = Path(input_dir)
    files = sorted(
        p for p in directory.glob("*.rst") if PEP_FILE_RE.match(p.name)
    )
    return [load_raw_document(p) for p in files]


def build_knowledge_state(input_dir: str | Path = "data/raw") -> KnowledgeState:
    """Run the full pipeline: raw RST -> extraction -> curated merge ->
    KnowledgeState, validated before returning."""
    documents = load_raw_documents(input_dir)

    proposals: list[Entity] = []
    relationships: list[Relationship] = []
    for doc in documents:
        proposals.append(extract_pep_metadata(doc["text"]))
        relationships.extend(extract_relationships(doc["text"]))
        relationships.extend(extract_design_relationships(doc["text"]))
        relationships.extend(extract_pep_structure_relationships(doc["text"]))

    for proposal in proposals:
        proposal.properties.update(
            curated.PROPERTY_OVERLAYS.get(proposal.id, {})
        )

    entities = sorted(proposals, key=lambda e: e.properties.get("pep_number", 0))
    entities.extend(
        Entity(
            id=definition["id"],
            type=definition["type"],
            properties={
                key: value
                for key, value in definition.items()
                if key not in {"id", "type"}
            },
        )
        for definition in curated.CURATED_ENTITIES
    )

    relationships.extend(
        Relationship(*triple) for triple in curated.CURATED_RELATIONSHIPS
    )

    # Deterministic ordering, then drop any accidental duplicates.
    relationships.sort(key=lambda r: (r.source, r.relation, r.target))
    seen: set[tuple[str, str, str]] = set()
    unique: list[Relationship] = []
    for relationship in relationships:
        key = (relationship.source, relationship.relation, relationship.target)
        if key not in seen:
            seen.add(key)
            unique.append(relationship)

    state = KnowledgeState(
        schema_version=curated.SCHEMA_VERSION,
        domain=curated.DOMAIN,
        entities=entities,
        relationships=unique,
    )
    validate_knowledge(state)
    return state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the canonical knowledge state from raw PEP documents"
    )
    parser.add_argument("--input", default="data/raw", help="directory of .rst files")
    parser.add_argument(
        "--output",
        default=None,
        help="write the validated KnowledgeState to this JSON file (e.g. knowledge.json)",
    )
    args = parser.parse_args(argv)

    documents = load_raw_documents(args.input)
    print(f"Loaded {len(documents)} raw PEP documents from {args.input}")
    for doc in documents:
        print(f"  PEP {doc['pep_number']}: {len(doc['text'])} chars")

    if args.output:
        state = build_knowledge_state(args.input)
        payload = {
            "schema_version": state.schema_version,
            "domain": state.domain,
            "entities": [
                {"id": entity.id, "type": entity.type, **entity.properties}
                for entity in state.entities
            ],
            "relationships": [
                {"source": rel.source, "relation": rel.relation, "target": rel.target}
                for rel in state.relationships
            ],
        }
        Path(args.output).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(
            f"Validated {len(payload['entities'])} entities, "
            f"{len(payload['relationships'])} relationships"
        )
        print(f"Wrote {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())