import re

from src.graph import KnowledgeGraph
from src.schema import Entity

QUESTION_SIGNALS = {
    "q1_wildcard_token": {
        "wildcard",
        "underscore",
        "placeholder",
        "ignore value",
        "throwaway",
    },
    "q2_dispatch_semantics": {
        "switch",
        "dispatch",
        "lookup",
        "precompute",
        "jump table",
        "elif chain",
        "if/elif",
    },
    "q3_or_pattern_separator": {
        "or pattern",
        "alternative pattern",
        "pattern separator",
        "separator",
        "nested pattern",
        "fall-through",
        "stacked case",
    },
    "q4_keyword_hardness": {
        "keyword",
        "reserved word",
        "identifier",
        "soft keyword",
        "hard keyword",
    },
}

FEATURE_SIGNALS = {
    "feature_pattern_matching": {
        "pattern matching",
        "destructur",
        "mapping",
        "sequence",
        "class pattern",
        "wildcard",
        "guard",
        "subject",
        "match statement",
        "shape",
    },
    "feature_switch_statement": {
        "switch",
        "multi-branch",
        "dispatch",
        "dict dispatch",
        "jump table",
        "precompute",
    },
}

PEP_TO_PEP_RELATIONS = {
    "PRECEDENT_FOR",
    "CONTRASTS_WITH",
    "SUPERSEDED_BY",
    "SUPERSEDES",
    "SPLITS_INTO",
}

_INPUT_TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("`", "")).lower()


def _signal_matches(text: str, signals: set[str]) -> list[str]:
    normalized = _normalize(text)
    matched = []
    for signal in signals:
        pattern = r"\b" + re.escape(signal) + r"\w*\b"
        if re.search(pattern, normalized):
            matched.append(signal)
    return sorted(matched)


def _pep_entities(graph: KnowledgeGraph) -> dict[str, object]:
    return {
        eid: graph.get_entity(eid)
        for eid in graph.entities
        if eid.startswith("pep_")
    }


def _build_question_evidence(question_id: str, graph: KnowledgeGraph) -> dict:
    question = graph.get_entity(question_id)
    question_text = question.properties.get("text", question_id) if question else question_id

    options = []
    for rel in graph.outgoing_relationships(question_id, "HAS_OPTION"):
        option = graph.get_entity(rel.target)
        objections = []
        for obj_rel in graph.outgoing_relationships(rel.target, "HAS_OBJECTION"):
            objection = graph.get_entity(obj_rel.target)
            objections.append(
                {
                    "id": obj_rel.target,
                    "text": objection.properties.get("text", "") if objection else "",
                    "category": objection.properties.get("category", "") if objection else "",
                    "outcome": objection.properties.get("outcome", "") if objection else "",
                    "raised_in": [
                        r.target
                        for r in graph.outgoing_relationships(obj_rel.target, "RAISED_IN")
                    ],
                }
            )
        options.append(
            {
                "id": rel.target,
                "label": option.properties.get("label", rel.target) if option else rel.target,
                "objections": objections,
            }
        )

    decisions = []
    for rel in graph.outgoing_relationships(question_id, "RESOLVED_BY"):
        decision = graph.get_entity(rel.target)
        properties = decision.properties if decision else {}
        decisions.append(
            {
                "id": rel.target,
                "recorded_in": properties.get("recorded_in", ""),
                "decision_type": properties.get("decision_type", "final"),
                "chose": properties.get("chose", ""),
                "rejected": properties.get("rejected", []),
                "rationale": properties.get("rationale", ""),
                "note": properties.get("note", ""),
            }
        )

    raised_in = sorted(
        r.source for r in graph.incoming_relationships(question_id, "RAISES_QUESTION")
    )

    return {
        "question": question_id,
        "question_text": question_text,
        "raised_in": raised_in,
        "historical_options": options,
        "decisions": decisions,
    }


def _collect_precedents(pep_ids: set[str], graph: KnowledgeGraph) -> list[dict]:
    precedents = []
    for pep_id in sorted(pep_ids):
        for rel in graph.outgoing_relationships(pep_id):
            if rel.relation in PEP_TO_PEP_RELATIONS:
                target = graph.get_entity(rel.target)
                precedents.append(
                    {
                        "source": rel.source,
                        "relation": rel.relation,
                        "target": rel.target,
                        "target_title": target.properties.get("title", "") if target else "",
                    }
                )
    return precedents


