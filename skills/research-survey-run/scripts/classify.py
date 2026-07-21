#!/usr/bin/env python3
# [기능군: corpus] 결정론 분류·랭킹 — 독립(상호 import 없음)
"""범용 결정론 분류기 — 관심 주제(taxonomy 다이얼)로 논문 코퍼스를 다중라벨 분류·랭킹.

플러그인 자립형: 표준 라이브러리만 사용. ICML 전용 필드(poster_id·icml_url·_oral)에 비결합 —
아래 '범용 코퍼스 스키마'를 읽고 워크스페이스 표준 경로에 쓴다.

범용 코퍼스 스키마 (60-data/corpus.json, JSON 배열):
  [ { "id": "<고유 id>", "title": "...", "abstract": "...",
      "keywords": "<선택>", "url": "<선택>",
      "flags": { "oral": false } } , ... ]
  - 필수: id, title, abstract. 선택: keywords, url, flags(중요도 플래그 dict).
  - ICML 코퍼스는 icml2026_master.json을 이 스키마로 매핑해 쓰면 된다(id=poster_id, url=icml_url,
    flags.oral=oral 여부). 매핑 예시는 references/phase_contracts.md.

입력:  <workspace>/00-system/taxonomy.json  +  <workspace>/60-data/corpus.json
출력:  <workspace>/70-analysis/categories/<cat>.{md,csv}
       <workspace>/70-analysis/shortlist/<cat>.md
       <workspace>/70-analysis/summary.md
       <workspace>/70-analysis/all_categorized.json

사용:
  python classify.py --workspace .                     # 전체 분류
  python classify.py --workspace . --sample <cat> 14   # 표본 검수(고정 시드)
  python classify.py --workspace . --shortlist-n 30    # 쇼트리스트 크기
"""
import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path


def compile_cat(cat_def, guards):
    rc = lambda p: re.compile(p, re.IGNORECASE)  # 인라인 (?i) 금지 — 여기서 IGNORECASE 부여
    return {
        "patterns": [rc(p) for p in cat_def.get("patterns", [])],
        "relevance": [rc(p) for p in cat_def.get("relevance_terms", [])],
        "noise": [rc(p) for p in cat_def.get("noise_terms", [])],
        "exclude": [rc(p) for p in cat_def.get("exclude", [])],
        "guard": rc(guards[cat_def["guard"]]) if cat_def.get("guard") else None,
        "threshold": cat_def.get("threshold"),
    }


def score(rec, c, title_weight, default_threshold):
    title = rec.get("title") or ""
    body = " ".join(filter(None, [rec.get("abstract"), rec.get("keywords")]))
    full = title + " \n " + body
    if c["guard"] and not c["guard"].search(full):
        return None
    for ex in c["exclude"]:
        if ex.search(full):
            return None
    s, hits = 0, []
    for pat in c["patterns"]:
        it, ib = bool(pat.search(title)), bool(pat.search(body))
        if it:
            s += title_weight
        if ib:
            s += 1
        if it or ib:
            hits.append(pat.pattern[:40])
    for pat in c["relevance"]:
        if pat.search(full):
            s += 1
    for pat in c["noise"]:
        if pat.search(full):
            s -= 2
    thr = c["threshold"] if c["threshold"] is not None else default_threshold
    return {"score": s, "hits": hits} if s >= thr else None


