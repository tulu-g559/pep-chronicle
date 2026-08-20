# PEP Chronicle

PEP Chronicle is a **deterministic historical design reasoner** for a focused slice of Python's PEP history. It models the design history of `structural pattern matching` (and its rejected switch/case predecessor) as an explicit knowledge graph, and it reasons over that graph when given a new, free-text Python language proposal.

No `LLM`, no `external API`, no `embeddings`, no `vector database`, no `automated
entity extraction`. 
The entity schema, extraction rules, and reasoning logic are all explicit code in this repository.

## What It Does

Python's language design history contains proposals, alternatives, objections, and decisions, but those relationships are difficult to navigate from individual PEP documents. A proposal like `match/case` is spread across several PEPs, and the rejected alternatives are usually the most informative part, yet they are the easiest to miss when reading.

[ODG <- here](https://excalidraw.com/#json=JNP7UxaOGyjqjvEvKhrzz,RRQuOutSX_zzbJePhrD8LA)

<img width="1524" height="881" alt="image" src="https://github.com/user-attachments/assets/7036b706-5ce6-4c05-8144-7c3318b300c8" />


This project models a selected slice of that history as explicit entities and relationships, then uses the resulting graph to reason about a new proposal:
```
    NEW INPUT
    "I want to introduce a new reserved keyword for pattern matching."
        |
        v
    direct design-question signals
        |
        v
    DesignQuestion
        |
        v
    DesignOptions
        |
        v
    Objections
        |
        v
    Decision
        |
        v
    PEP context
        |
        v
    Historical relationships
        |
        v
    Actionable recommendation
```

The new proposal is matched against the knowledge state. It is never
inserted into `knowledge.json`.

## Why This Subset

Five PEPs spanning fourteen years, one complete decision arc:

| PEP | Year | Status | Role |
|---|---|---|---|
| PEP 3103 | 2006 | Rejected | A Switch/Case Statement |
| PEP 622 | 2020 | Superseded | Structural Pattern Matching (original combined draft) |
| PEP 634 | 2021 | Final | Structural Pattern Matching: Specification |
| PEP 635 | 2021 | Final | Structural Pattern Matching: Motivation and Rationale |
| PEP 636 | 2021 | Final | Structural Pattern Matching: Tutorial |

PEP 3103 proposed switch/case in 2006 and was rejected after the debate
focused on dispatch semantics and implementation concerns. PEP 622 proposed
structural pattern matching in 2020, a broader feature built on
destructuring and pattern semantics. The Steering Council split it into a
specification, a motivation/rationale document, and a tutorial, and it
shipped in Python 3.10.

The two eras connect: the 2020 design still had to answer the 2006 dispatch
question, and it did so in the opposite direction, informed by the objection
that sank the 2006 approach. The graph records that with `PRECEDENT_FOR`,
`CONTRASTS_WITH`, and `INFORMED_BY`.

This is intentionally narrow. Depth matters more than breadth: individual
syntax decisions (wildcard token, OR-pattern separator, keyword hardness)
each have multiple proposed alternatives and specific objections, which is
much better ground truth for testing a reasoner than skimming hundreds of
PEPs.

## What Is Modeled

The knowledge state uses seven entity kinds:

| Entity | Purpose |
|---|---|
| Proposal | A PEP document (metadata: number, title, status, version, date, authors) |
| Feature | The language capability being discussed, separate from the document describing it |
| DesignQuestion | A specific design fork where multiple solutions were considered |
| DesignOption | A candidate solution, including rejected ones |
| Objection | An argument against an option, with its category and outcome |
| Decision | The selected option, rejected options, rationale, and source PEP |
| Concept | A supporting concept defined or explained by the PEPs |

The central structure is a design chain:

```
DesignQuestion
    -> HAS_OPTION
    -> DesignOption
    -> HAS_OBJECTION
    -> Objection

DesignQuestion
    -> RESOLVED_BY
    -> Decision
    -> CHOSE / REJECTED
    -> DesignOption
```

A question can have several competing options, each option can have several
objections, and a decision can select one option while rejecting others.
Flattening everything into "accepted" and "rejected" would throw away the
alternatives and the arguments, which is exactly the information a developer
wants when asking "has this been tried before?"

## Knowledge Representation

`knowledge.json` is the single source of truth. It is plain JSON with four
top-level keys (`schema_version`, `domain`, `entities`, `relationships`)
and is meant to be readable on its own, independent of the code:

- schema version: 1.0
- domain: Python PEP design history: structural pattern matching (match/case) and its precedent, the rejected switch statement
- 41 entities: 5 Proposals, 2 Features, 7 Concepts, 4 DesignQuestions, 11 DesignOptions, 7 Objections, 5 Decisions
- 64 relationships across 20 relation types

A small slice of what is in the file:

```json
{
  "id": "pep_622",
  "type": "Proposal",
  "title": "Structural Pattern Matching",
  "status": "Superseded",
  "python_version": "3.10"
}
```

```json
{ "source": "pep_622", "relation": "RAISES_QUESTION", "target": "q4_keyword_hardness" }
```

The graph also records the historical relationships between PEPs:

- `PRECEDENT_FOR` (pep_3103 -> pep_622)
- `CONTRASTS_WITH` (pep_3103 -> pep_622)
- `SUPERSEDED_BY` / `SUPERSEDES` (pep_622 <-> pep_634)
- `SPLITS_INTO` (pep_622 -> pep_634, pep_635, pep_636)
- `INFORMED_BY` (the 2020 dispatch decision cites the 2006 objection)

## Installation

Requirements:

- Python 3.10 or newer
- No third-party dependencies: the entire project uses the standard library
- No environment variables or configuration files

There is nothing to install. Clone the repository and run everything from
the repository root:

```bash
python cli.py "I want to introduce a new reserved keyword for pattern matching."
```

## Architecture

```
data/raw/*.rst
    |
    v
src/ingest.py       normalize, extract, merge curated content, validate
    |
    v
src/extract.py       RST section parsing, evidence-phrase rules, relationships
    |
    v
knowledge.json       curated knowledge state (source of truth)
    |
    v
src/graph.py         in-memory adjacency graph
    |
    v
src/reasoner.py      signal matching, graph traversal, scoring
    |
    v
cli.py               rendering and CLI entry point
```

### src/ingest.py

Normalizes raw text (strips BOM, NFC unicode normalization, CRLF to LF,
trailing blank lines), runs the extraction rules over each document, merges
the curated knowledge definitions, and produces a validated `KnowledgeState`
with the canonical structure consumed by `graph.py`. It can regenerate
`knowledge.json` from the raw documents:

```bash
python -m src.ingest --input data/raw --output knowledge.json
```

The state is validated before writing: duplicate entity ids and
relationships that reference unknown entities fail the build.

### src/extract.py

Deterministic, section-aware extraction rules that reproduce the knowledge
structure from the raw RST documents:

- Parses RST sections by their underline headers (===, ---, etc.).
- Applies declarative rules: each rule names section title keys, required
  evidence phrases, a relation, and a target. A relationship is emitted only
  when the section exists and the phrases are all present in it.
- `_PROPOSAL_RULES` cover the proposal level (e.g. an Abstract containing
  "pattern matching statement" emits `PROPOSES -> feature_pattern_matching`).
- `_DESIGN_CHAIN_RULES` cover full design chains (options, objections,
  decision, chosen and rejected options) for all four design questions:
  wildcard token, dispatch semantics, OR-pattern separator, and keyword
  hardness.
- `_DECISION_ONLY_RULES` cover decisions whose evidence lives in a
  different section than the main chain (e.g. d2b, the 2020 dispatch
  decision, documented in PEP 622's "use dispatch dict semantics for
  matches" section).
- PEP-structure rules derive `SUPERSEDED_BY` / `SUPERSEDES` from the
  `Superseded-By:` / `Replaces:` headers and `SPLITS_INTO` from the abstract
  of the replacement PEP.
- The PEP number is read from the `PEP:` header line, but the extractor does
  not dispatch on it. It never special-cases "if this is pep_622, emit
  everything": pep_634, 635, and 636 produce only what their content
  supports.

Extraction is reproducible but scoped. What the documents cannot state is
kept as explicit curated definitions in `src/curated.py` (feature and
concept wording, option labels, objection texts, decision rationales, and
historical links such as `PRECEDENT_FOR`, which a 2006 document cannot
reference). The pipeline merges the two layers, so regenerating
`knowledge.json` never drops the manually designed content.

### src/schema.py

Defines `Entity`, `Relationship`, and `KnowledgeState` as plain dataclasses,
plus `validate_knowledge()`, which checks for duplicate entity ids and
relationships that reference unknown entities.

### src/graph.py

Builds an in-memory adjacency structure from a `KnowledgeState` with
`outgoing` and `incoming` indexes, and exposes:

- `get_entity(entity_id)`
- `outgoing_relationships(entity_id, relation=None)`
- `incoming_relationships(entity_id, relation=None)`

`load_knowledge(path)` reads `knowledge.json` and returns a `KnowledgeGraph`.

### src/reasoner.py

The deterministic reasoning core:

- `QUESTION_SIGNALS`: a hand-curated vocabulary per design question
  (e.g. q4_keyword_hardness: "keyword", "reserved keyword", "soft keyword",
  "hard keyword", ...).
- `FEATURE_SIGNALS`: a vocabulary per feature (e.g. feature_pattern_matching:
  "pattern matching", "wildcard", "guard", ...).
- Direct vs contextual relevance: signals that belong to a DesignQuestion
  are strong evidence and determine the primary questions. A feature match
  is context only; it explains historical relatedness but never promotes
  every question raised by a matched feature to primary relevance. Only
  when no direct signal matches at all do feature-derived questions fall
  back into the primary list, explicitly marked as contextual.
- Scoring: an exact multi-word phrase scores +3, a single-word signal
  scores +1, so "reserved keyword" outweighs a bare "keyword".
- Boundary-aware matching: multi-word phrases are anchored at word
  boundaries and only allow an inflectional ending on the last word, so
  "for pattern matching" cannot match the "or pattern" signal. No raw
  substring matching.
- Graph traversal: from each selected question it walks `HAS_OPTION`,
  `HAS_OBJECTION`, `RESOLVED_BY`, `CHOSE` / `REJECTED`, collects the raising
  PEPs, PEP-to-PEP precedents, and builds recommendations from the graph
  only. Every question carries its matched-signal trace for auditability.

The reasoner is deterministic. The same input and the same knowledge state
always produce the same output.

### cli.py

Two ways to run it:

- Single-shot: `python cli.py "your proposal here"`
- Interactive: `python cli.py`, then type proposals until a blank line

Rendering covers the proposal, matched signals, relevant questions,
contextual questions, historical options and objections, decisions,
historical context, precedents, and recommendations. On Windows it
reconfigures stdout to UTF-8 so non-ASCII characters render correctly.

## Knowledge Construction

The extraction pipeline in this repository:

```
Raw PEP RST
    -> parse sections
    -> locate relevant domain-specific sections
    -> verify expected phrases
    -> emit entities and relationships
    -> validate graph
    -> knowledge.json
```

This is not automated knowledge-graph extraction in the general sense. The
extractor does not discover arbitrary entities from arbitrary documents.
Every rule names the section and the evidence phrases it is looking for, so
it only reproduces structure that was explicitly designed beforehand. The
manually designed content (wording, labels, and historical links that no
document states) lives in `src/curated.py` as explicit definitions, and the
full knowledge state is validated before it is written. `knowledge.json` is
the runtime source of truth and is never modified by the reasoning system.
The regeneration command and its verification are described in the
Regeneration section below.

To see what the current rules reproduce from the raw documents:

```bash
python -c "
from src.ingest import load_raw_documents
from src.extract import extract_relationships, extract_design_relationships
for doc in load_raw_documents():
    rels = extract_relationships(doc['text']) + extract_design_relationships(doc['text'])
    for r in rels:
        print(r.source, r.relation, r.target)
"
```

## Regeneration

`knowledge.json` is a build artifact of the deterministic pipeline. It can
be regenerated at any time from the raw PEP documents in `data/raw`:

```bash
python -m src.ingest --input data/raw --output knowledge.json
```

Expected output:

```
Loaded 5 raw PEP documents from data/raw
  PEP 622: 88429 chars
  PEP 634: 23167 chars
  PEP 635: 58226 chars
  PEP 636: 25324 chars
  PEP 3103: 24810 chars
Validated 41 entities, 64 relationships
Wrote knowledge.json
```

The pipeline normalizes each RST document, runs the section-aware
extraction rules, merges the curated definitions from `src/curated.py`,
validates the result (duplicate entity ids and relationships that reference
unknown entities fail the build), and writes the canonical structure with
the four top-level keys (`schema_version`, `domain`, `entities`,
`relationships`) that `graph.py` expects.

Verify the output shape:

```bash
python -c "import json; d = json.load(open('knowledge.json', encoding='utf-8')); print(type(d), len(d['entities']), len(d['relationships']))"
```

Regeneration is idempotent and never drops the manually designed content:
anything the documents cannot state (wording, option labels, objection
texts, and historical links such as `PRECEDENT_FOR`) is merged in from
`src/curated.py` before validation.

## Reasoning Over a New Input

```bash
python cli.py "I want to introduce a new reserved keyword for pattern matching."
```

The system matches the direct question signals (`reserved keyword`,
`keyword`) to q4_keyword_hardness, and treats the feature match on
"pattern matching" as context only:

```
MATCHED CONCEPTS
----------------
  question: q4_keyword_hardness  (keyword, reserved keyword)
  feature:  feature_pattern_matching  (pattern matching)

RELEVANT DESIGN QUESTIONS
-------------------------
1. Should match/case be hard keywords or soft (contextual) keywords?  (score 4)

CONTEXTUAL DESIGN QUESTIONS (context only)
------------------------------------------
  What token should be used for the wildcard pattern?  (score 3)
    via: [feature_pattern_matching] pattern matching
  What syntax should separate alternatives in an OR pattern?  (score 3)
    via: [feature_pattern_matching] pattern matching

HISTORICAL DECISIONS
--------------------
  d4 (pep_622): chose 'Soft (contextual) keyword'; rejected: Hard keyword
    rationale: PEG parser (PEP 617) supports backtracking, making soft
    keywords workable; avoids breaking existing code that uses match as an
    identifier (notably re.match).

HISTORICAL CONTEXT
------------------
  pep_622 — Structural Pattern Matching [Superseded, Python 3.10, 2020-06-23]

PRECEDENTS
----------
  pep_622 SUPERSEDED_BY pep_634 ('Structural Pattern Matching: Specification')
  pep_622 SPLITS_INTO pep_635 ('Structural Pattern Matching: Motivation and Rationale')
  ...
```

### What the system produces

The `reason()` function returns a structured result with:

- `signal_match`: which question and feature signals matched, plus
  unmatched terms
- `direct_questions`: question ids matched by direct signals
- `relevant_questions`: primary questions, each with `relevance_type`
  (direct or contextual), `relevance_score`, `matched_signals`,
  `historical_options` (with objections), and `decisions`
- `contextual_questions`: feature-derived questions that did not make the
  primary list
- `historical_context`: the PEPs involved
- `precedents`: PEP-to-PEP historical links
- `recommendations`: human-readable lines assembled from the graph

## CLI Usage

Two ways to run the CLI.

Single proposal as an argument:

```bash
python cli.py "I want to add a switch-style dispatch mechanism using precomputed lookup tables."
```

Interactive session (type proposals until a blank line):

```bash
python cli.py
```

The rendered output covers the proposal, matched signals, relevant and
contextual design questions, historical options and objections, decisions,
historical context, precedents, and recommendations. On Windows, stdout is
reconfigured to UTF-8 so non-ASCII characters render correctly. See
"Reasoning Over a New Input" for a full example run.

## Testing

```bash
python test_system.py
```

99 checks, all passing: knowledge state loading (41 entities, 64
relationships), retrieval of known-like inputs, novel inputs, irrelevant
inputs (no invented connections), mixed proposals, vague input handling,
knowledge.json integrity, CLI integration, and the direct vs contextual
relevance and signal-matching regression tests.

## Project Structure

```
cli.py               CLI entry point and rendering
knowledge.json       knowledge state (41 entities, 64 relationships)
test_system.py       integration and regression test suite
approach.md          design notes and rationale
data/raw/            source PEP documents as RST
src/
  schema.py          Entity, Relationship, KnowledgeState, validation
  ingest.py          regeneration pipeline: extract, merge curated, validate
  extract.py         section-aware extraction rules
  curated.py         manually designed knowledge definitions
  graph.py           in-memory knowledge graph
  reasoner.py        deterministic reasoning over new inputs
```
