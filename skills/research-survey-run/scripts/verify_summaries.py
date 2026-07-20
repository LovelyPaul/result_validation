#!/usr/bin/env python3
"""범용 요약 결정론 검수 — 3중 검증의 1차(자가검증)·2차(독립 실측) 공용 도구.

각 요약 md가 규격을 지키는지 결정론으로 검사한다(눈대중 대체):
  - 플레이스홀더 잔존 0 (스켈레톤 미작성 슬롯)
  - 필수 섹션 존재: '## Summary', '## Why', '## Evidence'
  - 페이지 인용 ≥ min-cites (기본 3) — 정규식 p.\\d+ / Table \\d / Figure \\d
  - source_pdf 표기 존재

source-coverage 검수 (v0.5.0 P1-2 — `--corpus` 지정 시 활성):
  - ① Evidence 인용 실재: Evidence 절의 수치(퍼센트·소수·**정수 포함 전부** — R1)와 인용
    문구("…" 12자+)가 원문(--source-dir 의 PDF 추출 .txt 우선, 없으면 corpus.json abstract)에
    실재하는지 grep 대조. 부재 = FAIL (발명 수치·오인용 차단 — 결정론만, LLM 채점 금지).
    오탐 회피는 컨텍스트 창이 아니라 **마스킹+스코프**로: 인용 좌표(p.N·Table/Figure/§/
    Section N·arXiv id·YYYY-MM-DD)와 행머리 목차 번호(`1. `·`2) `)를 마스킹한 뒤 Evidence
    절 안에서만 추출. 연도형 4자리(1900~2099)는 초록 밖 메타데이터 유래가 흔해 제외.
    원문 대조는 숫자 경계 매칭(999를 1999에 오매칭 금지)·소형 정수(≤12)는 영어 수사
    (seven 등) 표기도 실재로 인정.
  - ② 키포인트 커버율: 원문 초록을 문장 단위 키포인트로 쪼개 요약이 각 키포인트의
    내용어(4자+ 단어)를 40% 이상 공유하면 커버로 판정. 커버율 < 임계(기본 0.6)면 WARN
    (경고 — exit 코드에는 불반영). 한글 요약이 영어 초록 용어를 인용 없이 완전 의역하면
    저평가될 수 있다 — 결정론 근사의 한계로 문서화한다.
  - 요약→원문 매핑은 arXiv id(`arXiv:NNNN.NNNNN` 우선, 없으면 본문 내 id 패턴)로 해결.
    **--corpus 지정 시 원문 미해결 = FAIL**(fail-closed) — 조용한 검사 생략은 매설 오류의
    우회 루프홀이 된다(append-only 병합 루프홀 실측 교훈).

사용:  python verify_summaries.py --dir <워크스페이스>/40-drafts/<cat>   [--min-cites 3]
       python verify_summaries.py --dir ... --corpus <ws>/60-data/corpus.json
           [--source-dir <PDF추출txt폴더>] [--coverage-threshold 0.6]
반환:  0=전건 PASS · 1=FAIL 존재 (FAIL 파일·사유 목록 출력) · 2=입력 경로 오류
자체 검사: `python verify_summaries.py --self-test` (외부 의존 0·tempfile 격리)
"""
import argparse
import json
import re
import sys
from pathlib import Path

PLACEHOLDER = re.compile(r"\(워커 작성|\(작성 필요|\bTODO\b|<채우세요>|\{\{[A-Z_]+\}\}")
CITE = re.compile(r"p\.\s*\d+|Table\s*\d|Figure\s*\d|Fig\.\s*\d|§\s*\d", re.IGNORECASE)
REQUIRED = ["## Summary", "## Why", "## Evidence"]

