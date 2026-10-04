# pivot.

**An arbitration engine for contradictory case law.**
Legal research tools find precedents. Pivot decides between them: it aligns the client's facts with each decision, weighs the precedents, and tells the lawyer which way the case leans, how sure it is, and *which missing fact would change the answer*.

> **The LLM extracts, the code decides.** Mistral reads documents and decisions; a deterministic, testable engine does the weighing. Every number on screen can be traced to a fact, a decision and a quoted excerpt.

*LLM x Law Hackathon Paris #2 — Mistral AI × Stanford Law School.*

---

## The demo: one legal question, end to end

The hackathon demo covers **a single, deliberately narrow question**: *is a platform worker an employee under French law?* (requalification of gig-economy couriers and drivers).

| | |
|---|---|
| **Corpus** | 12 decisions of the French Cour de cassation (2018–2025), official texts — 9 for employment, 3 for independence |
| **Grid** | 18 legally relevant factors (real-time tracking, account deactivation, price setting, freedom to work for competitors…) |
| **Scenario** | An M&A due-diligence on a delivery platform (*UrbanShift*): the lawyer pastes the case and attaches the data room |

What the lawyer sees:
1. **A leading position** — e.g. *Independence 65 %*, with its 95 % interval, flagged *Uncertain* and *Provisional*.
2. **Questions for the data room** — the unknown facts that would flip the outcome, ranked by impact (*"Can the platform suspend an account for refusals? If yes 63 % employment · if no 15 %"*).
3. **The pivot** — answering *Yes* moves the balance live; precedents that no longer apply (here, Uber 2025, where refusals had no consequence) are distinguished and excluded, with the reason.
4. **The evidence** — for every fact and every decision, the verbatim excerpt it rests on.

## Built for any use case

**The platform-worker question is an example, not the product.** Everything that is specific to it lives in two places:

| Specific to the demo | Generic (unchanged for a new question) |
|---|---|
| `contracts/grille.json` — the factors for *this* question, with their legal orientation and weight | Fact extraction (prompts are generated from the grid) |
| `data/fiches/` — the validated decisions for *this* question | The calculator (Bayesian model, pivots, distinguishing, a fortiori reading) |
| | The REST API, the MCP server, the dashboard (labels come from the grid) |

**Adding a new legal question** (unfair commercial termination, non-compete clauses, GDPR fines…) takes three steps and no code change: a lawyer writes the grid, `back.ingerer` extracts the decisions, a reviewer validates them.

The engine is also **jurisdiction-aware**: each decision carries its country, and a common-law precedent weighs far less in a civil-law case (×0.08), and vice versa (contract v1.4).

### Data sources: Legora — out of scope today, next step tomorrow

For the hackathon, the corpus is closed: Legora's research export (`dataset-legora/`) and the official texts it points to. **Scaling to any question means plugging Pivot into a case-law source**, and the architecture already has both doors:

- **Legora's database** → our ingestion pipeline already consumes Legora's structured export as extraction hints; a direct connection replaces the export with a live feed.
- **MCP, both ways** → Legora agents (or Le Chat, Claude…) call Pivot's tools (`pivot_structurer_cas`, `pivot_etat_du_droit`, `pivot_arbitrer`); or Pivot queries Legora through MCP to fetch the precedents to arbitrate.

> *Legora searches, Pivot arbitrates.* This integration is **outside the hackathon scope** and is the first thing we build next.

## How it works

```
 front (Next.js)  ──REST──►  back (FastAPI)  ──────────►  calculator (Python)
 prompt + files              • reads TXT/PDF/DOCX         • distinguishing: excludes precedents
 answer-first dashboard      • Mistral extracts facts       whose decisive fact differs
 live "what if"              • stores cases & decisions   • Bayesian logistic regression,
                             • MCP server for agents        prior = the lawyer's grid
                                                          • pivots, exception, a fortiori reading
                     one JSON contract: the "dossier" (contracts/dossier.schema.json)
```

- **One format end to end**: the back builds a *dossier*, the calculator fills its `resultat`, the front displays it. `contracts/valider.py` checks the schema and every consistency rule, in both directions.
- **Trust boundary**: the LLM output is never trusted as is — values must be `true / false / null`, every quoted excerpt is checked against the source text, and a fact without a verified quote goes back to the lawyer.
- **Deterministic**: same dossier, same result; an analysis takes ~30 ms, so "what if" simulations are instant.

## Run locally

```bash
cp .env.example .env            # add your MISTRAL_API_KEY
uv sync && npm ci
uv run --env-file .env uvicorn back.api:app --port 8000     # API + calculator
npm run dev                                                 # http://localhost:3000
```

Optional: `uv run --env-file .env python -m back.serveur_mcp` exposes the MCP server on `http://127.0.0.1:8001/mcp`.
Offline: the `/dashboard` route renders frozen fixtures without the backend.

## Checks

```bash
uv run pytest                               # 134 tests: back, calculator, contracts (no network)
uvx ruff check . && uvx ruff format --check .
npm run lint && npm run typecheck && npm run build
uv run python -m calculateur.evaluation <dossier.json>      # leave-one-out evaluation of the model
```

## Repository

```
src/          front — Next.js App Router, React 19, strict TypeScript, plain CSS
back/         API, Mistral extraction, ingestion, MCP server
calculateur/  the arbitration engine (pure Python, no network, no LLM)
contracts/    the shared JSON contract: schema, factor grid, validator, examples
data/         validated decisions (fiches), official texts, review trail (revues)
dataset-legora/  Legora research exports used to build the corpus
docs/         architecture & contracts, back-end spec, pitch, task plans
```

## Honest limits

- **Validation**: the 12 decisions were reviewed by independent AI legal reviewers against the official texts (trail in `data/revues/`), not yet by a practising lawyer.
- **Small corpus**: intervals stay wide; scores are evidence-weighted estimates, not calibrated probabilities. The model's prior strength (σ = 0.3) was chosen by leave-one-out cross-validation.
- **Contract wording vs. reality**: extraction reads what the documents say; courts look at how the relationship actually works.

## Docs

- [Architecture & JSON contracts](docs/architecture-contrats.md) (French)
- [Back-end spec](docs/spec-back.md) · [Pitch notes](docs/pitch.md)
- Frontend conventions: [AGENTS.md](AGENTS.md). Design tokens were inspected in Mistral Studio; Inter is self-hosted (`public/fonts/Inter-LICENSE.txt`).
