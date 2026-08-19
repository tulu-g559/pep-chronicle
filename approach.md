## 1. Problem / use case

When someone proposes a new Python language feature, the history of prior
attempts is usually buried in long PEPs. The proposal's author has to read
them, find the design questions, the options that were considered, the
objections raised, and the decisions made, and then figure out which parts
apply to the new idea. That is slow, and the most informative parts are
usually the rejected alternatives, which are exactly what skimming tends to
miss.

This project is a small deterministic engine that does that retrieval for one
domain: structural pattern matching. Given a free-text proposal, the system
maps it to historical design questions, walks a knowledge graph to the
options, objections, and decisions, and returns a structured brief: what was
asked, what was tried, what was objected to, and what was eventually chosen,
plus the PEP history and precedents that make the reasoning auditable.

The constraints shape the whole design: no LLM, no external API, no
embeddings, no automated entity/relationship extraction. Every decision in
the pipeline has to be explainable in terms of signals, a graph, and
deterministic rules, which means the output can be traced end to end:

```
NEW INPUT
  -> SIGNAL
  -> DESIGN QUESTION
  -> GRAPH
  -> HISTORICAL OPTIONS
  -> OBJECTIONS
  -> DECISION
  -> PRECEDENT
  -> ACTIONABLE OUTPUT
```

## 2. Subset chosen and why

Five PEPs spanning fourteen years:

| PEP | Year | Status | Role |
|---|---|---|---|
| PEP 3103 | 2006 | Rejected | A Switch/Case Statement |
| PEP 622 | 2020 | Superseded | Structural Pattern Matching (original combined draft) |
| PEP 634 | 2021 | Final | Structural Pattern Matching: Specification |
| PEP 635 | 2021 | Final | Structural Pattern Matching: Motivation and Rationale |
| PEP 636 | 2021 | Final | Structural Pattern Matching: Tutorial |

The story that makes this subset worth building on:

PEP 3103 (2006) proposed a switch/case statement. The debate centered on
dispatch semantics and implementation concerns: how the subject should be
evaluated, whether a precomputed dict is safe given named constants, and
what happens if `hash()` has side effects. The proposal was rejected.

Fourteen years later, PEP 622 (2020) proposed structural pattern matching.
This was not the 2006 proposal repeated: it was a much larger feature built
on destructuring and pattern semantics (wildcards, OR patterns, guards,
class patterns), with a subject and a match statement on top of it. The
Steering Council split the draft into PEP 634 (specification), PEP 635
(motivation and rationale), and PEP 636 (tutorial), and the feature shipped
in Python 3.10.

What makes the pair valuable is the connection between the two eras. The
2020 design still had to answer the 2006 dispatch question, and it did so by
rejecting the approach PEP 3103 had favored, explicitly informed by the
objection that sank it. The graph captures that arc through `PRECEDENT_FOR`
and `CONTRASTS_WITH` between the two PEPs, and through `INFORMED_BY` between
the 2020 decision and the 2006 objection.

Why this subset: five documents, one complete decision arc, and unusually
rich ground truth. Individual syntax decisions (wildcard token, OR-pattern
separator, keyword hardness) each have several proposed alternatives and
specific objections that killed them. That is much better material for
testing a reasoner than skimming twenty unrelated PEPs.

## 3. Knowledge model

The knowledge state is a typed graph with seven entity kinds:

| Entity | Why it exists |
|---|---|
| Proposal | Represents a PEP so historical proposals can be connected chronologically and semantically. |
| Feature | Represents the language capability being proposed, separating the idea from the document describing it. |
| DesignQuestion | Represents a specific design fork where multiple solutions were considered. |
| DesignOption | Represents each candidate solution, including rejected alternatives. |
| Objection | Captures the concrete argument against an option rather than losing it in document text. |
| Decision | Records the selected option, rejected options, rationale, and source PEP. |
| Concept | Represents supporting concepts defined or explained by the PEPs. |

The relationships between them tell the story:

