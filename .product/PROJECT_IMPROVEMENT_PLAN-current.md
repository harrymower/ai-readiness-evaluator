# AI Readiness Evaluator – Improvement Plan (Component-Based Experiment)

Plain language version. Goal: Flesch score ~67.

## Executive Summary

We want to learn the best “package” of information to give an AI agent (Claude) so it can build a working tool for any API. We will focus on the “content components” we put into the prompt. We will run a fair, controlled experiment across many APIs. We will test different combinations of components to learn which ones matter most, and for which kinds of APIs.

This plan replaces a fixed four-round staircase with a component-based experiment. It adds a simple normalization step so every API can be fed to the agent using the same building blocks. It uses a smart experimental design to keep the number of runs reasonable and to reduce noise.

The outcome is two things:
1) A publishable set of results that shows which components drive success.
2) A clear recipe our product can use to auto-generate the right package for any API.

---

## Goals

- Find out which content components (like schema, examples, usage patterns) actually help agents build against APIs.
- Learn the “best package” for simple, moderate, and complex APIs.
- Keep the experiment fair and reliable.
- Produce findings that are useful in the real world, not just in perfect lab settings.

---

## What We Will Test: The Standard Component Set

We will normalize any API into the same set of prompt-ready files. Some may be empty for a given API. That’s OK. The goal is a predictable shape so we can turn components on and off in tests.

Why these components (and how we’ll validate them)
- This set mirrors the most common failure modes we see in agent-written API clients: wrong fields/parsing (schema), wrong endpoint/params (endpoint docs), brittle behavior (no error/rate guidance), auth failures (auth sheet), lack of concrete grounding (examples), and unclear task framing (usage patterns).
- It also matches what human developers ask for when learning an API: a reference call, a definition of shape, a few real examples, how to authenticate, how to handle errors/limits, and clear tasks.
- Industry practice supports this: modern SDK generators and tools like OpenAPI/Swagger, Postman, and API portals provide these same elements because they reduce developer friction.
- We will not assume this set is “right.” The experiment explicitly tests their effect sizes and interactions. After the pilot, we will keep, drop, or add components based on measured impact.

- baseline_curl.txt
  - The core curl command(s). Always present. This is the baseline.
- schema.yaml
  - Machine-readable structure of endpoints and responses.
  - Source: OpenAPI if available; else we infer a minimal schema from captured examples.
- endpoint_docs.md
  - Human-readable endpoint descriptions and parameter notes. Scraped or cleaned.
- examples.jsonl
  - Request/response pairs (one per line). From Postman or captured by running curl.
- auth.md
  - How to authenticate (key headers, token steps, refresh).
- error_matrix.yaml
  - Common error codes and messages, plus guidance (“retry,” “fix param,” “re-auth”).
- rate_limits.yaml
  - Limits and backoff rules. Simple, clear instructions.
- usage_patterns.md
  - 2–3 specific “tasks” a developer actually does (e.g., “Get user by username and show public_repos”).
- postman_collection.json
  - Included if available as an extra reference (not always present).

These pieces are what we “give” the agent inside a structured prompt.

---

## Normalization Pipeline (Plain English)
Normalization means: take whatever we have and produce the standard component files above, in a predictable folder:



normalized/<api_name>/
- baseline_curl.txt
- schema.yaml
- endpoint_docs.md
- examples.jsonl
- auth.md
- error_matrix.yaml
- rate_limits.yaml
- usage_patterns.md
- postman_collection.json (optional)

Notes (clarifications)
- We do not “simulate” missing components. If a component cannot be produced from real sources, we leave it empty.
- “Infer schema” means deriving a minimal structure from real, captured responses (a measurement step), not fabricating a full spec.
- “Run baseline curl” means harvesting at least one actual request/response pair so the agent has a concrete example. This is also a measurement step, not a simulation.
- Scraping HTML docs is a transformation step to make unstructured text usable; we keep links back to sources for traceability.

- If a component cannot be produced, leave it empty.
- If there is no spec, infer schema from example responses.
- If there are no examples, run the baseline curl to capture at least one working request/response pair.
- If docs are only HTML, scrape and clean enough to produce endpoint_docs.md.
- usage_patterns.md should be practical tasks a developer would build, not marketing text.

