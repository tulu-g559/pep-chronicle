import subprocess, sys
from pathlib import Path
from src.graph import load_knowledge
from src.reasoner import reason

ROOT = Path(__file__).resolve().parent
KB_PATH = ROOT / "knowledge.json"


PASSED, FAILED=0, 0
FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        PASSED +=1
        print(f"  PASS  {name}")
    else:
        FAILED +=1
        FAILURES.append(name)
        print(f"  FAIL  {name}  {detail}")



def qids(result: dict) -> list[str]:
    return [q["question"] for q in result["relevant_questions"]]
def top(result: dict) -> str | None:
    return qids(result)[0] if qids(result) else None

def section(name: str) -> None:
    print(f"\n{name}")
    print("-" * len(name))



g = load_knowledge(KB_PATH)
kb_text = KB_PATH.read_text(encoding="utf-8")


section("0. Loaded knowledge state")
check("41 entities loaded", len(g.entities) == 41, str(len(g.entities)))
check(
    "64 relationships loaded",
    len(g.state.relationships) == 64,
    str(len(g.state.relationships)),
)


section("1. Known-like inputs — retrieve relevant historical knowledge")
known = [
    (
        "wildcard placeholder",
        "I want to introduce a new wildcard placeholder syntax for pattern matching.",
        ["q1_wildcard_token"],
        {"q1_wildcard_token": "opt_q1_underscore"},
    ),
    (
        "alternative patterns in nested matches",
        "I want a new syntax for expressing alternative patterns inside nested match patterns.",
        ["q3_or_pattern_separator"],
        {"q3_or_pattern_separator": "opt_q3_pipe"},
    ),
    (
        "reserved keyword",
        "I want to introduce a new reserved keyword for pattern matching.",
        ["q4_keyword_hardness"],
        {"q4_keyword_hardness": "opt_q4_soft_keyword"},
    ),
    (
        "switch dispatch with lookup tables",
        "I want to add a switch-style dispatch mechanism using precomputed lookup tables.",
        ["q2_dispatch_semantics"],
        {"q2_dispatch_semantics": "opt_q2_dict_dispatch"},
    ),
]
for name, proposal, expected, chose in known:
    result = reason(proposal, g)
    check(f"retrieval: {name} surfaces {expected[0]}", expected[0] in qids(result), str(qids(result)))
    check(f"retrieval: {name} top-ranked", top(result) == expected[0], str(top(result)))
    for qid, chosen in chose.items():
        item = next(q for q in result["relevant_questions"] if q["question"] == qid)
        check(f"retrieval: {name} has options", len(item["historical_options"]) >= 2)
        check(
            f"retrieval: {name} decision chose {chosen}",
            any(d["chose"] == chosen for d in item["decisions"]),
            str([d["chose"] for d in item["decisions"]]),
        )
        check(
            f"retrieval: {name} rationale present",
            all(d.get("rationale") for d in item["decisions"]),
        )



section("2. Novel inputs — reason from existing relationships")
novel =[
    (
        "fall-through case clauses",
        "I want to add C-style fall-through semantics between case clauses.",
        ["q3_or_pattern_separator"],
    ),
    (
        "soft keyword marking alternatives",
        "Introduce a soft keyword that also marks alternative patterns.",
        ["q4_keyword_hardness", "q3_or_pattern_separator"],
    ),
    (
        "custom non-binding wildcard character",
        "Allow a custom character as the non-binding wildcard instead of underscore.",
        ["q1_wildcard_token"],
    ),
]
for name, proposal, expected in novel:
    result = reason(proposal, g)
    got = qids(result)
    check(f"novel: {name} connects to known questions", all(e in got for e in expected), str(got))
    for qid in expected:
        item = next(q for q in result["relevant_questions"] if q["question"] == qid)
        check(
            f"novel: {name} cites historical objections",
            any(o["objections"] for o in item["historical_options"]),
        )
        check(
            f"novel: {name} cites historical decisions",
            len(item["decisions"]) >= 1,
        )



section("3. Irrelevant inputs — no invented connections")
irrelevant = [
    "I want to add a new standard library for parsing CSV files.",
    "The weather in San Francisco is nice today.",
    "Add a decorator for caching function results.",
]
for proposal in irrelevant:
    result = reason(proposal, g)
    check(
        f"irrelevant: no questions for '{proposal[:40]}...'",
        len(result["relevant_questions"]) == 0,
        str(qids(result)),
    )
    check("irrelevant: no precedents", len(result["precedents"]) == 0)
    check("irrelevant: no historical context", len(result["historical_context"]) == 0)
    check("irrelevant: no recommendations", len(result["recommendations"]) == 0)
    check("irrelevant: input echoed untouched", result["input"] == proposal)

section("4. Mixed proposals — multiple design questions")
mixed = [
    (
        "switch + keyword + alternatives + dispatch",
        "I want to add a switch-like pattern matching feature with a new reserved keyword, alternative pattern syntax, and precomputed dispatch.",
        ["q2_dispatch_semantics", "q3_or_pattern_separator", "q4_keyword_hardness"],
    ),
    (
        "wildcard token + OR separator",
        "New wildcard token and a better separator for or patterns.",
        ["q1_wildcard_token", "q3_or_pattern_separator"],
    ),
]
for name, proposal, expected in mixed:
    result = reason(proposal, g)
    got = qids(result)
    check(f"mixed: {name} finds all questions", all(e in got for e in expected), str(got))
    check(f"mixed: {name} ranks at least one expected first", top(result) in expected, str(got))

section("5. Empty / very vague input — fail gracefully")
vague = ["", "   ", "python", "add a feature", "?", "yes"]
for proposal in vague:
    result = reason(proposal, g)
    check(
        f"vague: no crash for {proposal!r}",
        isinstance(result, dict) and "relevant_questions" in result,
    )
    check(
        f"vague: no questions for {proposal!r}",
        len(result["relevant_questions"]) == 0,
        str(qids(result)),
    )

section("6. External-input integrity")
all_proposals = [p for _, p, *_ in known + novel + mixed]
for proposal in all_proposals:
    check(
        f"proposal not inserted into knowledge.json: {proposal[:40]}...",
        proposal not in kb_text,
    )



section("7. CLI integration")
r= subprocess.run(
    [sys.executable, "cli.py", "I want to add a switch-style dispatch mechanism using precomputed lookup tables."],
    cwd=ROOT,
    capture_output=True,
    text=True,
)
check("cli: single-arg mode exits 0", r.returncode == 0, r.stderr[-500:])
check("cli: prints design questions", "RELEVANT DESIGN QUESTIONS" in r.stdout)
check("cli: prints decisions", "HISTORICAL DECISIONS" in r.stdout)
check("cli: prints recommendations", "RECOMMENDATIONS" in r.stdout)

r_empty = subprocess.run(
    [sys.executable, "cli.py"],
    cwd=ROOT,
    input="\n",
    capture_output=True,
    text=True,
)
check("cli: empty interactive input exits cleanly", r_empty.returncode == 0, r_empty.stderr[-500:])

print(f"\n{'='*50}")
print(f"TOTAL: {PASSED + FAILED} checks, {FAILED} failed")
if FAILURES:
    print("Failed checks:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print("ALL PASS")