# ── source-coverage (P1-2) 정규식 ──────────────────────────────────
ARXIV_TAGGED = re.compile(r"arXiv[:\s]*(\d{4}\.\d{4,5})", re.IGNORECASE)
ARXIV_ANY = re.compile(r"\b(\d{4}\.\d{4,5})(?:v\d+)?\b")
ARXIV_FULL = re.compile(r"\d{4}\.\d{4,5}$")
EVIDENCE_SEC = re.compile(r"## Evidence(.*?)(?=\n## |\Z)", re.S)
SOURCE_PDF_LINE = re.compile(r"source_pdf:\s*([^\s(]+)")
PCT = re.compile(r"\d+(?:\.\d+)?(?=\s*%)")          # 94.2% → '94.2'
DEC = re.compile(r"\b\d+\.\d+\b")                    # 0.514 등 소수 (arXiv id는 제외)
INT = re.compile(r"(?<![\d.])\d+(?!\.?\d)")          # 정수 (R1 — 소수·id의 일부는 제외)
# 인용 좌표 마스킹 — 수치 '주장'이 아닌 원문 좌표·메타 표기 (추출 전에 제거)
CITE_COORD = re.compile(
    r"arXiv[:\s]*\d{4}\.\d{4,5}(?:v\d+)?|\b\d{4}\.\d{4,5}(?:v\d+)?\b"   # arXiv id
    r"|\d{4}-\d{2}-\d{2}"                                                # 날짜
    r"|p\.\s*\d+|(?:Table|Figure|Fig\.|Section|§)\s*[\d.]*\d", re.IGNORECASE)
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
COVERAGE_THRESHOLD = 0.6   # 커버율 경고 임계 기본값


def check(path, min_cites):
    t = path.read_text(encoding="utf-8", errors="replace")
    fails = []
    if PLACEHOLDER.search(t):
        fails.append("플레이스홀더 잔존")
    for sec in REQUIRED:
        if sec not in t:
            fails.append(f"섹션 누락: {sec}")
    if len(CITE.findall(t)) < min_cites:
        fails.append(f"페이지 인용 {len(CITE.findall(t))} < {min_cites}")
    if "source_pdf" not in t:
        fails.append("source_pdf 표기 없음")
    return fails


# ── source-coverage 층 (P1-2) ──────────────────────────────────────

def _norm(s):
    return " ".join((s or "").split())


def extract_claim_numbers(evidence_text):
    """Evidence 절에서 실재 대조할 수치 needle 추출 — 퍼센트·소수·정수 전부 (R1: 정수
    전면 제외가 '999 datasets' 발명 정수를 놓쳤다). 오탐 회피는 마스킹으로: 인용 좌표
    (p.N·Table/Figure/§/Section·arXiv id·날짜)와 행머리 목차 번호를 먼저 지운 뒤 추출.
    연도형 4자리(1900~2099)는 초록 밖 메타데이터(발행연도) 유래가 흔해 제외."""
    masked = CITE_COORD.sub(" ", evidence_text)
    masked = LIST_MARKER.sub(" ", masked)
    needles = []
    for rx in (PCT, DEC, INT):
        for m in rx.finditer(masked):
            tok = m.group(0)
            if ARXIV_FULL.fullmatch(tok):
                continue   # arXiv id 형태(NNNN.NNNNN) 안전벨트 — 마스킹 누락 대비
            if rx is INT and len(tok) == 4 and YEAR_MIN <= int(tok) <= YEAR_MAX:
                continue   # 연도 표기
            if tok not in needles:
                needles.append(tok)
    return needles


def extract_claim_quotes(evidence_text):
    """Evidence 절의 따옴표 인용 문구(12자+ — 짧은 용어 오탐 배제) needle 추출."""
    out = []
    for m in QUOTE.finditer(evidence_text):
        q = _norm(m.group(1) or m.group(2))
        if q and q not in out:
            out.append(q)
    return out