Why this helps: now all APIs look the same to our experiment harness and prompt builder.

---

## Prompt Assembly (What We Actually Feed to the Agent)

Why this prompt structure (and how we’ll test alternatives)
- Agents respond better to consistent sectioning and clear delimiters. Grouping by component reduces “context soup” and helps the model retrieve the right piece at the right time.
- Putting examples and schema near each other reduces hallucinated fields and improves parsing accuracy (an observed pattern in LLM coding tasks).
- We will treat this as our baseline prompt shape for controlled comparisons. In a secondary A/B, we will try alternative layouts (e.g., examples-first vs schema-first, merged docs+schema sections) to confirm the structure itself is not the driver.
We will build a structured prompt from the normalized components, like this:

System: You are building a Python CLI tool for the API below. Use the provided sections. Do not assume undocumented behavior.

Context:
[BASELINE_CURL]
…baseline_curl.txt…

[SCHEMA]
…schema.yaml…

[ENDPOINT_DOCS]
…endpoint_docs.md…

[EXAMPLES]
…examples.jsonl (first N examples)…

[AUTH]
…auth.md…

[ERROR_MATRIX]
…error_matrix.yaml…

[RATE_LIMITS]
…rate_limits.yaml…

[USAGE_PATTERNS]
…usage_patterns.md…

Task:
1) Build cli_tool.py
2) Build test_cli_tool.py using real API calls
3) Follow the schema and examples for parsing
4) Handle auth/rate limits/errors if those sections exist

The experiment will toggle sections on/off based on each test condition.

---

## Experimental Design (Plain English)

### Why we need a smarter design than “try everything”

If we have 6–8 components, testing every on/off combination would be 2^N. That grows too fast. We will use a “fractional factorial design” to pick a small, smart set of combinations that still lets us estimate which components matter most.

### Components for the first study (6 knobs)

We will start with these six (others can be added later once the harness is working):

Why these 6 knobs first
- They map to the clearest, independent levers we can toggle without creating overlap: structure (S), human guidance (D), grounding (E), access (A), resilience (R), and intent framing (U).
- They are also the most feasible to produce across many APIs in a consistent way.
- Starting with 6 keeps the design tractable (16 conditions vs 64). After the pilot, we will add or remove components based on observed effect sizes.

- S = schema.yaml
- D = endpoint_docs.md
- E = examples.jsonl
- A = auth.md
- R = error_matrix.yaml
- U = usage_patterns.md

We will always include baseline_curl.txt (the agent needs at least one reference call). postman_collection.json is optional and can be folded into “examples” as a source.

### Number of conditions

- Full combinations: 2^6 = 64 (too many per API).
- Use a fractional factorial (Resolution IV) with 16 conditions.
- This lets us estimate all main effects and some two-way interactions without testing all 64 combinations.

### Replication and randomization

- Replicate each condition 2 times (or 3 if time allows) to reduce randomness.
- Randomize the order of conditions per API.
- Randomize the order of APIs across days and runs.
- Record seeds and timestamps so runs are reproducible.

### Blocking (fair comparison by complexity)

APIs differ in complexity. To reduce noise, we will group APIs into simple, moderate, and complex using simple proxy signals:

- auth present? (yes = harder)
- endpoints count (more = harder)
- schema depth (more nesting = harder)
- average response size (larger = harder)
- pagination present? (yes = harder)
- error surface (more unique 4xx/5xx = harder)

Are there more signals?
- These are the starting signals for blocking. We will also log and may later include: auth type (OAuth vs API key), number of required parameters, required headers, presence of multipart/file upload, streaming responses, average latency/variance, and pagination style. We begin simple to avoid overfitting and add signals only if they improve explanatory power.

We compute a simple score and bucket:
- Simple: score 0–3
- Moderate: score 4–6
- Complex: score 7+

We analyze results within each bucket first, then roll up to an overall view. This gives us “recipes that work well” by API complexity.

---

## What We Will Measure

We will measure more than pass/fail:

- Task success (binary): Did the tool complete the defined task?
- Independent test pass rate: Tests authored separately from Claude (not by the same run) to avoid “grading its own work.”
- Time-to-first-pass: How long until the first successful test run? (Signals developer speed)
- Behavioral score: Did the tool follow auth, errors, rate limits, etc.?
- Error type distribution: Where do things fail? (auth, parsing, timeouts)
- Mock vs real drift: How often does something pass against a mock but fail against the real API? (Flags fidelity issues)

We will still use a small real-API subset to validate that our mocks are not too forgiving.

---

## Pilot Run (Sane Size)

- Components: 6 (S, D, E, A, R, U)
- Design: 16 conditions (fractional factorial)
- Replicates: 2
- APIs: 12 total (4 simple, 4 moderate, 4 complex)

Pilot workload:
12 APIs × 16 conditions × 2 reps = 384 runs
This is large but doable in batches over a few days.

If pilot looks good, we scale to 40–60 APIs using the same setup.

---

## Key Guardrails

- Independent tests: Do not let the same agent run write both the solution and the tests without checks. Use an independent test author (human or separate constrained LLM) with rules.
- Real-API validation subset: Always run a subset against the real API to keep mocks honest.
- Health gating: Probe endpoints and log rate limits and latency. If an outage occurs, tag those runs and do not count them as agent failures.
- Randomization: Shuffle run order to avoid time-of-day and quota bias.
- Run ledger: For every run, log API, bucket, condition ID, components included, start/end times, network health, outcome, and metrics.

---

## What the Results Should Tell Us

- Main effects: “Examples add +18 points on average.” “Schema adds +12.” “Usage patterns add +8” etc.
- Interactions (some): “Schema + examples together add more than either alone (+7 synergy).”
- By complexity: “For simple APIs, examples and patterns are the biggest lift. Docs add little.” “For complex APIs, auth + schema are non‑negotiable, and error/rate guidance adds stability.”

These become the “recipes” our product will build for each API class.

---

## Phases and Deliverables

### Phase 0: API Selection (Pre-Implementation)
Goal: Decide which APIs to include.
- Review current 24 APIs in config/apis.txt.
- Add more if needed to reach 12 for pilot (balanced by complexity).
- Deliverable: api_list.json with bucket labels (simple/moderate/complex).
- Acceptance: 12 APIs minimum with balance across buckets.

