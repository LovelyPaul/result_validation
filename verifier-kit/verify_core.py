#!/usr/bin/env python3
# [verifier-kit] 도메인 중립 검수 코어 — research-survey verify_summaries.py에서 로직 이관·다이얼화
"""도메인 중립 산출물 검수 엔진 — "무엇을 검증할지"를 다이얼(JSON)로 갈아 끼운다.

이 파일은 research-survey 플러그인 `verify_summaries.py`의 **검증된 grep 로직을 그대로**
가져오되, 논문 도메인에 하드코딩돼 있던 부분(필수 섹션·인용 패턴·원문 소스 표기·id 형식)을
다이얼로 외부화한 것이다. 코어(이 파일)는 도메인을 모른다 — 다이얼(dials/*.json)이 안다.

검증은 두 층이다(원본과 동일 구조):
  ① 규격(structural) — 항상 실행:
     - 플레이스홀더 잔존 0 (다이얼 placeholder 패턴)
     - 필수 섹션 존재 (다이얼 required_sections)
     - 근거 인용 ≥ min_cites (다이얼 cite_pattern)
     - 원문 소스 표기 존재 (다이얼 source_marker)
  ② 근거(grounding) — --corpus 지정 시:
     - 근거 절(다이얼 evidence_section)의 모든 수치(%·소수·정수)와 12자+ 인용 문구가
       원문에 substring 실재하는지 grep 대조. 부재 = FAIL (발명 수치·오인용 차단).
     - 오탐 회피는 컨텍스트 창이 아니라 마스킹+스코프: 인용 좌표(다이얼 coord_pattern)와
       행머리 목차 번호를 마스킹한 뒤 근거 절 안에서만 추출.
     - 원문 매핑은 다이얼 source_id_pattern(예: arXiv id)으로 해결. **--corpus 지정 시
       원문 미해결 = FAIL**(fail-closed) — 조용한 검사 생략은 매설 오류의 우회 루프홀이다.

다이얼 스키마는 README.md 참조. 다이얼 없이 --self-test 는 내장 논문 다이얼로 검증한다.

사용:  python3 verify_core.py --dir <산출물 폴더> --dial dials/research-paper.json
       python3 verify_core.py --dir ... --dial ... --corpus <corpus.json> [--source-dir <txt폴더>]
반환:  0=전건 PASS · 1=FAIL 존재 · 2=입력/다이얼 경로 오류
자체 검사: python3 verify_core.py --self-test (외부 의존 0·tempfile 격리)
"""
import argparse
import json
import re
import sys
from pathlib import Path

# ── 범용 상수 (도메인 무관 — 코어에 유지) ──────────────────────────
PCT = re.compile(r"\d+(?:\.\d+)?(?=\s*%)")          # 94.2% → '94.2'
DEC = re.compile(r"\b\d+\.\d+\b")                    # 0.514 등 소수
INT = re.compile(r"(?<![\d.])\d+(?!\.?\d)")          # 정수 (소수·id의 일부는 제외)
LIST_MARKER = re.compile(r"^\s*\d+[.)]\s", re.M)     # 행머리 목차·리스트 번호 (오탐원)
YEAR_MIN, YEAR_MAX = 1900, 2099                      # 연도형 4자리 — 메타데이터 유래 오탐원
WORD_NUMS = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five",
             "6": "six", "7": "seven", "8": "eight", "9": "nine", "10": "ten",
             "11": "eleven", "12": "twelve"}         # 소형 정수 — 원문 영어 수사 표기 인정
QUOTE = re.compile(r'"([^"\n]{12,})"|“([^”\n]{12,})”')   # 12자+ 인용 문구
_WORD = re.compile(r"[A-Za-z가-힣]{4,}")
_STOP = frozenset("""which their these those about there however while where with that this
from have been were also such using based into than more most other between across both
each only often them they when what upon over under without within because through""".split())
KEYPOINT_OVERLAP = 0.4   # 키포인트 커버 판정 — 문장 내용어 40%+ 공유

# ── 다이얼 필수 키 + 내장 논문 다이얼(하위호환·self-test 기본값) ───────
DIAL_REQUIRED_KEYS = ("name", "required_sections", "cite_pattern", "source_marker",
                      "evidence_section", "coord_pattern", "source_id_pattern")