def is_oral(rec):
    f = rec.get("flags") or {}
    return bool(f.get("oral") or f.get("spotlight"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--sample", nargs=2, metavar=("CAT", "N"))
    ap.add_argument("--shortlist-n", type=int, default=30)
    args = ap.parse_args()

    ws = Path(args.workspace).resolve()
    tax_path = ws / "00-system" / "taxonomy.json"
    corpus_path = ws / "60-data" / "corpus.json"
    for p in (tax_path, corpus_path):
        if not p.exists():
            print(f"[classify] 없음: {p}\n  → 00-system/taxonomy.json 과 60-data/corpus.json(범용 스키마)이 필요합니다.",
                  file=sys.stderr)
            return 2

    tax = json.load(open(tax_path, encoding="utf-8"))
    corpus = json.load(open(corpus_path, encoding="utf-8"))
    tw = tax.get("title_weight", 3)
    dthr = tax.get("default_threshold", 3)
    guards = tax.get("guards", {})
    cats = {n: compile_cat(cd, guards) for n, cd in tax["categories"].items()}

    results = {n: [] for n in cats}
    for rec in corpus:
        for n, c in cats.items():
            m = score(rec, c, tw, dthr)
            if m:
                e = dict(rec)
                e["_score"] = m["score"]
                e["_oral"] = is_oral(rec)
                results[n].append(e)
    for n in results:
        results[n].sort(key=lambda r: (not r["_oral"], -r["_score"], r.get("title", "")))

    if args.sample:
        cat, n = args.sample[0], int(args.sample[1])
        rows = results.get(cat, [])
        if not rows and cat not in results:
            print(f"[classify] 카테고리 없음: {cat} (있는 것: {', '.join(results)})", file=sys.stderr)
            return 2
        pick = random.Random(42).sample(rows, min(n, len(rows)))
        print(f"[{cat}] {len(rows)}편 중 무작위 {len(pick)} (고정 시드 42):")
        for r in pick:
            print(f"  ({r['_score']:>2}{' *oral' if r['_oral'] else ''}) {(r.get('title') or '')[:95]}")
        return 0

    out = ws / "70-analysis"
    (out / "categories").mkdir(parents=True, exist_ok=True)
    (out / "shortlist").mkdir(parents=True, exist_ok=True)
    fields = ["id", "title", "_score", "_oral", "keywords", "url"]
    for n, rows in results.items():
        with open(out / "categories" / f"{n}.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        lines = [f"# {n} ({len(rows)}편)", "",
                 f"> {tax['categories'][n].get('desc', '')}", "",
                 "| # | oral | score | title | url |", "|---|---|---|---|---|"]
        for i, r in enumerate(rows, 1):
            t = (r.get("title") or "").replace("|", "\\|")
            lines.append(f"| {i} | {'*' if r['_oral'] else ''} | {r['_score']} | {t} | {r.get('url') or ''} |")
        (out / "categories" / f"{n}.md").write_text("\n".join(lines), encoding="utf-8")
        sl = rows[:args.shortlist_n]
        s = [f"# shortlist — {n} (상위 {len(sl)} / {len(rows)}, oral 우선)", ""]
        for i, r in enumerate(sl, 1):
            ab = (r.get("abstract") or "").replace("\n", " ")
            s += [f"## {i}. {'*oral ' if r['_oral'] else ''}{r.get('title')} (score {r['_score']})",
                  f"- id: {r.get('id')} · url: {r.get('url') or ''}",
                  f"- abstract: {ab[:600]}{'…' if len(ab) > 600 else ''}", ""]
        (out / "shortlist" / f"{n}.md").write_text("\n".join(s), encoding="utf-8")

    slim = {n: [{k: r.get(k) for k in ("id", "title", "abstract", "keywords", "url", "_score", "_oral")}
                for r in rows] for n, rows in results.items()}
    (out / "all_categorized.json").write_text(json.dumps(slim, indent=1, ensure_ascii=False), encoding="utf-8")

    ids = {n: {str(r["id"]) for r in rows} for n, rows in results.items()}
    total = set().union(*ids.values()) if ids else set()
    sm = ["# 분류 요약", "",
          f"- 코퍼스 {len(corpus)}편 · 카테고리 합집합 {len(total)}편", "",
          "| 카테고리 | 편수 | oral | threshold |", "|---|---|---|---|"]
    for n, rows in results.items():
        o = sum(1 for r in rows if r["_oral"])
        sm.append(f"| {n} | {len(rows)} | {o} | {tax['categories'][n].get('threshold', dthr)} |")
    (out / "summary.md").write_text("\n".join(sm), encoding="utf-8")

    for n, rows in results.items():
        print(f"  {n:28s} {len(rows):5d}편 (oral {sum(1 for r in rows if r['_oral'])})")
    print(f"산출물: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
