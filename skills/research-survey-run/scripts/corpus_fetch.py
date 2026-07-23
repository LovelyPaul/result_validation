#!/usr/bin/env python3
# [기능군: corpus] arXiv 반입·--since 델타 — 독립(상호 import 없음)
"""corpus_fetch — arXiv export API에서 논문을 받아 범용 코퍼스 스키마로 반입.

"누구나 원하는 논문을 가져올 수 있게": arXiv id 목록 또는 검색어로 논문 메타데이터
(제목·초록 — **API 원문 verbatim**·url)를 받아 `60-data/corpus.json`(범용 스키마
id/title/abstract/url)으로 만든다. `--append`는 기존 코퍼스에 병합(중복 id 스킵).

사용:
  python3 corpus_fetch.py --workspace . --ids 2512.17776,2303.08896
  python3 corpus_fetch.py --workspace . --query "hallucination detection LLM" --max 10 --append
  python3 corpus_fetch.py --workspace . --query "..." --since 2026-06-01 --append   # 델타 반입

`--since YYYY-MM-DD`는 제출일(published) 필터 — 그 날짜 이후 제출분만 반입한다.
--query/--ids 어느 쪽과도 조합되고 --append와 병용하면 "지난 반입 이후 신규분만 병합"이
된다. 필터는 클라이언트측 결정론(응답의 published 대조 — published 없는 항목은 fail-closed
제외·경고). --query+--since 조합은 최신순 정렬(sortBy=submittedDate)로 요청해 --max 창이
최신분을 향하게 한다.

의존: python3 표준 라이브러리만. 자체 검사: `--self-test` (네트워크 0 — 파싱·병합 로직만
fixture로 검증).
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
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
            # published = v1 제출 시각 — --since 델타 필터 기준 (날짜 부분만)
            "published": norm(e.findtext("a:published", "", NS))[:10],
            # source_grade = 이 title/abstract의 출처 등급(codex#9): arXiv export API summary
            # 원문 verbatim이라 'api_summary'. 노트로 승격 시 이 등급이 verbatim 주장의 기준이 된다.
            "source_grade": "api_summary",
        })
    return out


def stamp_retrieved_at(rows, when):
    """반입 시점(retrieved_at) 스탬프 — 결정론 테스트 위해 when(YYYY-MM-DD)을 주입받는 순수 함수.
    출처 등급과 함께 '언제 받은 원문인가'를 기록해 stale·재대조의 기준 시점을 남긴다(codex#9)."""
    for r in rows:
        r["retrieved_at"] = when
    return rows


def parse_since(s):
    """--since 값 검증 → datetime.date. 형식 오류는 명시 SystemExit (조용한 오파싱 금지)."""
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise SystemExit(f"--since 형식 오류: {s!r} — YYYY-MM-DD 형식이어야 한다 (예: 2026-06-01)")


def filter_since(rows, since):
    """제출일(published) >= since 만 유지. published가 없거나 파싱 불가한 항목은
    **fail-closed 제외**(신선도 미확인분을 델타로 조용히 통과시키지 않는다) + stderr 경고.
    반환: (kept, dropped_old, dropped_undated)."""
    kept, old, undated = [], [], []
    for r in rows:
        try:
            pub = date.fromisoformat(r.get("published") or "")
        except ValueError:
            undated.append(r)
            continue
        (kept if pub >= since else old).append(r)
    if undated:
        print(f"경고: published 없는/불량 항목 {len(undated)}건을 --since 필터에서 제외했다"
              f"(fail-closed): {[r.get('id') for r in undated]}", file=sys.stderr)
    return kept, old, undated


RETRY_CODES = (429, 503)   # 일시 rate-limit — 1회 백오프 재시도 대상 (v0.4.1 F2 — 필드 실측)
RETRY_WAIT = 45            # 백오프 초 (필드 실측: 45s 후 성공)


def _default_opener(url):
    req = urllib.request.Request(url, headers={"User-Agent": "research-survey-corpus-fetch"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8")


def _request(url, retry_wait=RETRY_WAIT, opener=_default_opener):
    """HTTP GET + F2 오류 처리(필드 테스트 실측 반영): raw traceback 대신 명시 진단.
    429/503(일시 rate-limit)은 retry_wait초 백오프 후 **1회** 재시도, 그래도 실패하면
    SystemExit. 그 외 코드는 즉시 SystemExit 진단. 연결층 오류(URLError — 오프라인·DNS·
    연결 거부)와 타임아웃도 raw traceback 대신 명시 진단(SystemExit)."""
    try:
        return opener(url)
    except urllib.error.HTTPError as e:
        if e.code in RETRY_CODES:
            print(f"경고: arXiv API HTTP {e.code} (일시 rate-limit) — {retry_wait}s 백오프 후 "
                  f"1회 재시도합니다.", file=sys.stderr)
            time.sleep(retry_wait)
            try:
                return opener(url)
            except urllib.error.HTTPError as e2:
                raise SystemExit(f"arXiv API 요청 실패: HTTP {e2.code} — 백오프 재시도에도 실패. "
                                 f"몇 분 뒤 다시 시도하라. (URL: {url})")
        raise SystemExit(f"arXiv API 요청 실패: HTTP {e.code} {e.reason} — ID/검색어와 네트워크를 "
                         f"확인하라. (URL: {url})")
    except urllib.error.URLError as e:
        # HTTPError가 URLError의 하위클래스이므로 이 분기는 연결층 오류만 받는다
        raise SystemExit(f"arXiv API 연결 실패(오프라인·DNS·연결거부): {e.reason} — "
                         f"네트워크 연결과 프록시 설정을 확인하라. (URL: {url})")
    except TimeoutError:
        raise SystemExit(f"arXiv API 응답 타임아웃(60s) — 네트워크가 느리거나 서버가 무응답이다. "
                         f"잠시 뒤 다시 시도하라. (URL: {url})")


FIELD_PREFIX = re.compile(r'\b(all|ti|abs|au|cat|co|jr|rn|id):', re.I)


def build_search_query(query):
    """검색어 → arXiv search_query 문자열.

    arXiv API의 `all:` 접두는 **첫 토큰에만 결합**한다 — `all:ontology construction LLM`은
    "ontology"만 필드 한정되고 나머지는 느슨하게 흩어져, `sortBy=submittedDate`와 겹치면
    사실상 "그냥 최신 논문"이 반환된다(주제 무관 물리·수학 논문 유입). 다중어 검색어는
    따옴표로 구절 결합해 이 오작동을 막는다.

    이미 필드 접두(all:/ti:/abs:/cat: 등)나 불리언(AND/OR/ANDNOT)을 쓴 질의는 사용자가
    직접 구성한 것으로 보고 그대로 통과시킨다.
    """
    q = query.strip()
    if FIELD_PREFIX.search(q) or re.search(r'\b(AND|OR|ANDNOT)\b', q):
        return q
    if '"' in q:
        return f"all:{q}"
    if len(q.split()) > 1:
        return f'all:"{q}"'
    return f"all:{q}"


def fetch(ids=None, query=None, max_n=10, since=None):
    if ids:
        params = {"id_list": ",".join(ids), "max_results": str(len(ids))}
    else:
        params = {"search_query": build_search_query(query), "max_results": str(max_n)}
        if since:
            # 델타 모드: 최신순 정렬로 --max 창이 since 이후 신규분을 향하게 한다
            params["sortBy"] = "submittedDate"
            params["sortOrder"] = "descending"
    url = API + "?" + urllib.parse.urlencode(params)
    return stamp_retrieved_at(parse_atom(_request(url)), date.today().isoformat())


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
    <published>2025-12-19T18:59:59Z</published>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2303.08896v3</id>
    <title>SelfCheckGPT</title>
    <summary>Second abstract.</summary>
    <published>2023-03-15T17:00:00Z</published>
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
    if rows[0]["published"] != "2025-12-19" or rows[1]["published"] != "2023-03-15":
        failures.append(f"published 파싱 오류: {[r['published'] for r in rows]}")
    # P2 [5] source_grade: API summary 원문이라 전건 api_summary
    if not all(r["source_grade"] == "api_summary" for r in rows):
        failures.append(f"source_grade 누락/오류: {[r.get('source_grade') for r in rows]}")
    # P2 [5] retrieved_at: 주입 날짜 스탬프(결정론)
    stamped = stamp_retrieved_at(parse_atom(_FIXTURE), "2026-07-21")
    if not all(r["retrieved_at"] == "2026-07-21" for r in stamped):
        failures.append(f"retrieved_at 스탬프 오류: {[r.get('retrieved_at') for r in stamped]}")
    # 다중어 검색어 구절 결합 — all: 접두가 첫 토큰에만 붙는 arXiv 동작 대응
    if build_search_query("ontology construction LLM") != 'all:"ontology construction LLM"':
        failures.append(f"다중어 구절 결합 오류: {build_search_query('ontology construction LLM')}")
    if build_search_query("OntoClean") != "all:OntoClean":
        failures.append(f"단일어 질의 변형 오류: {build_search_query('OntoClean')}")
    for passthru in ('abs:"ontology" AND cat:cs.AI', 'all:"a" OR all:"b"', 'ti:ontology'):
        if build_search_query(passthru) != passthru:
            failures.append(f"필드/불리언 질의 통과 오류: {passthru} → {build_search_query(passthru)}")
    # P1-5: --since 델타 필터 (네트워크 0 — fixture 날짜만)
    kept, old, undated = filter_since(rows, parse_since("2024-01-01"))
    if [r["id"] for r in kept] != ["2512.17776"] or [r["id"] for r in old] != ["2303.08896"]:
        failures.append(f"--since 필터 오류: kept={[r['id'] for r in kept]} old={[r['id'] for r in old]}")
    kept_all, _, _ = filter_since(rows, parse_since("2023-01-01"))
    if len(kept_all) != 2:
        failures.append(f"--since 전건 유지 오류: {len(kept_all)}")
    # 경계값: since == published 당일은 포함(>=)
    kept_eq, _, _ = filter_since(rows, parse_since("2025-12-19"))
    if [r["id"] for r in kept_eq] != ["2512.17776"]:
        failures.append(f"--since 당일 포함(>=) 오류: {[r['id'] for r in kept_eq]}")
    # published 없는 항목 → fail-closed 제외 + 경고
    import contextlib as _ctx
    import io as _io
    err_s = _io.StringIO()
    with _ctx.redirect_stderr(err_s):
        kept_u, _, undated_u = filter_since(
            rows + [{"id": "no-date", "title": "t", "abstract": "a", "url": "u"}],
            parse_since("2020-01-01"))
    if [r["id"] for r in undated_u] != ["no-date"] or len(kept_u) != 2:
        failures.append(f"published 결측 fail-closed 오류: kept={len(kept_u)} undated={undated_u}")
    if "published 없는" not in err_s.getvalue():
        failures.append(f"published 결측 경고 미출력: {err_s.getvalue()!r}")
    # --since 형식 오류 → 명시 SystemExit
    try:
        parse_since("2026/06/01")
        failures.append("--since 형식 오류를 통과시킴")
    except SystemExit as e:
        if "형식 오류" not in str(e):
            failures.append(f"--since 형식 진단 이상: {e}")
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
    # v0.4.1 F2: HTTPError 처리 — 모의 opener(네트워크 0)
    def _http_err(code):
        return urllib.error.HTTPError("http://t", code, "msg", None, None)
    calls = {"n": 0}
    def _flaky(url):   # 1회 429 → 2회째 성공 (백오프 재시도 경로)
        calls["n"] += 1
        if calls["n"] == 1:
            raise _http_err(429)
        return _FIXTURE
    import contextlib
    import io
    err2 = io.StringIO()
    with contextlib.redirect_stderr(err2):
        body = _request("http://t", retry_wait=0, opener=_flaky)
    if calls["n"] != 2 or "DEER" not in body:
        failures.append(f"F2 429 백오프 재시도 실패: calls={calls['n']}")
    if "백오프" not in err2.getvalue():
        failures.append(f"F2 백오프 경고 미출력: {err2.getvalue()!r}")
    def _always_429(url):
        raise _http_err(429)
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            _request("http://t", retry_wait=0, opener=_always_429)
        failures.append("F2 재시도 실패를 통과시킴")
    except SystemExit as e:
        if "재시도에도 실패" not in str(e):
            failures.append(f"F2 재실패 진단 이상: {e}")
    def _404(url):
        raise _http_err(404)
    try:
        _request("http://t", retry_wait=0, opener=_404)
        failures.append("F2 404를 통과시킴")
    except SystemExit as e:
        if "HTTP 404" not in str(e):
            failures.append(f"F2 404 진단 이상: {e}")
    # 이월 minor: URLError(오프라인·DNS·타임아웃) → raw traceback 대신 명시 진단
    def _offline(url):
        raise urllib.error.URLError(OSError("getaddrinfo failed"))
    try:
        _request("http://t", retry_wait=0, opener=_offline)
        failures.append("URLError를 통과시킴")
    except SystemExit as e:
        if "연결 실패" not in str(e) or "오프라인" not in str(e):
            failures.append(f"URLError 진단 이상: {e}")
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
    ap.add_argument("--since", help="제출일(published) 델타 필터 — YYYY-MM-DD 이후 제출분만 반입")
    ap.add_argument("--self-test", action="store_true", help="네트워크 없는 자체 검사")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(_self_test())
    if not a.ids and not a.query:
        ap.error("--ids 또는 --query 필요 (또는 --self-test)")
    since = parse_since(a.since) if a.since else None   # 형식 검증은 fetch 전에 (요청 낭비 방지)

    rows = fetch(ids=[i.strip() for i in a.ids.split(",")] if a.ids else None,
                 query=a.query, max_n=a.max, since=since)
    if since:
        rows, old, undated = filter_since(rows, since)
        print(f"델타 필터(--since {a.since}): 유지 {len(rows)}편 · 이전 제출 제외 {len(old)}편"
              + (f" · published 결측 제외 {len(undated)}편" if undated else ""))
    out = Path(a.workspace) / CORPUS_REL
    merged, added, skipped = save(rows, out, a.append)
    print(f"반입 완료: 신규 {len(added)}편 · 중복 스킵 {len(skipped)}편 · 총 {len(merged)}편 → {out}")
    for r in added:
        print(f"  + {r['id']}  {r['title'][:80]}")


if __name__ == "__main__":
    main()
