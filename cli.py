from __future__ import annotations
import io, sys
from pathlib import Path

if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.graph import load_knowledge
from src.reasoner import reason

BANNER = """
-----------------------------------------
|PEP Chronicle
|Historical Python Design Reasoner
|========================================
"""


def _option_markers(item: dict) -> dict[str, str]:
    markers: dict[str, str] = {}
    for decision in item["decisions"]:
        markers[decision.get("chose", "")] = "✓"
        for rejected_id in decision.get("rejected", []):
            markers[rejected_id] = "✗"
    return markers


def render(result: dict) -> str:
    lines: list[str] = []

    lines.append("NEW PROPOSAL")
    lines.append("-" * len("NEW PROPOSAL"))
    lines.append(f"> {result['input']}")
    lines.append("")

    lines.append("MATCHED CONCEPTS")
    lines.append("-" * len("MATCHED CONCEPTS"))
    for qid, signals in result["signal_match"]["questions"].items():
        lines.append(f"  question: {qid}  ({', '.join(signals)})")
    for fid, signals in result["signal_match"]["features"].items():
        lines.append(f"  feature:  {fid}  ({', '.join(signals)})")
    unmatched = result["signal_match"]["unmatched_terms"]
    if unmatched:
        lines.append(f"  unmatched terms: {', '.join(unmatched)}")
    lines.append("")

    lines.append("RELEVANT DESIGN QUESTIONS")
    lines.append("-" * len("RELEVANT DESIGN QUESTIONS"))
    for i, item in enumerate(result["relevant_questions"], start=1):
        lines.append(
            f"{i}. {item['question_text']}  (score {item['relevance_score']})"
        )
    lines.append("")

    lines.append("HISTORICAL OPTIONS AND OBJECTIONS")
    lines.append("-" * len("HISTORICAL OPTIONS AND OBJECTIONS"))
    for item in result["relevant_questions"]:
        markers = _option_markers(item)
        lines.append(f"Question: {item['question_text']}")
        for option in item["historical_options"]:
            marker = markers.get(option["id"], " ")
            lines.append(f"  {marker} {option['label']}")
            for objection in option["objections"]:
                lines.append(f"      objection ({objection['category']}):")
                lines.append(f"        {objection['text']}")
        lines.append("")

    lines.append("HISTORICAL DECISIONS")
    lines.append("-" * len("HISTORICAL DECISIONS"))
    for item in result["relevant_questions"]:
        labels = {o["id"]: o["label"] for o in item["historical_options"]}
        for decision in item["decisions"]:
            chose = labels.get(decision["chose"], decision["chose"])
            rejected = [
                labels.get(rid, rid) for rid in decision.get("rejected", [])
            ]
            kind = (
                f" [{decision.get('decision_type', 'final')}]"
                if decision.get("decision_type", "final") != "final"
                else ""
            )
            lines.append(
                f"  {decision['id']}{kind} ({decision.get('recorded_in', '')}): "
                f"chose '{chose}'; rejected: {', '.join(rejected) or 'none'}"
            )
            lines.append(f"    rationale: {decision.get('rationale', '')}")
            if decision.get("note"):
                lines.append(f"    note: {decision['note']}")
        lines.append("")

    lines.append("HISTORICAL CONTEXT")
    lines.append("-" * len("HISTORICAL CONTEXT"))
    for pep in result["historical_context"]:
        lines.append(
            f"  {pep['id']} — {pep['title']} "
            f"[{pep['status']}, Python {pep['python_version']}, {pep['created']}]"
        )
    lines.append("")

    lines.append("PRECEDENTS")
    lines.append("-" * len("PRECEDENTS"))
    for precedent in result["precedents"]:
        lines.append(
            f"  {precedent['source']} {precedent['relation']} "
            f"{precedent['target']} ('{precedent['target_title']}')"
        )
    if not result["precedents"]:
        lines.append("  (none)")
    lines.append("")

    lines.append("RECOMMENDATIONS")
    lines.append("-" * len("RECOMMENDATIONS"))
    for recommendation in result["recommendations"]:
        lines.append(f"  - {recommendation}")
    lines.append("")

    return "\n".join(lines)



def main(argv: list[str]) -> int:
    graph = load_knowledge(Path("knowledge.json"))
    print(BANNER)

    if len(argv) >= 2:
        proposals = [" ".join(argv[1:])]
    else:
        proposals = []
        while True:
            try:
                proposal = input("\nEnter a new Python proposal (blank to quit):\n> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not proposal.strip():
                break
            proposals.append(proposal.strip())

    if not proposals:
        print("No proposal provided. Goodbye.")
        return 0

    for proposal in proposals:
        result = reason(proposal, graph)
        print(render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))