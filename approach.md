# approach.md

## 1. Subset chosen and why
Python's structural pattern matching (`match`/`case`), tracked across:
- PEP 3103 (2006, Rejected) — earlier switch/case proposal
- PEP 622 (2020, Superseded) — original combined pattern matching proposal
- PEP 634 (2021, Final) — specification
- PEP 635 (2021, Final) — motivation & rationale
- PEP 636 (2021, Final) — tutorial

Why this subset: it's small (5 documents) but has a complete decision
arc — an idea rejected in 2006 for [semantic reason X], revived in
2020 with a materially different design, split into 3 documents by
the Steering Council for clarity, and finalized in 3.10. Depth over
breadth: I can trace individual syntax decisions (wildcard token,
OR-pattern separator, keyword hardness) to specific alternatives that
were proposed and specific objections that killed them — this is
richer ground truth than skimming 20 unrelated PEPs.

## 2. Entities and relationships modeled — and why
[Paste your schema table here. For each entity, one sentence on why
it exists: e.g. "DesignQuestion and DesignOption are separated from
Decision because a single question often has 3+ competing options,
and modeling them as siblings under a Decision node — rather than
flattening 'chosen vs rejected' into two categories — lets the system
surface ALL alternatives someone considered, not just the winner,
which is closer to what a developer actually wants when asking 'has
this been tried before.'"]

## 3. How the knowledge representation was built, and tradeoffs
- Manual extraction: I read each PEP's "Rejected Ideas" / "Alternatives"
  sections and hand-coded each into DesignQuestion/DesignOption/
  Objection/Decision tuples in knowledge.json. No NER/LLM auto-extraction
  used, per constraint.
- Tradeoff: I did NOT model every sentence of syntax spec (types,
  grammar rules) as entities — only the *decisions with visible
  alternatives and objections*, since those are what's reusable for
  reasoning about a *new* proposal. A full grammar graph would be
  storage, not knowledge.
- Tradeoff: cross-PEP relationships (SUPERSEDES, PRECEDENT_FOR) were
  asserted by me from reading the PEPs' own metadata (Replaces: field)
  and content, not inferred automatically.

## 4. How the system reasons over new input
[Describe once built — e.g.: user describes a new proposed feature
in free text. System does keyword/concept matching (yours, not an
NER library) against Feature and DesignQuestion nodes to find related
clusters, then walks HAS_OPTION → HAS_OBJECTION → Decision to produce
a structured brief: similar past proposals, questions the new idea
will likely face, objections historically raised against similar
options, and how they were resolved.]

## 5. What I'd build next
- Extend to PEP 636 tutorial content for beginner-friendly explanation
  generation
- Add People/Author network across PEPs
- Weight objections by whether the concern proved valid post-adoption
  (needs post-3.10 bug tracker data — out of scope for 3 days)