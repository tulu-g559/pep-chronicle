from dataclasses import dataclass, field
from typing import Any


@dataclass
class Entity:
    id: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Relationship:
    source: str
    relation: str
    target: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeState:
    schema_version: str
    domain: str
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)


def validate_knowledge(state: KnowledgeState) -> None:
    entity_ids = {entity.id for entity in state.entities}

    if len(entity_ids) != len(state.entities):
        raise ValueError("Duplicate entity IDs found")

    for relationship in state.relationships:
        if relationship.source not in entity_ids:
            raise ValueError(
                f"Unknown relationship source: {relationship.source}"
            )

        if relationship.target not in entity_ids:
            raise ValueError(
                f"Unknown relationship target: {relationship.target}"
            )