- `PROPOSES`: a Proposal puts forward a Feature.
- `RAISES_QUESTION`: a Proposal surfaces a DesignQuestion.
- `HAS_OPTION`: a DesignQuestion points at each candidate DesignOption.
- `HAS_OBJECTION`: a DesignOption points at the arguments against it.
- `RAISED_IN`: an Objection points back at the PEP where it was raised.
- `RESOLVED_BY`: a DesignQuestion points at its Decision(s).
- `CHOSE` / `REJECTED`: a Decision selects one option and rejects the rest.
- `INFORMED_BY`: a Decision cites the objection that influenced it.
- `PRECEDENT_FOR` / `CONTRASTS_WITH` / `SUPERSEDES` / `SUPERSEDED_BY` /
  `SPLITS_INTO`: chronological and semantic links between PEPs.

DesignQuestion, DesignOption, Objection, and Decision are deliberately
separate. A question can have multiple competing options, each option can
have multiple objections, and a decision can select one option while
rejecting several others. Flattening "chosen vs rejected" into two
categories would lose the alternatives that were considered and the reasons
they failed, which is exactly the information a developer wants when asking
"has this been tried before?"

## 4. Knowledge construction

I first created a manually curated knowledge state from close reading of the
five PEPs. I then implemented deterministic, section-aware extraction rules
to reproduce the relevant structure from the raw .rst documents. The
extractor identifies PEP sections and checks for domain-specific evidence
phrases before emitting entities and relationships. No NER, automated
knowledge-graph construction library, LLM, or external API is used for
entity/relationship extraction.

Tradeoffs made during construction:

- The graph does not model every sentence of the syntax specification
  (grammar rules, type details). It models the decisions with visible
  alternatives and objections, because those are what reasoning about a new
  proposal can reuse. A full grammar graph would be storage, not knowledge.
- Cross-PEP relationships (SUPERSEDES, PRECEDENT_FOR) are asserted from the
  PEPs' own metadata (for example the Replaces field) and from content, not
  inferred by a model. This keeps the provenance honest: every edge exists
  because a document says so.
- The knowledge state is intentionally small (41 entities, 64 relationships)
  and is never modified at runtime. Proposals go in, evidence comes out, and
  `knowledge.json` stays byte-identical.

## 5. Reasoning over new inputs

The current pipeline:

```
New proposal
     |
     v
Signal matching
     |
     v
Direct DesignQuestion matches
     |
     v
Feature matches for contextual information
     |
     v
KnowledgeGraph traversal
     |
     v
DesignOptions
     |
     v
Objections
     |
     v
Decisions
     |
     v
PEP history / precedents
     |
     v
Structured recommendation
```

The system does not ask an LLM to interpret the proposal. It uses a
domain-specific vocabulary of signals mapped to known features and design
questions. Multi-word signals receive higher weight than generic single-word
signals, and boundary-aware matching prevents substring errors such as
matching `or pattern` inside `for pattern matching`.

Scoring is deliberately simple and deterministic: an exact multi-word phrase
such as "reserved keyword" scores +3, a single-word signal such as "keyword"
scores +1. Direct question signals are the primary evidence and decide which
questions are relevant. Feature matches are context only: they explain why a
question is historically related, but they never promote every question
raised by a matched feature to primary relevance. Feature-derived questions
fall back to primary status only when no direct signal matched at all, and
in that case they are explicitly marked as contextual.

Every relevant question carries its evidence chain: the matched signals that
selected it, the options with their objections, the decisions with what was
chosen and rejected, and the PEPs where all of it happened. Recommendations
are then assembled strictly from the graph (`HAS_OPTION` -> `HAS_OBJECTION`
-> `RESOLVED_BY` -> `CHOSE` / `REJECTED`, plus PEP-to-PEP relations), never
from token-overlap heuristics.

## 6. Design decisions and tradeoffs

- **Deterministic instead of learned.** No LLM, embeddings, or semantic
  similarity. The cost is that the signal vocabulary only covers the
  pattern-matching and switch domain, and paraphrases outside it are missed.
  The benefit is that every selection is reproducible and explainable, which
  matters more for a historical reasoning tool than recall does.
