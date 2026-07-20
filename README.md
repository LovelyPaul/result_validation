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
| `/research-survey` command | Router: `tutorial` / `demo` / `init` / `run` / `help` |
| `demo` walkthrough (`references/DEMO.md`) | Post-install toy run on bundled samples: scaffold → copy corpus+3 wiki notes → classify (7/15 extracted) → wiki search with cited excerpts → 2 gate-rejection demos (no-source, timeline tampering) → clean promote |
| `corpus_fetch.py` | Pull your own papers from the arXiv export API (`--ids` / `--query --max`, verbatim title+abstract, `--append` dedup-merge) into the universal corpus schema |
| `research-survey-main` skill | Live tutorial + orchestration (RUNBOOK is the SOT) |
| `research-survey-init` skill | Scaffolds a workspace-standards workspace (10-unit numbering, CLAUDE.md 12-section, 7-layer harness — standard docs cited by path) |
| `research-survey-run` skill | One category cycle: extract → summarize → triple-verify → organize |
| wiki search/promote layer | Real tools (not just a contract): `wiki_index.py` (SQLite FTS5 index, or pure-python char-bigram BM25 fallback), `wiki_query.py` (FTS5-match + bigram-BM25 fused by RRF K=60 with per-channel dedup, dangling-free wikilinks), `wiki_promote.py` (dry-run diff → `--apply` gate with frontmatter+citation lint, JSONL manifest). BM25 formula ported verbatim from the tax-wiki demo (ablation-verified) |
| Root `CLAUDE.md` + `AGENTS.md` | Agent adapter — any agent (Codex etc.) runs the same RUNBOOK. **Variant opening**: if your first message is a research question, the agent answers bare (no files/web) and that answer becomes the bare-vs-grounded comparison material |
| RUNBOOK §0.5 preflight | Probes OS/python and LLM CLIs (`command -v` / `Get-Command`, Windows + Unix commands both given) — only tools actually observed are offered as bare-LLM subjects; web-chat paste is the zero-CLI fallback |
| RUNBOOK §3.5 output convention | Outputs go only to your workspace `artifacts/` or `40-drafts/` — never into the plugin folder; previous outputs are preserved under `artifacts/prev-<date>/`, not deleted |
| references/ | RUNBOOK · phase_contracts · taxonomy_dial · quality_gates · roles · citation_rules |
| assets/templates/ | taxonomy dial · survey section · self-contained comparison HTML · example workspace |
| examples/ | ICML 2026 worked example (6,628 papers, 9 categories — real counts, verdicts, incidents) |

## Requirements
- Claude Code. Core tutorial runs locally (python3 stdlib for classify/verify scripts).
- Optional: a paper corpus (title/abstract/PDF) and destinations (Notion / a wiki).

## License
MIT

<p align="center"><sub>Research is useful only when it leaves behind reusable, sourced structure.</sub></p>
