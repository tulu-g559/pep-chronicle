SCHEMA_VERSION = "1.0"

DOMAIN = (
    "Python PEP design history: structural pattern matching (match/case) "
    "and its precedent, the rejected switch statement"
)

# Property overlays merged into the Proposal entities extracted from the
# RST headers. They preserve the curated knowledge model where the header
# text differs from it, or where the curated state records metadata that
# the headers do not carry (e.g. a rejection note).
PROPERTY_OVERLAYS = {
    "pep_3103": {
        "rejection_note": (
            "Rejected by Guido after a straw poll at his PyCon 2007 keynote "
            "showed no popular support."
        ),
    },
    "pep_622": {"superseded_by": "pep_634"},
    "pep_634": {"replaces": "pep_622"},
    "pep_635": {"authors": ["Tobias Kohn", "Talin"]},
    "pep_636": {"authors": ["Daniel F Moisset", "Guido van Rossum"]},
}

CURATED_ENTITIES = [
    {"id": "feature_switch_statement", "type": "Feature", "name": "switch statement",
     "description": "C-style multi-branch dispatch on a value, with dict-precompute optimization debated"},

    {"id": "feature_pattern_matching", "type": "Feature", "name": "structural pattern matching",
     "description": "match/case statement: destructures a subject against shape patterns (literal, capture, sequence, mapping, class, OR, wildcard)"},

    {"id": "concept_pattern_matching_semantics", "type": "Concept", "name": "Pattern Matching Semantics"},
    {"id": "concept_pattern_types", "type": "Concept", "name": "Pattern Types"},
    {"id": "concept_match_statement_behavior", "type": "Concept", "name": "Match Statement Behavior"},
    {"id": "concept_design_decisions", "type": "Concept", "name": "Design Decisions"},
    {"id": "concept_objections", "type": "Concept", "name": "Objections"},
    {"id": "concept_design_choices", "type": "Concept", "name": "Design Choices"},
    {"id": "concept_pattern_matching_usage", "type": "Concept", "name": "Pattern Matching Usage"},

    {"id": "q1_wildcard_token", "type": "DesignQuestion", "text": "What token should be used for the wildcard pattern?"},
    {"id": "q2_dispatch_semantics", "type": "DesignQuestion", "text": "Should case dispatch use if/elif-chain semantics or a precomputed dict?"},
    {"id": "q3_or_pattern_separator", "type": "DesignQuestion", "text": "What syntax should separate alternatives in an OR pattern?"},
    {"id": "q4_keyword_hardness", "type": "DesignQuestion", "text": "Should match/case be hard keywords or soft (contextual) keywords?"},

    {"id": "opt_q1_underscore", "type": "DesignOption", "question": "q1_wildcard_token", "label": "Use underscore `_`"},
    {"id": "opt_q1_ellipsis", "type": "DesignOption", "question": "q1_wildcard_token", "label": "Use ellipsis `...`"},
    {"id": "opt_q1_question_mark", "type": "DesignOption", "question": "q1_wildcard_token", "label": "Use question mark `?`"},

    {"id": "opt_q2_if_elif", "type": "DesignOption", "question": "q2_dispatch_semantics", "label": "School I: if/elif-chain equivalent semantics"},
    {"id": "opt_q2_dict_dispatch", "type": "DesignOption", "question": "q2_dispatch_semantics", "label": "School II: precomputed dict-based dispatch"},

    {"id": "opt_q3_pipe", "type": "DesignOption", "question": "q3_or_pattern_separator", "label": "Use `|`"},
    {"id": "opt_q3_or_keyword", "type": "DesignOption", "question": "q3_or_pattern_separator", "label": "Use `or` keyword"},
    {"id": "opt_q3_comma", "type": "DesignOption", "question": "q3_or_pattern_separator", "label": "Use comma"},
    {"id": "opt_q3_stacked_case", "type": "DesignOption", "question": "q3_or_pattern_separator", "label": "Stacked `case` clauses (C-style fallthrough look)"},

    {"id": "opt_q4_hard_keyword", "type": "DesignOption", "question": "q4_keyword_hardness", "label": "Hard keyword"},
    {"id": "opt_q4_soft_keyword", "type": "DesignOption", "question": "q4_keyword_hardness", "label": "Soft (contextual) keyword"},

    {"id": "obj_q1_ellipsis", "type": "Objection", "option": "opt_q1_ellipsis",
     "text": "Looks like 'items omitted'; conflicts with existing conventional use of ... in Python docs/examples to mean elided content.",
     "category": "readability", "outcome": "blocked"},

    {"id": "obj_q1_question_mark", "type": "Objection", "option": "opt_q1_question_mark",
     "text": "No precedent in any Python syntax for ? as a token; would require tokenizer changes.",
     "category": "precedent/implementation", "outcome": "blocked"},

    {"id": "obj_q2_dict_dispatch", "type": "Objection", "option": "opt_q2_dict_dispatch",
     "text": "Named constants used as case values can't be reliably resolved at the time the dict is frozen; if hash() has side effects or its value changes, optimized and unoptimized code can behave differently.",
     "category": "correctness/semantics", "outcome": "blocked"},

    {"id": "obj_q3_comma", "type": "Objection", "option": "opt_q3_comma",
     "text": "Looks too much like a tuple literal; would force a different spelling for actual tuples, and commas already carry too many meanings in Python.",
     "category": "ambiguity", "outcome": "blocked"},

    {"id": "obj_q3_stacked_case", "type": "Objection", "option": "opt_q3_stacked_case",
     "text": "Misleads users into expecting C-style fall-through semantics (a common source of bugs in C); introduces a novel indentation rule that breaks the 'colon increases indent' convention; does not support OR patterns nested inside other patterns.",
     "category": "readability/consistency", "outcome": "blocked"},

    {"id": "obj_q3_or_keyword", "type": "Objection", "option": "opt_q3_or_keyword",
     "text": "Readable, but | has precedent in Elixir/Erlang/F#/Mathematica/OCaml/Ruby/Rust/Scala pattern syntax, is shorter for nested patterns like Point(0|1, 0|1), and is already used elsewhere in Python for set union, dict merge (PEP 584), and union types (PEP 604); or risks over-association with boolean short-circuiting.",
     "category": "consistency/precedent", "outcome": "blocked"},

    {"id": "obj_q4_hard_keyword", "type": "Objection", "option": "opt_q4_hard_keyword",
     "text": "match is a very common existing identifier (e.g. re.match); a hard keyword would break a large amount of existing code. The new PEG parser doesn't require hard-keyword status, and no alternative keyword avoids the same identifier-collision problem.",
     "category": "backwards compatibility", "outcome": "blocked"},

    {"id": "d1", "type": "Decision", "question": "q1_wildcard_token", "recorded_in": "pep_622",
     "chose": "opt_q1_underscore", "rejected": ["opt_q1_ellipsis", "opt_q1_question_mark"],
     "rationale": "Underscore already used as a throwaway target elsewhere in Python (e.g. unpacking); used as the wildcard in nearly every other language with pattern matching (C#, Elixir, Erlang, F#, Haskell, OCaml, Ruby, Rust, Scala, Swift)."},

    {"id": "d2", "type": "Decision", "question": "q2_dispatch_semantics", "recorded_in": "pep_3103",
     "decision_type": "design_preference",
     "chose": "opt_q2_dict_dispatch", "rejected": ["opt_q2_if_elif"],
     "rationale": "Guido's stated preference in PEP 3103 leaned toward School II (dict dispatch) for performance, despite its named-constant/hash-side-effect problems.",
     "note": "This was a design preference discussed in PEP 3103, not an implemented decision. The overall proposal was later rejected."},

    {"id": "d2b", "type": "Decision", "question": "q2_dispatch_semantics", "recorded_in": "pep_634",
     "chose": "opt_q2_if_elif", "rejected": ["opt_q2_dict_dispatch"],
     "rationale": "14 years later, match statement semantics defined as equivalent to a first-match if/elif chain, explicitly avoiding the named-constant/dict-freezing problems that undermined PEP 3103's School II approach.",
     "informed_by": "obj_q2_dict_dispatch"},

    {"id": "d3", "type": "Decision", "question": "q3_or_pattern_separator", "recorded_in": "pep_622",
     "chose": "opt_q3_pipe", "rejected": ["opt_q3_or_keyword", "opt_q3_comma", "opt_q3_stacked_case"],
     "rationale": "Consistent with other pattern-matching languages, consistent with Python's own existing uses of | (set union, dict merge, PEP 604 unions), and reads better than `or` in deeply nested patterns."},

    {"id": "d4", "type": "Decision", "question": "q4_keyword_hardness", "recorded_in": "pep_622",
     "chose": "opt_q4_soft_keyword", "rejected": ["opt_q4_hard_keyword"],
     "rationale": "PEG parser (PEP 617) supports backtracking, making soft keywords workable; avoids breaking existing code that uses match as an identifier (notably re.match)."},
]

# Historical links asserted by reading the PEPs; no single document states
# them. PEP 3103 predates PEP 622, and the concept mappings are editorial
# judgments about which document defines, explains, addresses, justifies,
# or demonstrates which concept.
CURATED_RELATIONSHIPS = [
    ("pep_3103", "PRECEDENT_FOR", "pep_622"),
    ("pep_3103", "CONTRASTS_WITH", "pep_622"),
    ("pep_634", "DEFINES", "concept_pattern_matching_semantics"),
    ("pep_634", "DEFINES", "concept_pattern_types"),
    ("pep_634", "DEFINES", "concept_match_statement_behavior"),
    ("pep_635", "EXPLAINS", "concept_design_decisions"),
    ("pep_635", "ADDRESSES", "concept_objections"),
    ("pep_635", "JUSTIFIES", "concept_design_choices"),
    ("pep_636", "DEMONSTRATES", "concept_pattern_matching_usage"),
]