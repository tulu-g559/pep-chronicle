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
        "reserved keyword",
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

##--## --- signal matching ---------------------------------------------------------


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("`", "")).lower()


def _signal_weight(signal: str) -> int:
    # Deterministic weighting (no ML, no similarity):
    #   exact multi-word phrase  -> +3   ("reserved keyword", "or pattern")
    #   single-word signal       -> +1   ("keyword", "dispatch")
    # A phrase is more specific evidence than a bare word, so "reserved
    # keyword" outweighs the generic "keyword" for q4_keyword_hardness.
    return 3 if len(signal.split()) > 1 else 1


def _signal_matches(text: str, signals: set[str]) -> list[str]:
    normalized = _normalize(text)
    matched = []
    for signal in signals:
        words = signal.split()
        if len(words) == 1:
            # Single-word signal: word boundary + optional inflectional
            # ending (keyword -> keywords, precompute -> precomputed).
            # Word-boundary anchoring prevents substring false positives.
            pattern = r"\b" + re.escape(signal) + r"\w*\b"
        else:
            # Multi-word phrase: word boundary before the first word, exact
            # interior words, optional space/hyphen between words, and an
            # inflectional ending on the last word (or pattern -> or patterns).
            # Never raw substring matching, so "for pattern matching" cannot
            # match the "or pattern" signal.
            parts = [re.escape(word) for word in words]
            pattern = r"\b" + parts[0]
            for part in parts[1:-1]:
                pattern += r"[\s-]+" + part
            pattern += r"[\s-]+" + parts[-1] + r"\w*\b"
        if re.search(pattern, normalized):
            matched.append(signal)
    return sorted(matched)


def _order_by_score(qids, scores) -> list[str]:
    lookup = scores if callable(scores) else lambda qid: scores[qid]
    return sorted(qids, key=lambda qid: (lookup(qid), qid))


#### --- evidence building -----=======-------------


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


# --- recommendation formatting ----------------------------------------------

_BACKTICK_RE = re.compile(r"`[^`]*`")


def _fix_spacing(text: str) -> str:
    # Presentation-only repair for recommendation text. Inserts missing
    # spaces around punctuation so lines read cleanly ("Soft(contextual)"
    # -> "Soft (contextual)", "doesn'trequire" -> "doesn't require",
    # "'indent'convention" -> "'indent' convention", "C#,Elixir" ->
    # "C#, Elixir"). Content inside `code` spans is never touched, and the
    # underlying knowledge content is never modified.
    pieces: list[str] = []
    pos = 0
    for span in _BACKTICK_RE.finditer(text):
        pieces.append(_fix_spacing_plain(text[pos : span.start()]))
        pieces.append(span.group(0))
        pos = span.end()
    pieces.append(_fix_spacing_plain(text[pos:]))
    return "".join(pieces).strip()


def _fix_spacing_plain(segment: str) -> str:
    s = segment
    s = re.sub(r"(n't)([a-z])", r"\1 \2", s)  # doesn'trequire -> doesn't require
    s = re.sub(r"([a-z])'([a-z]{3,})", r"\1' \2", s)  # 'word'word -> 'word' word
    s = re.sub(r"([A-Za-z])\(([a-z][a-z ]*)\)", r"\1 (\2)", s)  # Soft(x) -> Soft (x)
    s = re.sub(r"([,;])([A-Za-z])", r"\1 \2", s)  # C#,Elixir -> C#, Elixir
    s = re.sub(r"(\))([a-z])", r"\1 \2", s)  # );word -> ); word
    s = re.sub(r"\s{2,}", " ", s)
    return s


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
                f"chose '{chose_label}' - {decision.get('rationale', '')}"
            )
            if decision.get("note"):
                line += f" Note: {decision['note']}"
            recommendations.append(_fix_spacing(line))

            for rejected_id in decision.get("rejected", []):
                label = option_labels.get(rejected_id, rejected_id)
                objections = option_objections.get(rejected_id, [])
                detail = "; ".join(objections) or "no recorded objection"
                recommendations.append(
                    _fix_spacing(f"  rejected '{label}': {detail}")
                )

    for precedent in precedents:
        recommendations.append(
            _fix_spacing(
                f"Historical link: {precedent['source']} {precedent['relation']} "
                f"{precedent['target']} ('{precedent['target_title']}')."
            )
        )

    return recommendations


# --- main reasoning entry point ---------------------------------------------