BUILTIN_PAPER_DIAL = {
    "name": "research-paper (builtin)",
    "required_sections": ["## Summary", "## Why", "## Evidence"],
    "cite_pattern": r"p\.\s*\d+|Table\s*\d|Figure\s*\d|Fig\.\s*\d|§\s*\d",
    "placeholder_pattern": r"\(워커 작성|\(작성 필요|\bTODO\b|<채우세요>|\{\{[A-Z_]+\}\}",
    "source_marker": "source_pdf",
    "evidence_section": r"## Evidence(.*?)(?=\n## |\Z)",
    "coord_pattern": (r"arXiv[:\s]*\d{4}\.\d{4,5}(?:v\d+)?|\b\d{4}\.\d{4,5}(?:v\d+)?\b"
                      r"|\d{4}-\d{2}-\d{2}"
                      r"|p\.\s*\d+|(?:Table|Figure|Fig\.|Section|§)\s*[\d.]*\d"),
    "source_id_pattern": r"\b(\d{4}\.\d{4,5})(?:v\d+)?\b",
    "source_id_tagged": r"arXiv[:\s]*(\d{4}\.\d{4,5})",
    "min_cites": 3,
    "coverage_threshold": 0.6,
}


class Dial:
    """다이얼(도메인 규칙) — JSON을 컴파일된 정규식 묶음으로."""
    def __init__(self, raw):
        missing = [k for k in DIAL_REQUIRED_KEYS if not raw.get(k)]
        if missing:
            raise ValueError(f"다이얼 필수 키 누락: {missing}")
        self.name = raw["name"]
        self.required_sections = list(raw["required_sections"])
        self.source_marker = raw["source_marker"]
        self.min_cites = int(raw.get("min_cites", 3))
        self.coverage_threshold = float(raw.get("coverage_threshold", 0.6))
        rc = lambda p, f=re.I: re.compile(p, f)
        self.cite = rc(raw["cite_pattern"])
        self.placeholder = rc(raw["placeholder_pattern"]) if raw.get("placeholder_pattern") else None
        self.evidence_sec = re.compile(raw["evidence_section"], re.S)
        self.coord = rc(raw["coord_pattern"])
        self.source_marker_line = rc(re.escape(self.source_marker) + r":\s*([^\s(]+)")
        self.source_id_any = rc(raw["source_id_pattern"])
        self.source_id_tagged = rc(raw["source_id_tagged"]) if raw.get("source_id_tagged") else None
        # source_id 안전벨트: full-match로 needle 오추출 방지 (예: arXiv id가 수치로 잡히는 것)
        self.source_id_full = rc(raw.get("source_id_full", raw["source_id_pattern"]))

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))


def load_dial(dial_path):
    return Dial.load(dial_path) if dial_path else Dial(BUILTIN_PAPER_DIAL)


# ── ① 규격 검사 ────────────────────────────────────────────────────

def check_structural(text, dial):
    fails = []
    if dial.placeholder and dial.placeholder.search(text):
        fails.append("플레이스홀더 잔존")
    for sec in dial.required_sections:
        if sec not in text:
            fails.append(f"섹션 누락: {sec}")
    n_cites = len(dial.cite.findall(text))
    if n_cites < dial.min_cites:
        fails.append(f"근거 인용 {n_cites} < {dial.min_cites}")
    if dial.source_marker not in text:
        fails.append(f"{dial.source_marker} 표기 없음")
    return fails


# ── ② 근거 검사 (범용 grep — 원본 로직 이관) ───────────────────────

def _norm(s):
    return " ".join((s or "").split())


def extract_claim_numbers(evidence_text, dial):
    """근거 절에서 실재 대조할 수치 needle 추출 — 퍼센트·소수·정수 전부.
    인용 좌표(다이얼 coord)와 행머리 목차 번호를 먼저 마스킹한 뒤 추출.
    연도형 4자리(1900~2099)는 초록 밖 메타데이터 유래가 흔해 제외."""
    masked = dial.coord.sub(" ", evidence_text)
    masked = LIST_MARKER.sub(" ", masked)
    needles = []
    for rx in (PCT, DEC, INT):
        for m in rx.finditer(masked):
            tok = m.group(0)
            if dial.source_id_full.fullmatch(tok):
                continue   # source id 형태 안전벨트 — 마스킹 누락 대비
            if rx is INT and len(tok) == 4 and YEAR_MIN <= int(tok) <= YEAR_MAX:
                continue   # 연도 표기
            if tok not in needles:
                needles.append(tok)
    return needles


def extract_claim_quotes(evidence_text):
    """근거 절의 따옴표 인용 문구(12자+) needle 추출."""
    out = []
    for m in QUOTE.finditer(evidence_text):
        q = _norm(m.group(1) or m.group(2))
        if q and q not in out:
            out.append(q)
    return out


