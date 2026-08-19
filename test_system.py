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


section("8. Deterministic relevance — direct vs contextual")
from src.reasoner import _fix_spacing

# TEST 1: feature expansion must not promote q1/q3 to primary relevance.
r = reason(
    "I want to introduce a new reserved keyword for pattern matching.", g
)
check(
    "regression: reserved keyword primary is q4",
    qids(r) == ["q4_keyword_hardness"],
    str(qids(r)),
)
check(
    "regression: q1/q3 not primary",
    not {"q1_wildcard_token", "q3_or_pattern_separator"} & set(qids(r)),
)
check(
    "regression: q4 marked direct",
    all(q["relevance_type"] == "direct" for q in r["relevant_questions"]),
)
check(
    "regression: trace shows reserved keyword then keyword",
    r["relevant_questions"][0]["matched_signals"]
    == ["[question] reserved keyword", "[question] keyword"],
    str(r["relevant_questions"][0]["matched_signals"]),
)
check(
    "regression: pep_622 still historical context",
    "pep_622" in [p["id"] for p in r["historical_context"]],
)

# TEST 2: wildcard/placeholder syntax -> q1.
r = reason(
    "I want to introduce a new wildcard placeholder syntax for pattern matching.", g
)
check(
    "regression: wildcard placeholder primary is q1",
    qids(r) == ["q1_wildcard_token"],
    str(qids(r)),
)

# TEST 3: alternative patterns in nested matches -> q3.
r = reason(
    "I want to introduce a new syntax for alternative patterns inside nested match patterns.", g
)
check(
    "regression: alternative patterns primary is q3",
    qids(r) == ["q3_or_pattern_separator"],
    str(qids(r)),
)

# TEST 4: switch-style dispatch with precomputed lookup tables -> q2.
r = reason(
    "I want to add a switch-style dispatch mechanism using precomputed lookup tables.", g
)
check(
    "regression: dispatch primary is q2",
    qids(r) == ["q2_dispatch_semantics"],
    str(qids(r)),
)

# TEST 5: mixed construct — q2, q3, q4 primary; q1 NOT inferred from the
# feature match alone.
r = reason(
    "I want to add a new pattern matching construct with alternative patterns, "
    "a new keyword, and optimized dispatch.",
    g,
)
got = qids(r)
check(
    "regression: mixed construct finds q2/q3/q4",
    {"q2_dispatch_semantics", "q3_or_pattern_separator", "q4_keyword_hardness"}
    <= set(got),
    str(got),
)
check(
    "regression: mixed construct does not invent q1",
    "q1_wildcard_token" not in got,
    str(got),
)

# TEST 6: irrelevant input — no invented connections.
r = reason("I want to improve Python's garbage collector to reduce memory usage.", g)
check(
    "regression: GC input has no relevant questions",
    len(r["relevant_questions"]) == 0,
    str(qids(r)),
)
check(
    "regression: GC input has no precedents",
    len(r["precedents"]) == 0,
)
check(
    "regression: GC input has no historical context",
    len(r["historical_context"]) == 0,
)

# TEST 7: old substring bug — "for pattern matching" must not match
# q3_or_pattern_separator via the "or pattern" signal.
r = reason("for pattern matching", g)
all_traces = [
    sig
    for q in r["relevant_questions"] + r["contextual_questions"]
    for sig in q["matched_signals"]
]
check(
    "regression: 'or pattern' never in matched signals",
    not any("or pattern" in sig for sig in all_traces),
    str(all_traces),
)
check(
    "regression: q3 not directly matched",
    "q3_or_pattern_separator" not in r["signal_match"]["questions"],
    str(r["signal_match"]["questions"]),
)

section("9. Broad input fallback and formatting")
r = reason("I want to change Python's pattern matching behavior.", g)
check(
    "fallback: broad input surfaces contextual questions",
    len(r["relevant_questions"]) >= 1,
    str(qids(r)),
)
check(
    "fallback: questions clearly marked contextual",
    all(q["relevance_type"] == "contextual" for q in r["relevant_questions"]),
    str([q["relevance_type"] for q in r["relevant_questions"]]),
)
check(
    "fallback: no direct questions",
    r["direct_questions"] == [],
    str(r["direct_questions"]),
)
check(
    "fallback: pep_622 in historical context",
    "pep_622" in [p["id"] for p in r["historical_context"]],
)

fixed = _fix_spacing(
    "Soft(contextual) keyword doesn'trequire; "
    "the 'colon increases indent'convention C#,Elixir"
)
check(
    "formatting: spacing artifacts repaired",
    fixed
    == "Soft (contextual) keyword doesn't require; "
    "the 'colon increases indent' convention C#, Elixir",
    fixed,
)
fixed_ticks = _fix_spacing("use `_`;e.g. Point(0|1, 0|1)")
check(
    "formatting: code spans untouched, real calls unspaced",
    fixed_ticks == "use `_`; e.g. Point(0|1, 0|1)",
    fixed_ticks,
)

print(f"\n{'='*50}")
print(f"TOTAL: {PASSED + FAILED} checks, {FAILED} failed")
if FAILURES:
    print("Failed checks:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print("ALL PASS")