def reason(proposal: str, graph: KnowledgeGraph) -> dict:
    question_hits = {
        qid: _signal_matches(proposal, signals)
        for qid, signals in QUESTION_SIGNALS.items()
    }
    feature_hits = {
        fid: _signal_matches(proposal, signals)
        for fid, signals in FEATURE_SIGNALS.items()
    }

    # 1. DIRECT evidence: signals belonging to a DesignQuestion are strong.
    direct_scores: dict[str, int] = {}
    direct_traces: dict[str, list[str]] = {}
    for qid, matched in question_hits.items():
        if not matched:
            continue
        weighted = sorted(matched, key=lambda s: (-_signal_weight(s), s))
        direct_scores[qid] = sum(_signal_weight(s) for s in matched)
        direct_traces[qid] = [f"[question] {s}" for s in weighted]

    # 2. CONTEXTUAL evidence: a matched Feature explains why a design
    #    question is historically relevant (Feature -> PROPOSES -> PEP ->
    #    RAISES_QUESTION), but it must NOT promote every question raised by
    #    that feature's PEP to primary relevance.
    contextual: dict[str, dict] = {}
    for fid in sorted(feature_hits):
        matched = feature_hits[fid]
        if not matched:
            continue
        for rel in graph.incoming_relationships(fid, "PROPOSES"):
            pep_id = rel.source
            for q_rel in graph.outgoing_relationships(pep_id, "RAISES_QUESTION"):
                qid = q_rel.target
                entry = contextual.setdefault(
                    qid, {"score": 0, "signals": [], "peps": set()}
                )
                entry["peps"].add(pep_id)
                for signal in matched:
                    entry["score"] += _signal_weight(signal)
                    entry["signals"].append((fid, signal))

    direct_qids = set(direct_scores)

    # 3. Primary questions: direct hits win. Feature-derived questions are
    #    used only as a fallback when no direct question signal matched.
    if direct_qids:
        primary_qids = direct_qids
        primary_kind = "direct"
    elif contextual:
        primary_qids = set(contextual)
        primary_kind = "contextual"
    else:
        primary_qids = set()
        primary_kind = "direct"

    def _score(qid: str) -> int:
        if qid in direct_scores:
            return direct_scores[qid]
        return contextual[qid]["score"]

    def _contextual_trace(qid: str) -> list[str]:
        traces = {
            f"[{fid}] {signal}" for fid, signal in contextual[qid]["signals"]
        }
        return sorted(
            traces,
            key=lambda t: (-_signal_weight(t.split("] ", 1)[1]), t),
        )

    evidence = []
    for qid in _order_by_score(primary_qids, _score):
        item = _build_question_evidence(qid, graph)
        item["relevance_type"] = primary_kind
        item["relevance_score"] = _score(qid)
        item["matched_signals"] = (
            direct_traces[qid] if qid in direct_scores else _contextual_trace(qid)
        )
        evidence.append(item)

    # 4. Remaining feature-derived questions are context only and stay out of
    #    the primary list whenever a direct match already exists.
    contextual_evidence = []
    for qid in _order_by_score(
        set(contextual) - primary_qids,
        lambda q: contextual[q]["score"],
    ):
        item = _build_question_evidence(qid, graph)
        item["relevance_type"] = "contextual"
        item["relevance_score"] = contextual[qid]["score"]
        item["matched_signals"] = _contextual_trace(qid)
        contextual_evidence.append(item)

    # 5. Historical context: PEPs raised by primary questions, PEPs recorded
    #    in their decisions, and PEPs behind matched features.
    involved_peps: set[str] = set()
    for entry in contextual.values():
        involved_peps.update(entry["peps"])
    for item in evidence:
        involved_peps.update(item["raised_in"])
        for decision in item["decisions"]:
            involved_peps.add(decision.get("recorded_in", ""))

    precedents = _collect_precedents(
        {p for p in involved_peps if p.startswith("pep_")}, graph
    )

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

    # 6. Unmatched terms: every signal word that did match is "explained",
    #    including the words inside matched phrases (e.g. "pattern matching"
    #    explains both "pattern" and "matching").
    matched_terms = set()
    for matched in question_hits.values():
        matched_terms.update(matched)
    for matched in feature_hits.values():
        matched_terms.update(matched)
    all_tokens = set(_INPUT_TOKEN_RE.findall(_normalize(proposal)))
    explained = set()
    for signal in matched_terms:
        explained.update(_INPUT_TOKEN_RE.findall(signal))
    unmatched = sorted(
        token for token in all_tokens if token not in explained and len(token) > 2
    )

    return {
        "input": proposal,
        "signal_match": {
            "questions": {qid: m for qid, m in question_hits.items() if m},
            "features": {fid: m for fid, m in feature_hits.items() if m},
            "unmatched_terms": unmatched,
        },
        "direct_questions": sorted(direct_qids),
        "relevant_questions": evidence,
        "contextual_questions": contextual_evidence,
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