def check_evidence_grounding(text, source_text, dial):
    """근거 인용 실재 검사 — 수치·인용 문구가 원문에 substring 실재하는지.
    부재 항목 = FAIL 사유 목록 반환. 근거 절이 없으면 [](섹션 누락은 규격 검사 몫)."""
    m = dial.evidence_sec.search(text)
    if not m:
        return []
    ev = m.group(1)
    src_norm = _norm(source_text)
    src_fold = src_norm.casefold()
    fails = []
    for n in extract_claim_numbers(ev, dial):
        # 숫자 경계 매칭 — '999'가 '1999'·'999.5' 안에서 오매칭되지 않게
        found = re.search(rf"(?<![\d.]){re.escape(n)}(?![\d.])", src_norm)
        if not found and n in WORD_NUMS:
            found = re.search(rf"\b{WORD_NUMS[n]}\b", src_fold)
        if not found:
            fails.append(f"근거 수치 원문 부재: {n!r}")
    for q in extract_claim_quotes(ev):
        if q.casefold() not in src_fold:
            fails.append(f"근거 인용 문구 원문 부재: {q[:60]!r}")
    return fails


def _content_words(s):
    return {w.lower() for w in _WORD.findall(s) if w.lower() not in _STOP}


def keypoint_coverage(abstract, summary_text):
    """초록 문장 단위 키포인트 커버율 — (커버율 float | None, 미커버 문장 목록)."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", _norm(abstract)) if s.strip()]
    kps = []
    for s in sents:
        cw = _content_words(s)
        if len(cw) >= 4:
            kps.append((s, cw))
    if not kps:
        return None, []
    sw = _content_words(summary_text)
    uncovered = [s for s, cw in kps if len(cw & sw) / len(cw) < KEYPOINT_OVERLAP]
    return 1.0 - len(uncovered) / len(kps), uncovered


def resolve_source(text, corpus_by_id, source_dir, dial):
    """산출물 → (실재 대조용 원문, 커버율용 초록, 실패 사유). fail-closed:
    해결 불가면 (None, None, 사유). 실재 대조 원문은 --source-dir 의 <source_marker stem>.txt
    또는 <id>.txt 를 우선, 없으면 corpus의 title+abstract."""
    m = (dial.source_id_tagged.search(text) if dial.source_id_tagged else None) or dial.source_id_any.search(text)
    sid = m.group(1) if m else None
    entry = corpus_by_id.get(sid) if sid else None
    abstract = entry.get("abstract") if entry else None

    src_text = None
    if source_dir:
        cands = []
        pm = dial.source_marker_line.search(text)
        if pm:
            cands.append(Path(source_dir) / (Path(pm.group(1)).stem + ".txt"))
        if sid:
            cands.append(Path(source_dir) / f"{sid}.txt")
        for c in cands:
            if c.exists():
                src_text = c.read_text(encoding="utf-8", errors="replace")
                break
    if src_text is None and entry:
        src_text = (entry.get("title") or "") + " " + (abstract or "")

    if src_text is None:
        why = ("원문 id 표기 없음" if not sid
               else f"corpus에 id {sid} 없음(--source-dir 텍스트도 부재)")
        return None, None, why
    return src_text, abstract, None


def run(dirpath, dial, corpus=None, source_dir=None, out=sys.stdout):
    d = Path(dirpath)
    if not d.exists():
        print(f"[verify] 없음: {d}", file=sys.stderr)
        return 2
    corpus_by_id = None
    if corpus:
        cp = Path(corpus)
        if not cp.exists():
            print(f"[verify] corpus 없음: {cp}", file=sys.stderr)
            return 2
        corpus_by_id = {str(e.get("id")): e
                        for e in json.loads(cp.read_text(encoding="utf-8"))}
    mds = sorted(d.glob("*.md"))
    total, bad, warned = 0, 0, 0
    for m in mds:
        total += 1
        t = m.read_text(encoding="utf-8", errors="replace")
        fails = check_structural(t, dial)
        warns = []
        if corpus_by_id is not None:
            src_text, abstract, why = resolve_source(t, corpus_by_id, source_dir, dial)
            if src_text is None:
                fails.append(f"근거 원문 미해결: {why}")   # fail-closed
            else:
                fails.extend(check_evidence_grounding(t, src_text, dial))
                if abstract:
                    cov, uncovered = keypoint_coverage(abstract, t)
                    if cov is not None and cov < dial.coverage_threshold:
                        warns.append(f"키포인트 커버율 {cov:.2f} < {dial.coverage_threshold} "
                                     f"(미커버 {len(uncovered)}문장)")
        if fails:
            bad += 1
            print(f"  [FAIL] {m.name}: {'; '.join(fails)}", file=out)
        if warns:
            warned += 1
            print(f"  [WARN] {m.name}: {'; '.join(warns)}", file=out)
    ok = total - bad
    tail = f" · WARN {warned}" if warned else ""
    print(f"검수[{dial.name}]: 파일 {total} · PASS {ok} · FAIL {bad}{tail}", file=out)
    return 0 if bad == 0 else 1


# ── self-test (원본 fixture 이관 — 내장 논문 다이얼로) ──────────────
_ABSTRACT = ("The proposed system achieves 94.2% accuracy on the standard benchmark "
             "evaluation suite. We introduce a novel retrieval mechanism combining sparse "
             "and dense ranking signals. Experiments demonstrate consistent improvements "
             "across seven multilingual datasets under strict protocols. The framework "
             "supports incremental corpus updates without full reindexing overhead.")
_GOOD_MD = """## Summary
The system achieves 94.2% accuracy on the standard benchmark evaluation suite (p.2).
It introduces a novel retrieval mechanism combining sparse and dense ranking signals (p.3).
Experiments demonstrate consistent improvements across seven multilingual datasets under
strict protocols (Table 1). The framework supports incremental corpus updates (p.7).