**GitHub Issues:**
- [#6: Phase 0.1 — Audit current APIs and gather basic signals for bucketing](https://github.com/harrymower/ai-readiness-evaluator/issues/6)
- [#7: Phase 0.2 — Score and bucket APIs into simple/moderate/complex](https://github.com/harrymower/ai-readiness-evaluator/issues/7)
- [#8: Phase 0.3 — Select final pilot set of 12 APIs balanced across buckets](https://github.com/harrymower/ai-readiness-evaluator/issues/8)
- [#9: Phase 0.4 — Produce api_list.json with bucket labels](https://github.com/harrymower/ai-readiness-evaluator/issues/9)

### Phase 0.1: Normalization + Component Builder
Goal: Turn each API into the standard component set.
- Build scripts to extract or infer:
  - schema.yaml (spec or inferred)
  - endpoint_docs.md (scraped/cleaned)
  - examples.jsonl (captured or from Postman)
  - auth.md / error_matrix.yaml / rate_limits.yaml (basic templates if unknown)
  - usage_patterns.md (2–3 concrete tasks)
- Keep baseline_curl.txt always present.
- Deliverable: normalized/<api_name> folders.
- Acceptance: 100% of pilot APIs have a complete folder; empty files allowed where data does not exist.

**GitHub Issues:**
- [#10: Phase 0.1.1 — Create normalization folder structure and templates](https://github.com/harrymower/ai-readiness-evaluator/issues/10)
- [#11: Phase 0.1.2 — Build baseline_curl.txt extractor](https://github.com/harrymower/ai-readiness-evaluator/issues/11)
- [#12: Phase 0.1.3 — Build schema.yaml generator (OpenAPI or inferred)](https://github.com/harrymower/ai-readiness-evaluator/issues/12)
- [#13: Phase 0.1.4 — Build endpoint_docs.md scraper/cleaner](https://github.com/harrymower/ai-readiness-evaluator/issues/13)
- [#14: Phase 0.1.5 — Build examples.jsonl collector](https://github.com/harrymower/ai-readiness-evaluator/issues/14)
- [#15: Phase 0.1.6 — Build auth.md, error_matrix.yaml, rate_limits.yaml generators](https://github.com/harrymower/ai-readiness-evaluator/issues/15)
- [#16: Phase 0.1.7 — Build usage_patterns.md generator](https://github.com/harrymower/ai-readiness-evaluator/issues/16)
- [#17: Phase 0.1.8 — Validate and complete all normalized/ folders](https://github.com/harrymower/ai-readiness-evaluator/issues/17)

### Phase 1: Experiment Harness + Design
Goal: Be able to run controlled combinations.
- Implement fractional factorial design (16 conditions for S/D/E/A/R/U).
- Add prompt assembler to include/exclude components per condition.
- Add randomization of conditions and APIs.
- Add run ledger and logging.
- Deliverables: design_matrix.json, run_harness.py, run_ledger.csv.
- Acceptance: Dry run over 2–3 APIs completes without manual intervention.

**GitHub Issues:**
- [#20: Phase 1.1 - Design and generate fractional factorial design matrix](https://github.com/harrymower/ai-readiness-evaluator/issues/20)
- [#21: Phase 1.2 - Build prompt assembler with component toggling](https://github.com/harrymower/ai-readiness-evaluator/issues/21)
- [#22: Phase 1.3 - Implement randomization for conditions and APIs](https://github.com/harrymower/ai-readiness-evaluator/issues/22)
- [#23: Phase 1.4 - Build run ledger and logging system](https://github.com/harrymower/ai-readiness-evaluator/issues/23)
- [#24: Phase 1.5 - Build health gating and API probing](https://github.com/harrymower/ai-readiness-evaluator/issues/24)
- [#25: Phase 1.6 - Build core experiment harness](https://github.com/harrymower/ai-readiness-evaluator/issues/25)
- [#26: Phase 1.7 - Build independent test framework](https://github.com/harrymower/ai-readiness-evaluator/issues/26)
- [#27: Phase 1.8 - Build mock vs real validation system](https://github.com/harrymower/ai-readiness-evaluator/issues/27)
- [#28: Phase 1.9 - Dry run validation over 2-3 APIs](https://github.com/harrymower/ai-readiness-evaluator/issues/28)

### Phase 2: Pilot Study (12 APIs × 16 × 2)
Goal: Prove signal and feasibility.
- Run the full pilot with health gating and retries.
- Use independent tests and a real-API validation subset.
- Deliverables: pilot_results.json, pilot_report.md.
- Acceptance: Stable main effects found with consistent patterns; mock vs real drift < 10% for passing runs.

**GitHub Issues:**
- [#29: Phase 2.1 - Prepare 12 pilot APIs with complete normalization](https://github.com/harrymower/ai-readiness-evaluator/issues/29)
- [#30: Phase 2.2 - Create independent tests for all 12 pilot APIs](https://github.com/harrymower/ai-readiness-evaluator/issues/30)
- [#31: Phase 2.3 - Execute pilot study (384 runs)](https://github.com/harrymower/ai-readiness-evaluator/issues/31)
- [#32: Phase 2.4 - Run real-API validation subset](https://github.com/harrymower/ai-readiness-evaluator/issues/32)
- [#33: Phase 2.5 - Analyze pilot results and generate report](https://github.com/harrymower/ai-readiness-evaluator/issues/33)
- [#34: Phase 2.6 - Gate 2 decision: Evaluate pilot success](https://github.com/harrymower/ai-readiness-evaluator/issues/34)

### Phase 3: Scale Study (40–60 APIs)
Goal: Increase statistical power and generality.
- Expand to more APIs while keeping balance across complexity buckets.
- Use the same design and harness.
- Deliverables: study_results.json, study_report.md (publishable).
- Acceptance: Clear component effect sizes and “winning recipes” per bucket.

**GitHub Issues:**
- [#35: Phase 3.1 - Expand API set to 40-60 APIs with balanced buckets](https://github.com/harrymower/ai-readiness-evaluator/issues/35)
- [#36: Phase 3.2 - Normalize all scale study APIs](https://github.com/harrymower/ai-readiness-evaluator/issues/36)
- [#37: Phase 3.3 - Create independent tests for all scale study APIs](https://github.com/harrymower/ai-readiness-evaluator/issues/37)
- [#38: Phase 3.4 - Execute scale study (1280-1920 runs)](https://github.com/harrymower/ai-readiness-evaluator/issues/38)
- [#39: Phase 3.5 - Run real-API validation for scale study](https://github.com/harrymower/ai-readiness-evaluator/issues/39)
- [#40: Phase 3.6 - Analyze scale study results and generate publishable report](https://github.com/harrymower/ai-readiness-evaluator/issues/40)
- [#41: Phase 3.7 - Gate 3 decision: Evaluate scale study success](https://github.com/harrymower/ai-readiness-evaluator/issues/41)

### Phase 4: “Winning Recipes” and Guidance
Goal: Produce recommendations we can implement in the product.
- Summarize best packages per complexity class:
  - Simple: examples + schema + patterns
  - Moderate: schema + examples + auth + error matrix
  - Complex: schema + auth + examples + rate limits + error matrix + patterns
- Deliverables: recipes.yml, guidance.md.

**GitHub Issues:**
- [#42: Phase 4.1 - Extract winning recipes from scale study results](https://github.com/harrymower/ai-readiness-evaluator/issues/42)
- [#43: Phase 4.2 - Create recipes.yml specification](https://github.com/harrymower/ai-readiness-evaluator/issues/43)
- [#44: Phase 4.3 - Generate guidance.md documentation](https://github.com/harrymower/ai-readiness-evaluator/issues/44)
- [#45: Phase 4.4 - Validate recipes against held-out APIs](https://github.com/harrymower/ai-readiness-evaluator/issues/45)

### Phase 5: Product Stub (Optional but Useful)
Goal: Prove we can package this for real use.
- Build a CLI or module that takes an API’s raw resources, runs normalization, and outputs a prompt package following the “recipe” for its class.
- Acceptance: Given a new API input, produce a package and pass the independent tests for at least one task.

**GitHub Issues:**
- [#46: Phase 5.1 - Design product CLI architecture](https://github.com/harrymower/ai-readiness-evaluator/issues/46)
- [#47: Phase 5.2 - Build API classifier module](https://github.com/harrymower/ai-readiness-evaluator/issues/47)
- [#48: Phase 5.3 - Build recipe selector module](https://github.com/harrymower/ai-readiness-evaluator/issues/48)
- [#49: Phase 5.4 - Build prompt package generator](https://github.com/harrymower/ai-readiness-evaluator/issues/49)
- [#50: Phase 5.5 - Build end-to-end CLI tool](https://github.com/harrymower/ai-readiness-evaluator/issues/50)
- [#51: Phase 5.6 - Validate product stub with new APIs](https://github.com/harrymower/ai-readiness-evaluator/issues/51)

---

## Success Metrics

- Clarity: We can say “These three components matter most for simple APIs; these five for complex APIs.”
- Effect size: Show how much each component lifts success (and time-to-first-pass).
- Robustness: Results hold across API buckets; mock vs real drift < 10% for pass/fail.
- Reproducibility: Independent replication on a subset produces similar results.

---

## Risks and Mitigations

- Messy inputs: Some APIs have light docs or no examples. Mitigation: allow empty components; still include them in runs.
- API flakiness: Rate limits and downtime can bias results. Mitigation: health gating, randomization, retries, drift tagging.
- Too many runs: Full factorial explodes. Mitigation: fractional factorial; pilot first; scale gradually.
- Circular validation: If the agent writes the tests, results can be biased. Mitigation: independent test authoring, real-API subset.

---

## Decision Gates

- Gate 1 (after Phase 0.1): Can we normalize at least 12 APIs cleanly? If not, adjust scope or improve scraping/inference.
- Gate 2 (after Phase 2): Do we see strong, consistent effects across components? If not, revisit component definitions or prompt assembly.
- Gate 3 (after Phase 3): Are results stable across buckets, and is real validation close to mocks? If not, tighten fidelity or increase real runs.
- Gate 4 (before Phase 5): Do we have recipes we trust? If yes, proceed to product stub.

---

## Appendix: Component File Templates (Lightweight)

- baseline_curl.txt
  - One curl per line. Keep it copy-paste friendly.

- schema.yaml
  - OpenAPI 3.0 if available; else a minimal schema: endpoints, params, key response fields.

- endpoint_docs.md
  - Bullet lists with endpoint, params (name, type, required), and a short description.

- examples.jsonl
  - One JSON object per line:
    {"request": {"method": "GET", "url": "...", "headers": {...}, "body": null}, "response": {"status": 200, "headers": {...}, "json": {...}}}

- auth.md
  - “Use header X-Api-Key: $KEY. Keys do not expire.” Or “OAuth2: client credentials flow, token endpoint ….”

- error_matrix.yaml
  - - code: 401
      message: Unauthorized
      action: “Re-authenticate with a valid token”

- rate_limits.yaml
  - limit: “60 requests/hour”
  - backoff: “exponential: 1s, 2s, 4s…”
  - headers: [“X-RateLimit-Remaining”, “X-RateLimit-Reset”]

- usage_patterns.md
  - Pattern 1: “Get user by username and print public_repos”
    Steps: …
    Expected fields: …

- postman_collection.json
  - As-is if present.

---

## Appendix: References & Prior Art (Selected)

Industry guidelines and API design references
- OpenAPI Initiative. OpenAPI Specification. Rationale for machine-readable schemas, parameter definitions, and example payloads. https://www.openapis.org
- Microsoft REST API Guidelines. Emphasis on error models, pagination, versioning, and consistency. https://github.com/microsoft/api-guidelines
- Google API Design Guide. Strong conventions for resource modeling, errors, and usage patterns. https://cloud.google.com/apis/design
- Stripe API Reference and Style Guide. Widely cited for clear errors, rate limits, examples, and consistency. https://stripe.com/docs/api
- GitHub REST API v3 Docs. Clear error payloads and rate limit headers (X-RateLimit-*). https://docs.github.com/rest

Error and rate-limit practices
- RFC 7807: Problem Details for HTTP APIs (standardized error payload shape). https://www.rfc-editor.org/rfc/rfc7807
- RFC 7231: HTTP/1.1 Semantics (status codes and semantics). https://www.rfc-editor.org/rfc/rfc7231
- Exponential backoff for transient errors (industry standard; documented by Google Cloud and AWS). https://cloud.google.com/storage/docs/retry-strategy, https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter

Developer onboarding and API portals
- Postman API Lifecycle/Design Guidelines: examples and collections improve time-to-first-success. https://www.postman.com/api-platform
- Stoplight/Prism (mocking from OpenAPI) demonstrates value of examples and schema for testing and onboarding. https://github.com/stoplightio/prism
- Twilio/SendGrid/Stripe developer docs emphasize: “quick-start (curl), schema/reference, examples, and usage patterns” to reduce friction.

LLM and program synthesis references (components that help)
- Chen et al., “Evaluating Large Language Models Trained on Code” (HumanEval): structured prompts and examples improve code success.
- OpenAI Function Calling and Tool Use docs: structured schemas and example payloads reduce hallucinations and improve tool calls.
- Prompt engineering best practices (OpenAI/Anthropic/Google): worked examples (few-shot), explicit constraints, and sectioned context raise accuracy.

Notes on evidence level
- The items above motivate the initial component set: schema (structure), examples (grounding), endpoint docs (human guidance), auth/rate/errors (operational robustness), and usage patterns (task framing).
- Our experiment is designed to measure effect sizes and interactions so we do not rely only on prior art. After the pilot, we will keep/drop/refine components based on data.

## Closing

This plan is built for both science and shipping. We will stop guessing. We will test the components that make up a “good cookbook” for the agent. We will learn what works best for different kinds of APIs. And we will turn those findings into a product that can auto-generate the right package for API owners.

Once you approve, I will:
- Add Phase 0.1 and the experiment harness to the repo plan.
- Create templates and stubs for normalization outputs.
- Propose the exact 16-condition matrix for the six components.
