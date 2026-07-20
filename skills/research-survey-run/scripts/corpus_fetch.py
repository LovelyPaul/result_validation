#!/usr/bin/env python3
"""corpus_fetch — arXiv export API에서 논문을 받아 범용 코퍼스 스키마로 반입.

"누구나 원하는 논문을 가져올 수 있게": arXiv id 목록 또는 검색어로 논문 메타데이터
(제목·초록 — **API 원문 verbatim**·url)를 받아 `60-data/corpus.json`(범용 스키마
id/title/abstract/url)으로 만든다. `--append`는 기존 코퍼스에 병합(중복 id 스킵).

사용:
  python3 corpus_fetch.py --workspace . --ids 2512.17776,2303.08896
  python3 corpus_fetch.py --workspace . --query "hallucination detection LLM" --max 10 --append

의존: python3 표준 라이브러리만. 자체 검사: `--self-test` (네트워크 0 — 파싱·병합 로직만
fixture로 검증).
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

API = "http://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom"}
CORPUS_REL = "60-data/corpus.json"


def norm(s):
    """공백 정규화(개행 접기) — arXiv Atom은 줄바꿈 래핑이 있어 단어 단위 verbatim로 통일."""
    return re.sub(r"\s+", " ", (s or "")).strip()


def parse_atom(xml_text):
    """Atom XML → [{id, title, abstract, url}]. 결정론 파싱(zero-LLM)."""
    out = []
    for e in ET.fromstring(xml_text).findall("a:entry", NS):
        raw_id = e.findtext("a:id", "", NS)          # http://arxiv.org/abs/<id>v<n>
        m = re.search(r"abs/([0-9]{4}\.[0-9]{4,5})", raw_id)
        if not m:
            continue
        aid = m.group(1)
        out.append({
            "id": aid,
            "title": norm(e.findtext("a:title", "", NS)),
            "abstract": norm(e.findtext("a:summary", "", NS)),
            "url": f"https://arxiv.org/abs/{aid}",
        })
    return out


def fetch(ids=None, query=None, max_n=10):
    if ids:
        params = {"id_list": ",".join(ids), "max_results": str(len(ids))}
    else:
        params = {"search_query": f"all:{query}", "max_results": str(max_n)}
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "research-survey-corpus-fetch"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return parse_atom(r.read().decode("utf-8"))


def merge(existing, new):
    """--append 병합: 기존 id는 스킵(원본 불변), 신규만 뒤에 추가. 반환: (merged, added, skipped)."""
    seen = {str(e.get("id")) for e in existing}
    added, skipped = [], []
    for n in new:
        (skipped if n["id"] in seen else added).append(n)
        seen.add(n["id"])
    return existing + added, added, skipped


_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2512.17776v4</id>
    <title>DEER: A Benchmark for
 Evaluating Deep Research Agents</title>
    <summary>  Line one
of the abstract.  </summary>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2303.08896v3</id>
    <title>SelfCheckGPT</title>
    <summary>Second abstract.</summary>
  </entry>
</feed>"""


def _self_test():
    failures = []
    # 파싱: id 추출·공백 정규화(개행 접기)
    rows = parse_atom(_FIXTURE)
    if [r["id"] for r in rows] != ["2512.17776", "2303.08896"]:
        failures.append(f"id 파싱 오류: {[r['id'] for r in rows]}")
    if rows[0]["title"] != "DEER: A Benchmark for Evaluating Deep Research Agents":
        failures.append(f"title 정규화 오류: {rows[0]['title']!r}")
    if rows[0]["abstract"] != "Line one of the abstract.":
        failures.append(f"abstract 정규화 오류: {rows[0]['abstract']!r}")
    if rows[0]["url"] != "https://arxiv.org/abs/2512.17776":
        failures.append(f"url 오류: {rows[0]['url']}")
    # 병합: 중복 id 스킵·기존 불변·신규 추가
    existing = [{"id": "2512.17776", "title": "OLD", "abstract": "keep", "url": "u"}]
    merged, added, skipped = merge(existing, rows)
    if len(merged) != 2 or merged[0]["title"] != "OLD":
        failures.append(f"병합 기존 불변 위반: {merged}")
    if [a["id"] for a in added] != ["2303.08896"] or [s["id"] for s in skipped] != ["2512.17776"]:
        failures.append(f"병합 dedup 오류: added={added} skipped={skipped}")
    if failures:
        print("SELF-TEST FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print("SELF-TEST PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="arXiv → 범용 코퍼스 반입 (id 또는 검색어)")
    ap.add_argument("--workspace", default=".", help="워크스페이스 루트 (기본: 현재 폴더)")
    ap.add_argument("--ids", help="arXiv id 콤마 목록 (예: 2512.17776,2303.08896)")
    ap.add_argument("--query", help="arXiv 검색어 (all: 필드)")
    ap.add_argument("--max", type=int, default=10, help="--query 시 최대 편수 (기본 10)")
    ap.add_argument("--append", action="store_true", help="기존 corpus.json에 병합(중복 id 스킵)")
    ap.add_argument("--self-test", action="store_true", help="네트워크 없는 자체 검사")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(_self_test())
    if not a.ids and not a.query:
        ap.error("--ids 또는 --query 필요 (또는 --self-test)")

    rows = fetch(ids=[i.strip() for i in a.ids.split(",")] if a.ids else None,
                 query=a.query, max_n=a.max)
    out = Path(a.workspace) / CORPUS_REL
    if a.append and out.exists():
        existing = json.loads(out.read_text(encoding="utf-8"))
        merged, added, skipped = merge(existing, rows)
    else:
        merged, added, skipped = rows, rows, []
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"반입 완료: 신규 {len(added)}편 · 중복 스킵 {len(skipped)}편 · 총 {len(merged)}편 → {out}")
    for r in added:
        print(f"  + {r['id']}  {r['title'][:80]}")


if __name__ == "__main__":
    main()