## Why
Benchmark evaluation grounding.

## Evidence
- "novel retrieval mechanism combining sparse and dense ranking signals" (p.3)
- 94.2% accuracy (p.2, Table 1)

source_pdf: 1234.56789.pdf (p.1 제목 대조 OK) — arXiv:1234.56789
"""
_BAD_MD = """## Summary
The system reaches high accuracy (p.2).

## Why
Short.

## Evidence
- 88.8% accuracy claimed (p.2, Table 3, Figure 1)
- "outperforms human annotators by a large margin" (p.4)

source_pdf: 1234.56789.pdf (p.1 제목 대조 OK) — arXiv:1234.56789
"""
_NOID_MD = """## Summary
No identifier here (p.1).

## Why
x.

## Evidence
- something (p.2, Table 1, Figure 2)

source_pdf: unknown.pdf (p.1 제목 대조 OK)
"""


def _self_test():
    import io
    import tempfile
    failures = []
    dial = Dial(BUILTIN_PAPER_DIAL)

    # 다이얼 유효성: 필수 키 누락 → ValueError
    try:
        Dial({"name": "x"})
        failures.append("불완전 다이얼을 통과시킴")
    except ValueError:
        pass

    # 수치 needle 추출 — 퍼센트·소수만, arXiv id·§/Table 좌표 제외
    ev = "정확도 94.2% · Spearman 0.514 · arXiv:1234.56789 · § 3.2 절 · Table 2.1 참조"
    nums = extract_claim_numbers(ev, dial)
    if sorted(nums) != ["0.514", "94.2"]:
        failures.append(f"수치 needle 추출 오류: {nums}")
    # 인용 needle — 12자 미만 배제·공백 정규화
    qs = extract_claim_quotes('short "tiny" and "a properly long quoted   phrase" here')
    if qs != ["a properly long quoted phrase"]:
        failures.append(f"인용 needle 추출 오류: {qs}")
    # 실재/부재 판정
    if check_evidence_grounding(
            "## Evidence\n- 94.2% and \"novel retrieval mechanism combining sparse\" (p.1)\n",
            _ABSTRACT, dial):
        failures.append("실재 수치·인용을 부재 판정")
    g2 = check_evidence_grounding(
        "## Evidence\n- 88.8% and \"outperforms human annotators by a large margin\" (p.1)\n",
        _ABSTRACT, dial)
    if len(g2) != 2 or "88.8" not in g2[0] or "outperforms" not in g2[1]:
        failures.append(f"부재 수치·인용 미탐지: {g2}")
    # 발명 정수 추출·판정 + 목차형 오탐 0 + 영어 수사 인정 + 숫자 경계
    ev2 = ("- 999 datasets 와 123 languages 로 확장 (p.4, Table 3)\n"
           "1. Introduction 목차 항목\n2) Methods 목차 항목\n"
           "- 7 benchmarks 평가 · 2026-07-21 기록 · 2023년 발표 (Figure 2)\n")
    if sorted(extract_claim_numbers(ev2, dial)) != ["123", "7", "999"]:
        failures.append(f"정수 needle 추출 오류: {sorted(extract_claim_numbers(ev2, dial))}")
    g3 = check_evidence_grounding("## Evidence\n- 999 datasets across 123 languages (p.2)\n", _ABSTRACT, dial)
    if len(g3) != 2:
        failures.append(f"발명 정수 미탐지: {g3}")
    if check_evidence_grounding("## Evidence\n1. first (p.1)\n2. second (p.2)\n- 94.2% (Table 1)\n", _ABSTRACT, dial):
        failures.append("목차형 정수 오탐")
    if check_evidence_grounding("## Evidence\n- 7 multilingual datasets 개선 (p.3)\n", _ABSTRACT, dial):
        failures.append("수사 표기(seven) 인정 실패")
    g6 = check_evidence_grounding("## Evidence\n- 999 samples 사용 (p.5)\n", "The corpus contains 1999 samples.", dial)
    if len(g6) != 1:
        failures.append(f"숫자 경계 매칭 오류: {g6}")
    # 커버율
    cov_hi, _ = keypoint_coverage(_ABSTRACT, _GOOD_MD)
    cov_lo, unc = keypoint_coverage(_ABSTRACT, _BAD_MD)
    if cov_hi is None or cov_hi < 0.99:
        failures.append(f"커버 요약 커버율 오류: {cov_hi}")
    if cov_lo is None or cov_lo >= 0.6 or not unc:
        failures.append(f"미커버 요약 커버율 오류: {cov_lo}")

    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        drafts = ws / "drafts"
        drafts.mkdir()
        (drafts / "good.md").write_text(_GOOD_MD, encoding="utf-8")
        (drafts / "bad.md").write_text(_BAD_MD, encoding="utf-8")
        corpus = ws / "corpus.json"
        corpus.write_text(json.dumps([{
            "id": "1234.56789", "title": "Retrieval Benchmark",
            "abstract": _ABSTRACT, "url": "u"}]), encoding="utf-8")

        # 하위호환: --corpus 없으면 규격만 — bad.md도 규격은 지켰으므로 전건 PASS
        buf = io.StringIO()
        if run(drafts, dial, out=buf) != 0:
            failures.append(f"하위호환(코퍼스 없음) 오류: {buf.getvalue()}")

        # corpus 대조 — good=PASS·bad=발명 수치+오인용 FAIL+커버율 WARN
        buf = io.StringIO()
        rc = run(drafts, dial, corpus=corpus, out=buf)
        o = buf.getvalue()
        if rc != 1 or "[FAIL] good.md" in o:
            failures.append(f"corpus 대조 오류(good 오탐?): rc={rc}\n{o}")
        if "[FAIL] bad.md" not in o or "88.8" not in o or "outperforms" not in o:
            failures.append(f"bad.md 발명 수치·오인용 미탐지: {o}")
        if "[WARN] bad.md" not in o or "커버율" not in o:
            failures.append(f"bad.md 커버율 경고 누락: {o}")

        # fail-closed: id 미해결 → corpus 지정 시 FAIL
        (drafts / "noid.md").write_text(_NOID_MD, encoding="utf-8")
        buf = io.StringIO()
        run(drafts, dial, corpus=corpus, out=buf)
        if "[FAIL] noid.md" not in buf.getvalue() or "원문 미해결" not in buf.getvalue():
            failures.append(f"원문 미해결 fail-closed 누락: {buf.getvalue()}")
        (drafts / "noid.md").unlink()

        # --source-dir 전문 우선: abstract에 없어도 전문에 있으면 실재 PASS
        srcdir = ws / "pdftxt"
        srcdir.mkdir()
        (srcdir / "1234.56789.txt").write_text(
            "Full text: 88.8% ablation accuracy. The model outperforms human annotators "
            "by a large margin in the appendix.", encoding="utf-8")
        buf = io.StringIO()
        run(drafts, dial, corpus=corpus, source_dir=srcdir, out=buf)
        if "[FAIL] bad.md" in buf.getvalue():
            failures.append(f"--source-dir 전문 실재를 부재 오탐: {buf.getvalue()}")

    if failures:
        print("SELF-TEST FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print("SELF-TEST PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="도메인 중립 산출물 검수 (다이얼로 도메인 지정)")
    ap.add_argument("--dir")
    ap.add_argument("--dial", help="도메인 다이얼 JSON (미지정 시 내장 논문 다이얼)")
    ap.add_argument("--corpus", help="corpus.json — 지정 시 근거 실재 검사 활성")
    ap.add_argument("--source-dir", help="원문 추출 .txt 폴더 — 실재 대조 원문으로 abstract보다 우선")
    ap.add_argument("--self-test", action="store_true", help="외부 의존 없는 자체 검사")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if not args.dir:
        ap.error("--dir 필요 (또는 --self-test)")
    try:
        dial = load_dial(args.dial)
    except (ValueError, json.JSONDecodeError, OSError) as e:
        print(f"[verify] 다이얼 오류: {e}", file=sys.stderr)
        return 2
    return run(args.dir, dial, args.corpus, args.source_dir)


if __name__ == "__main__":
    sys.exit(main())
