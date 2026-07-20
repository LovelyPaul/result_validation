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

API = "https://export.arxiv.org/api/query"   # https 필수 (R1 [2] — 평문 http 금지)
NS = {"a": "http://www.w3.org/2005/Atom"}
CORPUS_REL = "60-data/corpus.json"


def norm(s):
    """공백 정규화(개행 접기) — arXiv Atom은 줄바꿈 래핑이 있어 단어 단위 verbatim로 통일."""
    return re.sub(r"\s+", " ", (s or "")).strip()


def parse_atom(xml_text):
    """Atom XML → [{id, title, abstract, url}]. 결정론 파싱(zero-LLM).
    malformed XML은 명시 SystemExit 진단(R1 [3]) — 조용한 빈 결과 금지. Atom 네임스페이스가
    아닌 feed는 빈 결과 대신 stderr 경고를 남긴다."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise SystemExit(f"arXiv 응답 XML 파싱 실패(malformed): {e} — 응답 앞부분: {xml_text[:120]!r}")
    entries = root.findall("a:entry", NS)
    if not entries and not root.tag.startswith("{http://www.w3.org/2005/Atom}"):
        print(f"경고: Atom 네임스페이스가 아닌 응답(root={root.tag}) — entry 0건. "
              f"API 주소/응답 형식을 확인하라.", file=sys.stderr)
    out = []
    for e in entries:
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


CORPUS_REQUIRED = ("id", "title", "abstract")   # 범용 코퍼스 스키마 필수키 (data-dictionary.md)


def check_corpus(obj, path):
    """--append 대상 코퍼스 타입/스키마 검증 (R1 [4]·R2 [4] 확장) — 비list·비dict 원소·
    필수키(id/title/abstract — data-dictionary 문서 기준) 누락 항목은 명시 거부(SystemExit).
    classify가 title/abstract를 읽으므로 id만으로는 하류 동작을 보장하지 못한다.
    오염된 코퍼스에 조용히 병합하는 것을 금지한다."""
    if not isinstance(obj, list):
        raise SystemExit(f"코퍼스 스키마 위반: {path} 는 JSON 배열이어야 한다 (실제: {type(obj).__name__})")
    for i, e in enumerate(obj):
        if not isinstance(e, dict):
            raise SystemExit(f"코퍼스 스키마 위반: {path} [{i}] 원소가 객체가 아니다 (실제: {type(e).__name__})")
        missing = [k for k in CORPUS_REQUIRED if not e.get(k)]
        if missing:
            raise SystemExit(f"코퍼스 스키마 위반: {path} [{i}] 항목에 필수키 누락 {missing} — "
                             f"범용 스키마 필수 = {'/'.join(CORPUS_REQUIRED)}")


def save(rows, out, append):
    """fetch 결과 저장. **0건이면 파일을 쓰지 않는다**(기존 코퍼스 보존·명시 경고, R2 [5])."""
    if not rows:
        raise SystemExit("경고: 반입 결과 0건 — 코퍼스 파일을 쓰지 않는다(기존 파일 보존). "
                         "검색어/ID를 확인하라.")
    out = Path(out)
    if append and out.exists():
        existing = json.loads(out.read_text(encoding="utf-8"))
        check_corpus(existing, str(out))   # 병합 전 스키마 검증 (R1 [4])
        merged, added, skipped = merge(existing, rows)
    else:
        merged, added, skipped = rows, rows, []
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return merged, added, skipped


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
    # R1 [3]-a: malformed XML → 명시 SystemExit 진단
    try:
        parse_atom("this is not xml <<<")
        failures.append("malformed XML을 조용히 통과시킴")
    except SystemExit as e:
        if "파싱 실패" not in str(e):
            failures.append(f"malformed 진단 메시지 이상: {e}")
    # R1 [3]-b: Atom 네임스페이스 아닌 feed → 빈 결과 + stderr 경고
    import contextlib
    import io
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rows_nons = parse_atom("<feed><entry><id>http://arxiv.org/abs/2512.17776v1</id></entry></feed>")
    if rows_nons != []:
        failures.append(f"비Atom feed 결과 이상: {rows_nons}")
    if "Atom 네임스페이스가 아닌" not in err.getvalue():
        failures.append(f"비Atom feed 경고 미출력: {err.getvalue()!r}")
    # R1 [4]+R2 [4]: --append 코퍼스 스키마 검증 — 비list·비dict·필수키(id/title/abstract) 누락 거부
    for bad, label in (({"not": "a list"}, "비list"),
                       (["문자열원소"], "비dict 원소"),
                       ([{"title": "id 없음", "abstract": "a"}], "id 누락"),
                       ([{"id": "x", "abstract": "a"}], "title 누락"),
                       ([{"id": "x", "title": "t"}], "abstract 누락")):
        try:
            check_corpus(bad, "test-corpus.json")
            failures.append(f"check_corpus가 {label}를 통과시킴")
        except SystemExit as e:
            if "스키마 위반" not in str(e):
                failures.append(f"check_corpus 진단 메시지 이상({label}): {e}")
    if check_corpus([{"id": "x", "title": "정상", "abstract": "본문"}], "t.json") is not None:
        failures.append("check_corpus가 정상 코퍼스에서 값을 반환")
    # R2 [5]: fetch 결과 0건 → 파일 미작성·기존 보존·명시 경고
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "corpus.json"
        original = '[{"id": "keep", "title": "t", "abstract": "a"}]'
        out.write_text(original, encoding="utf-8")
        try:
            save([], out, append=True)
            failures.append("0건인데 save가 통과")
        except SystemExit as e:
            if "0건" not in str(e):
                failures.append(f"0건 경고 메시지 이상: {e}")
        if out.read_text(encoding="utf-8") != original:
            failures.append("0건 save가 기존 파일을 변경함")
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
    merged, added, skipped = save(rows, out, a.append)
    print(f"반입 완료: 신규 {len(added)}편 · 중복 스킵 {len(skipped)}편 · 총 {len(merged)}편 → {out}")
    for r in added:
        print(f"  + {r['id']}  {r['title'][:80]}")


if __name__ == "__main__":
    main()
