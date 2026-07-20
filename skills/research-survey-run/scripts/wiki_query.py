#!/usr/bin/env python3
"""wiki_query — 질문 → (FTS5 매치 채널 + 문자 bigram BM25 랭킹 채널) RRF 융합 top-k → 리포트.

두 채널을 RRF(Reciprocal Rank Fusion, K=60)로 융합한다 — 다채널 하이브리드 규칙
(LLM_WIKI_RULES_DISTILLED.md C1 · 단순 유니온보다 우월·결정론):
  ① FTS5 매치 채널   : .index/wiki.db 가 있으면 MATCH + bm25()로 랭킹 (SQLite 내장).
  ② bigram BM25 채널 : 노트 본문을 문자 bigram으로 BM25 랭킹 — 수식·전처리는 wiki-demo
    wiki/scripts/query.py 를 그대로 이식(ablation으로 recall 검증된 수식·임의 개선 금지).
    한국어처럼 공백 토큰화가 약한 언어에서 FTS5 단독 매치가 놓치는 것을 bigram이 보완한다.

리포트는 <workspace>/20-knowledge-base/wiki/queries/ 에 저장하고, 존재하는 노트만
위키링크로 건다(dangling 0 불변식 — wiki-demo _linkify 패턴).

의존: python3 표준 라이브러리만. 자체 검사: `python3 wiki_query.py --self-test`.
"""
import argparse
import collections
import hashlib
import json
import math
import re
import sqlite3
import sys
import unicodedata
from datetime import date
from pathlib import Path

WIKI_REL = "20-knowledge-base/wiki"
NOTES_REL = f"{WIKI_REL}/notes"
QUERIES_REL = f"{WIKI_REL}/queries"
INDEX_REL = f"{WIKI_REL}/.index"

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.S)
_KV_RE = re.compile(r"([A-Za-z_][\w-]*):\s*(.*)$")


def parse_frontmatter(text):
    """정규식 frontmatter 파서(pyyaml 미사용). wiki_index.parse_frontmatter와 동일 규약."""
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        mm = _KV_RE.match(line.strip())
        if not mm:
            continue
        key, val = mm.group(1), mm.group(2).strip()
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            fm[key] = [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()] if inner else []
        else:
            fm[key] = val.strip().strip('"').strip("'")
    return fm, text[m.end():]


# ── 문자 bigram BM25 (wiki-demo wiki/scripts/query.py 이식 — 수식·전처리 그대로) ──
# 원본: gpters23/wiki-demo/wiki/scripts/query.py (BM25 백스톱, ablation 2026-07-08).
# 상수·_BM25_STRIP·_bigrams·idf·score 식·(-score,stem) 결정 정렬을 동일하게 유지해야
# ablation 동등성(union recall)이 성립 — 임의 개선 금지.

BM25_K1, BM25_B, BM25_TOPK = 1.2, 0.75, 10
_BM25_STRIP = re.compile(r"[\s「」『』()\[\],.·ㆍ:;'\"?!〈〉<>①-⑮]")
RRF_K = 60   # C1 다채널 융합 상수 (Reciprocal Rank Fusion — LLM_WIKI_RULES_DISTILLED.md C1)


def _bigrams(text):
    t = _BM25_STRIP.sub("", text)
    return [t[i:i + 2] for i in range(len(t) - 1)]


def _bm25_index(docs):
    """docs = {id: body_text} → (n, avgdl, tf, df, dl). wiki-demo _bm25_index 동일 구조."""
    toks = {i: _bigrams(b) for i, b in docs.items()}
    n = len(toks)
    avgdl = sum(len(v) for v in toks.values()) / n if n else 0
    df = collections.Counter()
    tf = {}
    for stem, t in toks.items():
        c = collections.Counter(t)
        tf[stem] = c
        for term in c:
            df[term] += 1
    dl = {stem: len(t) for stem, t in toks.items()}
    return n, avgdl, tf, df, dl


