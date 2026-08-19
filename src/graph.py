import json
from pathlib import Path

from src.schema import Entity, Relationship, KnowledgeState


class KnowledgeGraph:
    def __init__(self, state: KnowledgeState):
        self.state = state

        self.entities = {
            entity.id: entity
            for entity in state.entities
        }

        self.outgoing: dict[str, list[Relationship]] = {}
        self.incoming: dict[str, list[Relationship]] = {}

        for relationship in state.relationships:
            self.outgoing.setdefault(
                relationship.source, []
            ).append(relationship)

            self.incoming.setdefault(
                relationship.target, []
            ).append(relationship)

    def get_entity(self, entity_id: str) -> Entity | None:
        return self.entities.get(entity_id)

    def outgoing_relationships(
        self,
        entity_id: str,
        relation: str | None = None,
    ) -> list[Relationship]:

        relationships = self.outgoing.get(entity_id, [])

        if relation is None:
            return relationships

        return [
            r for r in relationships
            if r.relation == relation
        ]

    def incoming_relationships(
        self,
        entity_id: str,
        relation: str | None = None,
    ) -> list[Relationship]:

        relationships = self.incoming.get(entity_id, [])

        if relation is None:
            return relationships

        return [
            r for r in relationships
            if r.relation == relation
        ]


def load_knowledge(path: Path) -> KnowledgeGraph:
    data = json.loads(path.read_text(encoding="utf-8"))

    entities = [
        Entity(
            id=e["id"],
            type=e["type"],
            properties={
                key: value
                for key, value in e.items()
                if key not in {"id", "type"}
            },
        )
        for e in data["entities"]
    ]

    relationships = [
        Relationship(
            source=r["source"],
            relation=r["relation"],
            target=r["target"],
            properties={
                key: value
                for key, value in r.items()
                if key not in {"source", "relation", "target"}
            },
        )
        for r in data["relationships"]
    ]

    state = KnowledgeState(
        schema_version=data["schema_version"],
        domain=data["domain"],
        entities=entities,
        relationships=relationships,
    )

    return KnowledgeGraph(state)