def check_evidence_grounding(text, source_text):
    """① Evidence 인용 실재 검사 — 수치·인용 문구가 원문에 substring 실재하는지.
    부재 항목 = FAIL 사유 목록 반환. Evidence 절이 없으면 [](섹션 누락은 기본 검사 몫)."""
    m = EVIDENCE_SEC.search(text)
    if not m:
        return []
    ev = m.group(1)
    src_norm = _norm(source_text)
    src_fold = src_norm.casefold()
    fails = []
    for n in extract_claim_numbers(ev):
        # 숫자 경계 매칭 — '999'가 '1999'·'999.5' 안에서 오매칭(거짓 PASS)되지 않게
        found = re.search(rf"(?<![\d.]){re.escape(n)}(?![\d.])", src_norm)
        if not found and n in WORD_NUMS:
            # 소형 정수는 원문이 영어 수사로 쓴 경우(seven 등)도 실재로 인정
            found = re.search(rf"\b{WORD_NUMS[n]}\b", src_fold)
        if not found:
            fails.append(f"Evidence 수치 원문 부재: {n!r}")
    for q in extract_claim_quotes(ev):
        if q.casefold() not in src_fold:
            fails.append(f"Evidence 인용 문구 원문 부재: {q[:60]!r}")
    return fails


def _content_words(s):
    return {w.lower() for w in _WORD.findall(s) if w.lower() not in _STOP}


def keypoint_coverage(abstract, summary_text):
    """② 초록 문장 단위 키포인트 커버율 — (커버율 float | None, 미커버 문장 목록).
    내용어 4개 미만 문장은 키포인트에서 제외. 키포인트 0개면 None(판정 불가)."""
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


def resolve_source(text, corpus_by_id, source_dir):
    """요약 → (실재 대조용 원문, 커버율용 초록, 실패 사유). fail-closed:
    해결 불가면 (None, None, 사유). 실재 대조 원문은 --source-dir 의 <source_pdf stem>.txt
    또는 <arXiv id>.txt 를 우선(전문이 더 넓다), 없으면 corpus abstract(제목 포함)."""
    m = ARXIV_TAGGED.search(text) or ARXIV_ANY.search(text)
    aid = m.group(1) if m else None
    entry = corpus_by_id.get(aid) if aid else None
    abstract = entry.get("abstract") if entry else None

    src_text = None
    if source_dir:
        cands = []
        pm = SOURCE_PDF_LINE.search(text)
        if pm:
            cands.append(Path(source_dir) / (Path(pm.group(1)).stem + ".txt"))
        if aid:
            cands.append(Path(source_dir) / f"{aid}.txt")
        for c in cands:
            if c.exists():
                src_text = c.read_text(encoding="utf-8", errors="replace")
                break
    if src_text is None and entry:
        src_text = (entry.get("title") or "") + " " + (abstract or "")

    if src_text is None:
        why = ("arXiv id 표기 없음" if not aid
               else f"corpus에 id {aid} 없음(--source-dir 텍스트도 부재)")
        return None, None, why
    return src_text, abstract, None


def run(dirpath, min_cites=3, corpus=None, source_dir=None,
        coverage_threshold=COVERAGE_THRESHOLD, out=sys.stdout):
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
        fails = check(m, min_cites)
        warns = []
        if corpus_by_id is not None:
            t = m.read_text(encoding="utf-8", errors="replace")
            src_text, abstract, why = resolve_source(t, corpus_by_id, source_dir)
            if src_text is None:
                fails.append(f"source-coverage 원문 미해결: {why}")   # fail-closed
            else:
                fails.extend(check_evidence_grounding(t, src_text))
                if abstract:
                    cov, uncovered = keypoint_coverage(abstract, t)
                    if cov is not None and cov < coverage_threshold:
                        warns.append(f"키포인트 커버율 {cov:.2f} < {coverage_threshold} "
                                     f"(미커버 {len(uncovered)}문장 — 첫 문장: "
                                     f"{uncovered[0][:70]!r})")
        if fails:
            bad += 1
            print(f"  [FAIL] {m.name}: {'; '.join(fails)}", file=out)
        if warns:
            warned += 1
            print(f"  [WARN] {m.name}: {'; '.join(warns)}", file=out)
    ok = total - bad
    tail = f" · WARN {warned}" if warned else ""
    print(f"검수: 파일 {total} · PASS {ok} · FAIL {bad}{tail}", file=out)
    return 0 if bad == 0 else 1


# ── self-test (P1-2 fixture — 실재/부재·커버/미커버) ────────────────