def bm25_top(question, docs, k=BM25_TOPK):
    """질문 NL 원문 → BM25 top-k id (rank 순). 쿼리 term 중복 무시(set) — ablation 동일.
    동점만 (-score, id) 결정 정렬. score 식은 wiki-demo query.py 와 글자 단위 동일."""
    n, avgdl, tf, df, dl = _bm25_index(docs)
    if n == 0:
        return []
    scores = collections.Counter()
    for term in set(_bigrams(question)):
        nt = df.get(term, 0)
        if nt == 0:
            continue
        idf = math.log(1 + (n - nt + 0.5) / (nt + 0.5))
        for stem, c in tf.items():
            f_ = c.get(term, 0)
            if f_ == 0:
                continue
            scores[stem] += idf * f_ * (BM25_K1 + 1) / (
                f_ + BM25_K1 * (1 - BM25_B + BM25_B * dl[stem] / avgdl))
    return [s for s, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]


# ── FTS5 매치 채널 ──────────────────────────────────────────────────

def _fts_escape(question):
    """FTS5 MATCH 쿼리 안전화 — 토큰을 큰따옴표로 감싸 OR 결합(연산자 오파싱·구문오류 방지)."""
    toks = re.findall(r"\w+", question, flags=re.UNICODE)
    toks = [t for t in toks if len(t) >= 2]
    if not toks:
        return None
    return " OR ".join(f'"{t}"' for t in toks)


def fts5_top(db_path, question, k=BM25_TOPK):
    """FTS5 db가 있으면 MATCH + bm25()로 top-k id. db 없거나 매치 0이면 []."""
    if not Path(db_path).exists():
        return []
    match = _fts_escape(question)
    if not match:
        return []
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT id FROM notes WHERE notes MATCH ? ORDER BY bm25(notes) LIMIT ?",
            (match, k),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()
    return [r[0] for r in rows]


# ── 노트 로드·리포트 ────────────────────────────────────────────────

def load_notes(notes_dir):
    """notes/*.md → {id: {title, body, tags, path}}. id는 frontmatter 우선, 없으면 stem."""
    out = {}
    for p in sorted(Path(notes_dir).glob("*.md")):
        fm, body = parse_frontmatter(p.read_text(encoding="utf-8"))
        nid = fm.get("id") or p.stem
        out[nid] = {"title": fm.get("title") or p.stem, "body": body.strip(),
                    "tags": fm.get("tags") or [], "source": fm.get("source", ""), "path": str(p)}
    return out


def _slug(s):
    return re.sub(r"[^\w가-힣]+", "_", unicodedata.normalize("NFC", s)).strip("_")


def _excerpt(body, cap=500):
    body = body.strip()
    return body if len(body) <= cap else body[:cap].rstrip() + " …"