def _build_recommendations(
    evidence: list[dict],
    precedents: list[dict],
    pep_titles: dict[str, str],
) -> list[str]:
    recommendations: list[str] = []

    for item in evidence:
        option_labels = {
            option["id"]: option["label"]
            for option in item["historical_options"]
        }
        option_objections = {
            option["id"]: [obj["text"] for obj in option["objections"]]
            for option in item["historical_options"]
        }

        for decision in item["decisions"]:
            chose_id = decision.get("chose", "")
            chose_label = option_labels.get(chose_id, chose_id)
            recorded = decision.get("recorded_in", "")
            recorded_label = pep_titles.get(recorded, recorded)
            decision_type = decision.get("decision_type", "final")
            kind = "" if decision_type == "final" else f" [{decision_type}]"

            line = (
                f"Question '{item['question_text']}' (raised in {', '.join(item['raised_in'])}): "
                f"decision {decision['id']}{kind} recorded in {recorded_label} "
                f"chose '{chose_label}' — {decision.get('rationale', '')}"
            )
            if decision.get("note"):
                line += f" Note: {decision['note']}"
            recommendations.append(line)

            for rejected_id in decision.get("rejected", []):
                label = option_labels.get(rejected_id, rejected_id)
                objections = option_objections.get(rejected_id, [])
                detail = "; ".join(objections) or "no recorded objection"
                recommendations.append(f"  rejected '{label}': {detail}")

    for precedent in precedents:
        recommendations.append(
            f"Historical link: {precedent['source']} {precedent['relation']} "
            f"{precedent['target']} ('{precedent['target_title']}')."
        )

    return recommendations


def reason(proposal: str, graph: KnowledgeGraph) -> dict:
    question_hits = {
        qid: _signal_matches(proposal, signals)
        for qid, signals in QUESTION_SIGNALS.items()
    }
    feature_hits = {
        fid: _signal_matches(proposal, signals)
        for fid, signals in FEATURE_SIGNALS.items()
    }

    scores: dict[str, list[str]] = {}
    for qid, matched in question_hits.items():
        if matched:
            scores.setdefault(qid, [])
            scores[qid].extend(f"[question] {m}" for m in matched)

    related_questions: set[str] = set()
    for fid, matched in feature_hits.items():
        if not matched:
            continue
        for rel in graph.incoming_relationships(fid, "PROPOSES"):
            for q_rel in graph.outgoing_relationships(rel.source, "RAISES_QUESTION"):
                related_questions.add(q_rel.target)
                scores.setdefault(q_rel.target, [])
                scores[q_rel.target].extend(f"[{rel.source}] {m}" for m in matched)

    ordered_questions = sorted(
        scores,
        key=lambda qid: (-len(scores[qid]), qid),
    )

    involved_peps: set[str] = set()
    for qid in ordered_questions:
        involved_peps.update(
            r.source for r in graph.incoming_relationships(qid, "RAISES_QUESTION")
        )

    evidence = []
    for qid in ordered_questions:
        item = _build_question_evidence(qid, graph)
        item["relevance_score"] = len(scores[qid])
        item["matched_signals"] = scores[qid]
        involved_peps.update(item["raised_in"])
        for decision in item["decisions"]:
            involved_peps.add(decision.get("recorded_in", ""))
        evidence.append(item)

    precedents = _collect_precedents({p for p in involved_peps if p.startswith("pep_")}, graph)

    context_peps: dict[str, Entity] = {}

    for pep_id in sorted(involved_peps):
        if not pep_id.startswith("pep_"):
            continue

        entity = graph.get_entity(pep_id)

        if entity is not None:
            context_peps[pep_id] = entity
    historical_context = [
        {
            "id": pep_id,
            "title": entity.properties.get("title", ""),
            "status": entity.properties.get("status", ""),
            "python_version": entity.properties.get("python_version", ""),
            "created": entity.properties.get("created", ""),
        }
        for pep_id, entity in context_peps.items()
    ]

    matched_terms = set()
    for matched in question_hits.values():
        matched_terms.update(matched)
    for matched in feature_hits.values():
        matched_terms.update(matched)
    all_tokens = set(_INPUT_TOKEN_RE.findall(_normalize(proposal)))
    unmatched = sorted(
        token for token in all_tokens if token not in matched_terms and len(token) > 2
    )

    return {
        "input": proposal,
        "signal_match": {
            "questions": {qid: m for qid, m in question_hits.items() if m},
            "features": {fid: m for fid, m in feature_hits.items() if m},
            "unmatched_terms": unmatched,
        },
        "relevant_questions": evidence,
        "historical_context": historical_context,
        "precedents": precedents,
        "recommendations": _build_recommendations(
            evidence,
            precedents,
            {
                item["id"]: f"{item['id']} ('{item['title']}')"
                for item in historical_context
            },
        ),
    }