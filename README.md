English | [한국어](README.ko.md)

# research-survey

> Turn a research interest into a tracked, evidence-grounded survey — extract → summarize → triple-verify → insights/hypotheses → keep tracking new papers.

- [Quick Start](#quick-start)
- [Why research-survey?](#why-research-survey)
- [How it works](#how-it-works)
- [Features](#features)
- [Requirements](#requirements)
- [License](#license)

## Quick Start
```
/plugin marketplace add <owner>/gptaku-plugins   # or a local path
/plugin install research-survey
# restart Claude Code, then:
/research-survey demo              # 5-10 min toy walkthrough on bundled samples (extract → wiki search → gate rejections → promote)
/research-survey tutorial          # learn the pipeline live (~15 min)
/research-survey init <topic>      # scaffold a standards-compliant workspace
/research-survey run <category>    # run one full survey cycle
```

**Bring your own papers**: `corpus_fetch.py --ids <arxiv-ids>` or `--query "<terms>" --max N`
pulls titles/abstracts verbatim from the arXiv export API into the universal corpus schema
(`--append` merges, skipping duplicate ids) — then edit the taxonomy dial and re-run classify.
For a continuous survey, add `--since YYYY-MM-DD` to pull only papers submitted after your
last ingest (delta mode, combines with `--append`).

**Two ways to use:**
1. **Marketplace install** (above) — the plugin ships its command/skills; the repo-root
   `CLAUDE.md`/`AGENTS.md` adapter is **not loaded** in your project. Use `/research-survey`
   (or natural-language triggers) to start.
2. **Clone + `cd` into the repo** — the root adapter is active: any agent that reads
   `AGENTS.md` (Codex etc.) runs the same RUNBOOK, and the **variant opening** works
   (ask a research question as your first message → the bare answer becomes comparison material).

## Why research-survey?
A "bare-LLM summary" reads plausible but has no sources. A **grounded survey** ties every number
back to a page in the paper (`— Table 1, p.6`) and filters hallucinations through
**producer ≠ evaluator** triple verification. This plugin teaches and runs that difference.

## How it works
```
[dial]    taxonomy.json defines the topic (one file governs both snapshot + daily feed)
   -> [extract]  deterministic multi-label classification (reproducible, no-hallucination)
   -> [shortlist]
   -> [summarize] per-paper PDF-grounded summary (4-part + page-cited Evidence + source_pdf)
   -> [verify]   TRIPLE: self-check -> independent re-measure -> sample PDF cross-read
   -> [organize] wiki index/search (FTS5 + char-bigram BM25) + promote gate -> Notion (optional) + insight extraction
   -> [hypothesis] idea-critic scoring (reviewer + inspector) -> accept/hold -> ledger
   -> [continuous] daily arXiv matched by the same dial -> digest
```

## Features
| Component | What |
|---|---|
| `/research-survey` command | Router: `tutorial` / `demo` / `init` / `run` / `curriculum` / `team-compare` / `help` |
| `curriculum` track (`research-survey-curriculum` skill) | Guide-only 4-week course mapping the study curriculum onto real features: week01 get-it-running (demo/init/corpus_fetch/classify) → week02 knowledge base + review criteria (2-part wiki notes/promote gate/source-coverage/gold+seeded/wiki_grade) → week03 harden + Loop (deterministic gates/run_state resume/30-day audit/open-questions) → week04 multi-agent adjudication (team-compare cross-vendor/GUIDELINE). Measures learner progress from files (no fabricated progress) |
| `demo` walkthrough (`references/DEMO.md`) | Post-install toy run on bundled samples: scaffold → copy corpus+3 wiki notes → classify (7/15 extracted) → wiki search with cited excerpts → 2 gate-rejection demos (no-source, timeline tampering) → clean promote |
| `corpus_fetch.py` | Pull your own papers from the arXiv export API (`--ids` / `--query --max`, verbatim title+abstract, `--append` dedup-merge) into the universal corpus schema. `--since YYYY-MM-DD` filters by submission date for continuous-survey delta ingest (undated entries fail-closed excluded); network-layer errors (offline/DNS/timeout) get explicit diagnostics |
| `research-survey-main` skill | Live tutorial + orchestration (RUNBOOK is the SOT) |
| `research-survey-init` skill | Scaffolds a workspace-standards workspace (10-unit numbering, CLAUDE.md 12-section, 7-layer harness — standard docs cited by path). The scaffold includes a workspace `AGENTS.md` self-intro adapter: opening the workspace without a task makes the agent read PROJECT_STATUS/`run-state.json` and propose the next action (honest "not started yet" on empty state) |
| `research-survey-run` skill | One category cycle: extract → summarize → triple-verify → organize |
| wiki search/promote layer | Real tools (not just a contract): `wiki_index.py` (SQLite FTS5 index, or pure-python char-bigram BM25 fallback), `wiki_query.py` (FTS5-match + bigram-BM25 fused by RRF K=60 with per-channel dedup, dangling-free wikilinks), `wiki_promote.py` (dry-run diff → `--apply` gate with frontmatter+citation lint, JSONL manifest). BM25 formula ported verbatim from the tax-wiki demo (ablation-verified) |
| quality grading harness | `wiki_grade.py` — scores **top-1 hit rate / top-k recall** against a gold question set (question, expected top-1 note, expected evidence phrase — 12 bundled samples) and **gate rejection rate** against seeded error notes (5 bundled types: invented number, quote miscite, no source, timeline tampering, missing keys — plus 1 clean control note that must pass, watching for over-blocking). Also fail-closed checks that each gold evidence phrase is non-empty and really exists in the note. JSON report + optional `--min-top1`/`--min-reject` thresholds. Measured on bundled samples: 12/12 top-1, 5/5 seeded rejected, control passed |
| source-coverage verification | `verify_summaries.py --corpus` — greps that every Evidence number (percent/decimal/**integer** — cite coordinates & list markers masked, 4-digit years excluded, digit-boundary matching, small integers also matched as English numerals) and every quote actually exists in the source (PDF-extracted `--source-dir` text preferred, else corpus abstract; unresolvable source = FAIL, fail-closed) and warns when abstract key-point coverage falls below threshold (default 0.6) |
| maintenance loop | `wiki_index.py --audit` — 30-day **stale** detection (`updated`/`created` age; unparseable dates fail-closed), one-line health counts (notes/edges/orphan/broken/stale/skipped), **typed edges** `[[id\|rel]]` (contrasts/supports/extends) with a contrasts-pair listing, and note `confidence` declarations (verbatim 1.0 / summary 0.7) recorded in the manifest |
| Root `CLAUDE.md` + `AGENTS.md` | Agent adapter — any agent (Codex etc.) runs the same RUNBOOK. **Variant opening**: if your first message is a research question, the agent answers bare (no files/web) and that answer becomes the bare-vs-grounded comparison material |
| RUNBOOK §0.5 preflight | Probes OS/python and LLM CLIs (`command -v` / `Get-Command`, Windows + Unix commands both given) — only tools actually observed are offered as bare-LLM subjects; web-chat paste is the zero-CLI fallback |
| RUNBOOK §3.5 output convention | Outputs go only to your workspace `artifacts/` or `40-drafts/` — never into the plugin folder; previous outputs are preserved under `artifacts/prev-<date>/`, not deleted |
| references/ | RUNBOOK · phase_contracts · taxonomy_dial · quality_gates · roles · citation_rules |
| assets/templates/ | taxonomy dial · survey section · self-contained comparison HTML · example workspace |
| examples/ | ICML 2026 worked example (6,628 papers, 9 categories — real counts, verdicts, incidents) |

## Scripts (contributors)
All scripts live in `skills/research-survey-run/scripts/` (python3 stdlib, each `--self-test`), grouped by function. They import each other as sibling modules (co-located; see `sys.path` bootstrap), so they stay in one flat directory — see `RESTRUCTURE_PLAN.md` for the physical-split trade-off deferred to a future major.

| Group | Scripts | Role |
|---|---|---|
| **wiki** | `wiki_index.py` · `wiki_query.py` · `wiki_promote.py` · `wiki_grade.py` | index/audit (stale·MOC suggest·open-questions) · RRF search + pseudo-reranker & query routing · promote gate · grading harness (grade imports query/promote/verify) |
| **corpus** | `classify.py` · `corpus_fetch.py` | deterministic classify · arXiv ingest + `--since` delta + `source_grade`/`retrieved_at` |
| **verify** | `verify_summaries.py` | summary lint + source-coverage + source_grade consistency (reused by wiki_grade) |
| **team** *(v0.6.0)* | `team_compare.py` | multi-LLM team-compare lab — producer/reviewer per team, prompt via stdin, path-hygiene on ids, deterministic scoring scoped to Evidence number/quote substring existence (qualitative claims out of scope; low-evidence flagged) |
| **state** *(v0.7.0)* | `run_state.py` | pipeline state machine — records run-cycle stages in `_meta/run-state.json` for resume-after-interruption |

## Requirements
- Claude Code. Core tutorial runs locally (python3 stdlib for classify/verify scripts).
- Optional: a paper corpus (title/abstract/PDF) and destinations (Notion / a wiki).

## License
MIT

<p align="center"><sub>Research is useful only when it leaves behind reusable, sourced structure.</sub></p>