_ABSTRACT = ("The proposed system achieves 94.2% accuracy on the standard benchmark "
             "evaluation suite. We introduce a novel retrieval mechanism combining sparse "
             "and dense ranking signals. Experiments demonstrate consistent improvements "
             "across seven multilingual datasets under strict protocols. The framework "
             "supports incremental corpus updates without full reindexing overhead.")

_GOOD_MD = """## Summary
The system achieves 94.2% accuracy on the standard benchmark evaluation suite (p.2).
It introduces a novel retrieval mechanism combining sparse and dense ranking signals (p.3).
Experiments demonstrate consistent improvements across seven multilingual datasets under
strict protocols (Table 1). The framework supports incremental corpus updates without full
reindexing overhead (p.7).

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

    # 단위: 수치 needle 추출 — 퍼센트·소수만, arXiv id·§/Table 좌표 제외
    ev = "정확도 94.2% · Spearman 0.514 · arXiv:1234.56789 · § 3.2 절 · Table 2.1 참조"
    nums = extract_claim_numbers(ev)
    if sorted(nums) != ["0.514", "94.2"]:
        failures.append(f"수치 needle 추출 오류: {nums}")
    # 단위: 인용 needle — 12자 미만 배제·공백 정규화
    qs = extract_claim_quotes('short "tiny" and "a properly long quoted   phrase" here')
    if qs != ["a properly long quoted phrase"]:
        failures.append(f"인용 needle 추출 오류: {qs}")
    # 단위: 실재/부재 판정
    g = check_evidence_grounding(
        "## Evidence\n- 94.2% and \"novel retrieval mechanism combining sparse\" (p.1)\n",
        _ABSTRACT)
    if g:
        failures.append(f"실재 수치·인용을 부재 판정: {g}")
    g2 = check_evidence_grounding(
        "## Evidence\n- 88.8% and \"outperforms human annotators by a large margin\" (p.1)\n",
        _ABSTRACT)
    if len(g2) != 2 or "88.8" not in g2[0] or "outperforms" not in g2[1]:
        failures.append(f"부재 수치·인용 미탐지: {g2}")
    # R1 단위: 정수 포함 추출 — 발명 정수는 잡고, 좌표·목차·날짜·연도는 마스킹/제외 (오탐 0)
    ev2 = ("- 999 datasets 와 123 languages 로 확장 (p.4, Table 3)\n"
           "1. Introduction 목차 항목\n"
           "2) Methods 목차 항목\n"
           "- 7 benchmarks 평가 · 2026-07-21 기록 · 2023년 발표 (Figure 2)\n")
    nums2 = extract_claim_numbers(ev2)
    if sorted(nums2) != ["123", "7", "999"]:
        failures.append(f"R1 정수 needle 추출 오류: {sorted(nums2)} (기대 123·7·999)")
    # R1 단위: 발명 정수 → FAIL
    g3 = check_evidence_grounding("## Evidence\n- 999 datasets across 123 languages (p.2)\n",
                                  _ABSTRACT)
    if len(g3) != 2 or "999" not in g3[0] or "123" not in g3[1]:
        failures.append(f"R1 발명 정수 미탐지: {g3}")
    # R1 단위: 목차형 정수 + 실재 수치만 → 오탐 0
    g4 = check_evidence_grounding(
        "## Evidence\n1. first point (p.1)\n2. second point (p.2)\n- 94.2% 정확도 (Table 1)\n",
        _ABSTRACT)
    if g4:
        failures.append(f"R1 목차형 정수 오탐: {g4}")
    # R1 단위: 소형 정수의 영어 수사 표기 인정 — '7' vs 원문 'seven multilingual datasets'
    g5 = check_evidence_grounding("## Evidence\n- 7 multilingual datasets 개선 (p.3)\n",
                                  _ABSTRACT)
    if g5:
        failures.append(f"R1 수사 표기 인정 실패: {g5}")
    # R1 단위: 숫자 경계 매칭 — 원문 '1999'가 needle '999'의 거짓 PASS가 되면 안 됨
    g6 = check_evidence_grounding("## Evidence\n- 999 samples 사용 (p.5)\n",
                                  "The corpus contains 1999 samples in total.")
    if len(g6) != 1 or "999" not in g6[0]:
        failures.append(f"R1 숫자 경계 매칭 오류: {g6}")
    # 단위: 커버율 — 전문 포함 요약=1.0 / 무관 요약=낮음
    cov_hi, _ = keypoint_coverage(_ABSTRACT, _GOOD_MD)
    cov_lo, unc = keypoint_coverage(_ABSTRACT, _BAD_MD)
    if cov_hi is None or cov_hi < 0.99:
        failures.append(f"커버 요약 커버율 오류: {cov_hi}")
    if cov_lo is None or cov_lo >= 0.6 or not unc:
        failures.append(f"미커버 요약 커버율 오류: {cov_lo} unc={len(unc)}")

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

        # 하위호환: --corpus 없으면 기존 검사만 — bad.md도 규격은 지켰으므로 전건 PASS
        buf = io.StringIO()
        if run(drafts, out=buf) != 0:
            failures.append(f"하위호환(코퍼스 없음) 검수 오류: {buf.getvalue()}")

        # P1-2: corpus 대조 — good=PASS·bad=발명 수치+오인용 FAIL+커버율 WARN
        buf = io.StringIO()
        rc = run(drafts, corpus=corpus, out=buf)
        o = buf.getvalue()
        if rc != 1:
            failures.append(f"corpus 대조 exit 오류: {rc}\n{o}")
        if "good.md" in o and "[FAIL] good.md" in o:
            failures.append(f"good.md 오탐: {o}")
        if "[FAIL] bad.md" not in o or "88.8" not in o or "outperforms" not in o:
            failures.append(f"bad.md 발명 수치·오인용 미탐지: {o}")
        if "[WARN] bad.md" not in o or "커버율" not in o:
            failures.append(f"bad.md 커버율 경고 누락: {o}")

        # fail-closed: id 미해결 요약은 corpus 지정 시 FAIL (조용한 생략 루프홀 차단)
        (drafts / "noid.md").write_text(_NOID_MD, encoding="utf-8")
        buf = io.StringIO()
        run(drafts, corpus=corpus, out=buf)
        if "[FAIL] noid.md" not in buf.getvalue() or "원문 미해결" not in buf.getvalue():
            failures.append(f"원문 미해결 fail-closed 누락: {buf.getvalue()}")
        (drafts / "noid.md").unlink()

        # --source-dir 우선: 전문 txt에 있으면 abstract에 없어도 실재 PASS (커버율 WARN은 유지)
        srcdir = ws / "pdftxt"
        srcdir.mkdir()
        (srcdir / "1234.56789.txt").write_text(
            "Full text: 88.8% ablation accuracy. The model outperforms human annotators "
            "by a large margin in the appendix.", encoding="utf-8")
        buf = io.StringIO()
        run(drafts, corpus=corpus, source_dir=srcdir, out=buf)
        o = buf.getvalue()
        if "[FAIL] bad.md" in o:
            failures.append(f"--source-dir 전문 실재를 부재 오탐: {o}")
        if "[WARN] bad.md" not in o:
            failures.append(f"--source-dir 지정 시 커버율 경고 소실: {o}")

    if failures:
        print("SELF-TEST FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print("SELF-TEST PASS")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    ap.add_argument("--min-cites", type=int, default=3)
    ap.add_argument("--corpus", help="corpus.json 경로 — 지정 시 source-coverage 검수 활성(P1-2)")
    ap.add_argument("--source-dir", help="PDF 추출 .txt 폴더 — 실재 대조 원문으로 abstract보다 우선")
    ap.add_argument("--coverage-threshold", type=float, default=COVERAGE_THRESHOLD,
                    help=f"키포인트 커버율 경고 임계 (기본 {COVERAGE_THRESHOLD})")
    ap.add_argument("--self-test", action="store_true", help="외부 의존 없는 자체 검사")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if not args.dir:
        ap.error("--dir 필요 (또는 --self-test)")
    return run(args.dir, args.min_cites, args.corpus, args.source_dir,
               args.coverage_threshold)


if __name__ == "__main__":
    sys.exit(main())