- **Direct evidence outranks contextual evidence.** A proposal mentioning
  "pattern matching" is related to several historical questions, but
  returning all of them as equally relevant would overstate the evidence.
  Direct question signals determine primary reasoning; feature-derived
  questions are retained as context. Details in the final section.
- **Phrases weigh more than words.** "reserved keyword" is stronger evidence
  for the keyword-hardness question than "keyword" alone. The weighting is a
  plain integer (+3 / +1) so the reason for a score is visible in the trace.
- **Boundary-aware matching instead of substring matching.** The previous
  implementation matched "or pattern" inside "for pattern matching" because
  it did raw substring containment. The current matcher anchors multi-word
  phrases at word boundaries, requires exact interior words, and only allows
  an inflectional ending on the last word. False positives like the old one
  are structurally impossible now.
- **Evidence is separated from presentation.** Recommendation text passes
  through a defensive spacing fixer at render time (word before a paren,
  "n't" before a word, comma before a word), while code spans inside
  backticks are left untouched and the underlying knowledge is never edited.
- **The matched-signal trace is part of the output.** Each question exposes
  the exact signals that selected it, e.g. `[question] reserved keyword`,
  `[question] keyword`. The evaluator can see why a question was chosen
  without trusting a black box.

## 7. Limitations

- The signal vocabulary is hand-curated and domain specific. Anything
  phrased outside it gets no match, even if a human would recognize the
  intent. Adding a new question means adding signals by hand.
- There is no semantic understanding: synonyms and paraphrases that were not
  anticipated are missed, and inflection matching (via a `\w*` suffix) can
  occasionally over-match, e.g. "guard" matching "guardian". This is
  tolerated in exchange for simplicity and explainability.
- The knowledge state stops at Python 3.10. There is no post-adoption bug
  history, so the system cannot say whether historical objections proved
  valid after the feature shipped.
- Extraction is section and evidence-phrase based. An argument that is
  phrased in a way the phrase list does not cover will not become an
  Objection, and extraction has no source-span provenance yet, so a
  relationship cannot point at the exact sentence that justifies it.
- Reasoning is per-domain: the graph, the signals, and the questions are all
  about pattern matching. The machinery generalizes, the knowledge does not.

## 8. What I'd build next

With more time, I would:

1. Expand the knowledge state to additional pattern-matching design
   questions while keeping the same explicit schema.
2. Add CPython issue/bug history after Python 3.10 to determine whether
   historical objections corresponded to real post-adoption problems.
3. Model People and their roles to make authorship and design influence
   queryable.
4. Add source-span provenance to every entity and relationship so each
   piece of knowledge can be traced directly to the exact section of its
   source PEP.
5. Improve the new-input matcher from keyword signals to a larger
   deterministic domain vocabulary while preserving explainability.

Item 4 is the most valuable. It directly answers the question "can you prove
where this relationship came from?", which is the difference between a
knowledge base and an assertion. Every edge would carry a pointer into the
source document, and the audit trail in the CLI output would extend all the
way back to the .rst text.

## Most important change

The single most important change in this version is the separation of direct
from contextual relevance, which is also visible in the CLI as the
`CONTEXTUAL DESIGN QUESTIONS (context only)` section.

I distinguish direct matches from contextual matches. A proposal mentioning
"pattern matching" may be related to several historical questions, but
returning all of them as equally relevant would overstate the evidence.
Direct question signals therefore determine primary reasoning, while
feature-derived questions are retained as context.

Concretely: for the input "I want to introduce a new reserved keyword for
pattern matching", the keyword signals select `q4_keyword_hardness` as the
primary question. The feature match on "pattern matching" does still surface
the wildcard and OR-separator questions, but they are presented as context,
clearly marked, and never ranked as if they were directly requested. The
same rule in reverse: a broad input such as "I want to change Python's
pattern matching behavior" matches no direct signal, so the feature match
provides the contextual questions, each one labeled as contextual in the
output.

That distinction is the core of the reasoning design. It keeps feature
expansion useful for broad proposals while preventing the system from
claiming more evidence than the input actually provides.