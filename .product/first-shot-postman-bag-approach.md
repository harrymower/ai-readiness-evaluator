## First‑Shot Performance via Postman “Bag” + Thin Behavioral Requirements

### Executive Summary
- Goal: Achieve near‑perfect, one‑shot CLI generation against real APIs by handing the agent a curated “bag” of content, distributed inside a Postman collection.
- Approach: Provide a compact, unambiguous Postman “bag” the model can reliably act on, and measure success with a thin set of evaluator‑only behavioral requirements plus capability coverage derived from the bag.
- Outcome: A reproducible way to discover the minimal content needed for first‑shot success, and to ship that content as part of a Postman collection.

---

## Objectives
1) Measure: Can the model build a working CLI (real API calls, no mocks) on the first try?
2) Discover: What minimal content in the Postman collection (“bag”) makes that possible consistently across APIs?
3) Operationalize: Auto‑generate and ship that bag inside Postman so other agents/users get the same benefit.

---

## The “Bag” We Give the Agent (Inside Postman)
A structured, lightweight package that removes ambiguity and optimizes for direct code synthesis:

- Capability manifest (machine‑readable)
  - Endpoints, key query params, allowed values, and which combinations matter
  - Minimal CLI mapping: flags → params, subcommands → endpoints
- Executable examples (success + error)
  - Concrete requests with real responses for happy paths and common failures (404, invalid param)
  - Pagination/filters samples when relevant
- Auth and runtime guidance
  - Env var names (e.g., OMDB_API_KEY), usage pattern, and a safe sample invocation
  - Small retry/timeout/rate‑limit policy
- Behavior norms (tiny, explicit rules)
  - Exit codes on typical failures
  - Required key output fields and formatting preference (JSON vs pretty)

Example minimal manifest (embedded as a Postman variable or a documentation block):

```json
{
  "endpoints": [
    {"name": "movie_by_title", "path": "/", "params": ["t","y","type","plot"]}
  ],
  "cli_flags": {"--title":"t","--year":"y","--type":"type","--plot":"plot"},
  "required_fields": ["Title","Year","Type"],
  "auth_env": "OMDB_API_KEY"
}
```

---

## How We Measure (Evaluator‑Only)
A. Thin behavioral requirements (stable, non‑negotiables)
- Real API calls only; happy path succeeds
- Clear auth behavior (read key from env; fail cleanly if missing/invalid)
- Basic error policy (404/invalid input → non‑zero exit with useful message)
- A few must‑show fields in output for the primary endpoint

B. Capability coverage (derived from the bag)
- From the manifest, sample a subset of params/endpoints and verify:
  - The CLI exposes matching flags/subcommands
  - At least one real call per sampled capability succeeds and surfaces expected fields

Why this balance?
- The thin YAML avoids overfitting to our own rubric.
- Coverage is grounded in the Postman bag (the same source the agent sees), not an external, hand‑crafted spec.

---

## Alignment With Goals
- First‑shot integrity: The model still gets a single attempt; we simply give it the right structured inputs.
- Discover the minimal content: Ablate bag components and observe score deltas to identify the smallest set that yields near‑perfect results.
- Portable delivery: The bag lives in Postman, so it can be auto‑generated, versioned, and shared.

---

## Evaluation Workflow (High‑Level)
1) Prepare round inputs
   - R1: curl only
   - R2: curl + docs
   - R3: curl + docs + Postman (baseline bag)
   - R4 (optional): curl + docs + Postman (enhanced bag variants for ablation)
2) Claude generates CLI (single shot) using provided round content
3) Run evaluator
   - Execute thin behavioral requirements (real calls)
   - Execute capability coverage checks derived from bag manifest (sampled)
4) Report
   - Separate scores: Baseline checks vs. Capability coverage
   - Diagnostics mapped back to specific bag components

---

## Scoring Model (Illustrative)
- Baseline behavioral checks: 30–40 points
  - Happy path, auth handling, error exit codes, required fields
- Capability coverage: 60–70 points
  - Flags/params presence (exposed by CLI): 20
  - Successful real calls for sampled params/endpoints: 30–40
  - Pagination/search/filters (when applicable): 10

Notes:
- Weights can be tuned per API family.
- Coverage sampling keeps runs fast while still measuring “taking advantage of functionality.”

---

## Experiment Plan (to find the minimal bag)
- Start with a baseline Postman bag (auth + happy‑path example + minimal manifest)
- Incrementally add components and re‑evaluate:
  1) Add CLI mapping (flags → params)
  2) Add error examples and exit‑code guidance
  3) Add parameterized examples (year/type/plot, etc.)
  4) Add pagination/search recipes (if applicable)
  5) Add retry/timeout policy
- Record score deltas to isolate which elements materially improve one‑shot success.

---

## Implementation Roadmap
- Short‑term
  - Maintain thin behavioral_requirements per API (evaluator‑only)
  - Keep/extend BehavioralValidator for baseline checks (already added)
  - Define a minimal bag manifest schema and embed it as a Postman variable/documentation block
  - Build capability coverage runner that reads the manifest and performs sampled validations
- Mid‑term
  - Auto‑generate bag content from API sources (curl, docs, OpenAPI/Postman) with small manual curation
  - Integrate bag/scoring into comparison reports (separate baselines vs coverage) and transcripts
- Long‑term
  - Standardize bag generation across APIs; publish guidance/templates
  - Provide ablation toggles and presets to rapidly test new bag variants

---

## Risks & Mitigations
- Risk: Over‑prescriptive bag reduces generality
  - Mitigation: Keep manifest small; focus on high‑signal hints (auth, flags, examples)
- Risk: YAML rubric drift
  - Mitigation: Freeze thin baseline; drive most coverage from the manifest the agent also sees
- Risk: Auth/env brittleness (e.g., OMDB demo key)
  - Mitigation: Always specify env var names; include clear failure mode in bag + baseline check

---

## Success Criteria
- Consistent >90/100 first‑shot scores on target APIs with the minimal bag
- Clear attribution of improvements to specific bag components (via ablation deltas)
- Reusable, automated Postman bag generation with documented schema and examples

---

## Open Questions
- How much pagination/search support should be required for Tier‑1 coverage across APIs?
- Standard exit‑code policy across APIs or per‑API variance?
- Where to store the manifest (collection variable vs. documentation block) for best agent consumption?