def query(workspace, question, k=BM25_TOPK):
    ws = Path(workspace)
    notes_dir = ws / NOTES_REL
    if not notes_dir.exists():
        raise SystemExit(f"노트 폴더 없음: {notes_dir} — 먼저 wiki_index로 노트를 준비하세요.")
    notes = load_notes(notes_dir)
    ids = set(notes)
    docs = {i: (notes[i]["title"] + "\n" + notes[i]["body"]) for i in notes}

    fts_hits = fts5_top(ws / INDEX_REL / "wiki.db", question, k)
    bm_hits = bm25_top(question, docs, k)

    # C1 RRF 융합(K=60): 두 채널 랭킹을 Reciprocal Rank Fusion으로 결합 — 단순 유니온보다
    # 우월·결정론(LLM_WIKI_RULES_DISTILLED.md C1). score(d)=Σ 1/(K+rank_i(d)), 동점은
    # (-score, id) 결정 정렬. dangling 0 — 존재 id만.
    rrf = {}
    for ranking in (fts_hits, bm_hits):
        for rank, i in enumerate(ranking, start=1):
            if i in ids:
                rrf[i] = rrf.get(i, 0.0) + 1.0 / (RRF_K + rank)
    union = [i for i, _ in sorted(rrf.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]

    ch = "fts5+bigram(rrf)" if Path(ws / INDEX_REL / "wiki.db").exists() else "bigram-only"
    lines = [
        "---",
        f"question: {json.dumps(question, ensure_ascii=False)}",
        f"created: {date.today()}",
        f"channels: {ch}",
        f"fusion: rrf(k={RRF_K})",
        f"fts5_hits: {json.dumps(fts_hits, ensure_ascii=False)}",
        f"bigram_hits: {json.dumps(bm_hits, ensure_ascii=False)}",
        "---\n",
        f"# 위키 쿼리 — {question}\n",
        f"채널: {ch} · RRF(K={RRF_K}) 융합 top-{k}\n",
        "## 매칭 노트 (근거 발췌)",
    ]
    if union:
        for i in union:
            n = notes[i]
            tag = f" · tags: {', '.join(n['tags'])}" if n["tags"] else ""
            src = f"\n> 출처: {n['source']}" if n["source"] else ""
            # 존재하는 노트만 위키링크 (dangling 0 불변식)
            lines.append(f"\n### [[{i}]] — {n['title']}{tag}{src}")
            lines.append(f"\n{_excerpt(n['body'])}\n")
    else:
        lines.append("- (매칭 없음)")

    queries_dir = ws / QUERIES_REL
    queries_dir.mkdir(parents=True, exist_ok=True)
    out = queries_dir / f"{_slug(question)[:40]}-{hashlib.md5(question.encode('utf-8')).hexdigest()[:6]}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out, union, ch


def _self_test():
    import tempfile
    failures = []

    # 단위: BM25 수식 동작 — 질의어를 담은 문서가 상위
    docs = {"a": "언어모델 사전학습 데이터 품질", "b": "의료 영상 분할 합성 데이터"}
    top = bm25_top("사전학습 데이터 품질", docs, k=2)
    if not top or top[0] != "a":
        failures.append(f"bm25_top 랭킹 오류: {top} (기대 1위=a)")

    # 단위: _bigrams·strip
    if _bigrams("a b.c") != ["ab", "bc"]:
        failures.append(f"_bigrams strip 오류: {_bigrams('a b.c')}")

    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        notes = ws / NOTES_REL
        notes.mkdir(parents=True)
        (notes / "alpha.md").write_text(
            "---\nid: alpha\ntitle: LLM Pretraining\ntags: [llm]\n"
            "source: arXiv:2401.1, Table 1, p.6\n---\n대규모 언어모델 사전학습 데이터 품질.\n",
            encoding="utf-8")
        (notes / "beta.md").write_text(
            "---\nid: beta\ntitle: Medical Seg\ntags: [medical]\n"
            "source: arXiv:2402.2, p.3\n---\n의료 영상 분할 합성 데이터 증강.\n",
            encoding="utf-8")
        # 색인 없이(bigram-only) 쿼리 — index db 부재에도 동작해야 함
        out, union, ch = query(str(ws), "언어모델 사전학습", k=5)
        if not out.exists():
            failures.append("리포트 미생성")
        if "alpha" not in union:
            failures.append(f"유니온에 alpha 누락: {union}")
        report = out.read_text(encoding="utf-8")
        if "[[alpha]]" not in report:
            failures.append("존재 노트 위키링크 누락")
        # dangling 0: 리포트의 모든 [[id]]가 실존 노트여야
        for wl in re.findall(r"\[\[([^\]]+)\]\]", report):
            if wl not in {"alpha", "beta"}:
                failures.append(f"dangling 위키링크: {wl}")

    if failures:
        print("SELF-TEST FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print("SELF-TEST PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="wiki 쿼리 — FTS5 매치 + bigram BM25 RRF(K=60) 융합")
    ap.add_argument("question", nargs="?", help="자연어 질문")
    ap.add_argument("--workspace", default=".", help="워크스페이스 루트 (기본: 현재 폴더)")
    ap.add_argument("-k", "--topk", type=int, default=BM25_TOPK, help=f"top-k (기본 {BM25_TOPK})")
    ap.add_argument("--self-test", action="store_true", help="외부 의존 없는 자체 검사")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(_self_test())
    if not a.question:
        ap.error("question 인자가 필요합니다 (또는 --self-test)")
    out, union, ch = query(a.workspace, a.question, a.topk)
    print(f"리포트: {out}")
    print(f"채널: {ch} · RRF(K={RRF_K}) 융합 {len(union)}건: {', '.join(union) or '(없음)'}")


if __name__ == "__main__":
    main()
