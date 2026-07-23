#!/usr/bin/env python3
# [verifier-kit] 의미 채널 (G1+) — WARN 전용 보조 신호·판정 권한 없음·stdlib only
"""semantic_core — grep이 못 잡는 '붕 뜬 근거'를 사람에게 귀띔하는 WARN 전용 채널.

★ 설계 철칙 (하네스 무결성):
  - **판정 권한 0**: 이 채널은 FAIL도 exit code도 절대 내지 않는다. 결정론 grep
    (verify_core)만이 거부 권한을 갖는다. 의미 채널은 오직 WARN(귀띔)만 낸다.
  - **CI 거부율 불간섭**: grade_core의 거부율은 이 채널과 무관하게 계산된다. 여기 임계를
    바꿔도 CI 게이트 통과/실패는 바뀌지 않는다.
  - **stdlib only**: 무거운 임베딩(sentence-transformers 등) 없이 문자 n-gram + TF 코사인.

왜 이런 한계 설계인가 (실측 근거):
  문자 n-gram 코사인은 '완전히 붕 뜬 주장'(무관·표면 다른 왜곡, 유사도 ~0.13-0.19)은 잘
  잡지만, 충실한 의역(~0.39)과 부분 인용 왜곡(~0.39)은 겹쳐서 구분 못 한다 — 표면 문자열
  유사도의 본질적 한계다(진짜 의미 이해는 임베딩/NLI 몫, 로드맵). 그래서 이 채널은:
    · 낮은 임계(기본 0.2) '미만'만 WARN — 확실히 대응 근거가 안 보이는 주장만 귀띔.
    · 의역은 통과시킨다(정상 의역을 WARN하는 오탐보다 낫다). **저재현·저오탐 보조**가 목표.
  즉 grep이 정밀 검사(발명 수치·오인용 확정 FAIL), 의미 채널은 "이 주장 원문 어디에도
  안 닮았는데요?" 하는 낮은 신뢰도 귀띔이다.

방향성:
  verify_core.keypoint_coverage 는 원문→요약(놓친 키포인트)을 본다. 이 채널은 반대로
  요약(근거 절)→원문(대응 문장 부재)을 본다 — 근거 없이 붙인 주장을 귀띔. 상보적.

사용(라이브러리):
  from semantic_core import semantic_warnings
  warns = semantic_warnings(evidence_text, source_text, threshold=0.2)  # → [문장, 최대유사도] 목록
CLI:
  python3 semantic_core.py --dir <폴더> --dial dials/X.json --corpus <corpus.json> [--sim-threshold 0.2]
  (verify_core 규격·근거 FAIL 검사도 함께 돌리되, 의미 채널은 WARN으로만 덧붙인다.)
자체 검사: python3 semantic_core.py --self-test
"""
import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_core import load_dial, check_structural, check_evidence_grounding  # noqa: E402
from verify_core import resolve_source                                          # noqa: E402

NGRAM = 3
SIM_THRESHOLD = 0.2          # 이 값 '미만' 최대유사도면 WARN (확실히 붕 뜬 주장만)
MIN_CLAIM_CHARS = 12         # 너무 짧은 조각은 유사도가 불안정 — 대상서 제외
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
# 근거 절에서 '주장 문장'만 남기려 좌표·불릿 마커를 제거(유사도 왜곡 방지)
_COORD_STRIP = re.compile(
    r"\(.*?\)|p\.\s*\d+|(?:Table|Figure|Fig\.|Section|§)\s*[\d.]*\d"
    r"|arXiv[:\s]*\d{4}\.\d{4,5}|PR#\d+|[\w./-]+:\d+", re.I)
_BULLET = re.compile(r"^\s*[-*•]\s*", re.M)
# 소스 표기 줄(source_pdf: ... / source_diff: ...)은 주장이 아니라 메타 — 유사도 대상서 제외
_SOURCE_LINE = re.compile(r"(?im)^\s*\w+:\s*\S+\.(?:pdf|diff|txt|md|json)\b.*$")


def _ngrams(s):
    s = re.sub(r"\s+", " ", s.lower().strip())
    if len(s) < NGRAM:
        return Counter([s]) if s else Counter()
    return Counter(s[i:i + NGRAM] for i in range(len(s) - NGRAM + 1))


def _cosine(a, b):
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[k] * b[k] for k in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def _sentences(text):
    return [s.strip() for s in _SENT_SPLIT.split(text or "") if s.strip()]


def _claim_units(evidence_text):
    """근거 절 → 유사도 대조할 주장 단위 목록. 소스표기 줄·좌표·불릿 제거, 짧은 조각 배제."""
    body = _SOURCE_LINE.sub(" ", evidence_text or "")
    body = _BULLET.sub(" ", body)
    units = []
    for raw in _sentences(body):
        cleaned = _norm(_COORD_STRIP.sub(" ", raw))
        # 순수 인용부호 문구도 하나의 주장 단위로 인정
        if len(cleaned) >= MIN_CLAIM_CHARS:
            units.append((raw.strip(), cleaned))
    return units


def _norm(s):
    return " ".join((s or "").split())


def max_similarity(claim, source_sents_ngrams):
    cg = _ngrams(claim)
    return max((_cosine(cg, sg) for sg in source_sents_ngrams), default=0.0)


def semantic_warnings(evidence_text, source_text, threshold=SIM_THRESHOLD):
    """근거 절의 각 주장이 원문 어느 문장과도 임계 미만으로만 닮았으면 WARN 대상.
    반환: [(원주장 문장, 최대유사도)] — 임계 미만인 것만. 판정 아님(귀띔)."""
    src_ngrams = [_ngrams(s) for s in _sentences(source_text)]
    if not src_ngrams:
        return []
    out = []
    for raw, cleaned in _claim_units(evidence_text):
        sim = max_similarity(cleaned, src_ngrams)
        if sim < threshold:
            out.append((raw, round(sim, 3)))
    return out


def _evidence_of(text, dial):
    m = dial.evidence_sec.search(text)
    return m.group(1) if m else ""


def run(dirpath, dial, corpus, source_dir=None, sim_threshold=SIM_THRESHOLD, out=sys.stdout):
    """verify_core 규격·근거 FAIL 검사 + 의미 채널 WARN. exit code는 FAIL로만 결정
    (의미 WARN은 exit에 불반영 — 판정 권한 없음)."""
    d = Path(dirpath)
    if not d.exists():
        print(f"[semantic] 없음: {d}", file=sys.stderr)
        return 2
    corpus_by_id = {str(e.get("id")): e
                    for e in json.loads(Path(corpus).read_text(encoding="utf-8"))}
    total, bad, sem_warned = 0, 0, 0
    for m in sorted(d.glob("*.md")):
        total += 1
        t = m.read_text(encoding="utf-8", errors="replace")
        fails = check_structural(t, dial)
        src_text, _abstract, why = resolve_source(t, corpus_by_id, source_dir, dial)
        sem = []
        if src_text is None:
            fails.append(f"근거 원문 미해결: {why}")   # fail-closed (결정론)
        else:
            fails.extend(check_evidence_grounding(t, src_text, dial))
            sem = semantic_warnings(_evidence_of(t, dial), src_text, sim_threshold)
        if fails:
            bad += 1
            print(f"  [FAIL] {m.name}: {'; '.join(fails)}", file=out)
        if sem:
            sem_warned += 1
            tips = "; ".join(f"{s[:44]!r}(sim {v})" for s, v in sem)
            print(f"  [WARN·의미] {m.name}: 원문 대응 근거 희박 — {tips}", file=out)
    tail = f" · 의미WARN {sem_warned}" if sem_warned else ""
    print(f"검수+의미[{dial.name}]: 파일 {total} · FAIL {bad}{tail} "
          f"(의미 WARN은 판정 아님·exit 불반영)", file=out)
    return 0 if bad == 0 else 1


# ── self-test (원리·한계·불간섭을 모두 고정) ────────────────────────
_SOURCE = ("The system achieves 94.2% accuracy on the standard benchmark. "
           "We introduce a novel retrieval mechanism combining sparse and dense signals. "
           "Experiments show improvements across seven multilingual datasets.")


def _self_test():
    import io
    import tempfile
    from verify_core import Dial, BUILTIN_PAPER_DIAL
    failures = []
    src_sents = [_ngrams(s) for s in _sentences(_SOURCE)]

    # 원리: 직접 근거는 높고, 무관 주장은 낮다
    direct = max_similarity("achieves 94.2% accuracy on the standard benchmark", src_sents)
    unrel = max_similarity("the authors deploy a blockchain consensus protocol", src_sents)
    if not (direct > 0.6):
        failures.append(f"직접 근거 유사도 낮음: {direct}")
    if not (unrel < 0.2):
        failures.append(f"무관 주장 유사도 높음: {unrel}")
    if not (direct > unrel):
        failures.append("직접 근거가 무관 주장보다 안 높음")

    # WARN 판정: 무관 주장은 WARN, 직접 근거는 WARN 아님
    ev = ('- "achieves 94.2% accuracy on the standard benchmark" (p.2)\n'
          "- the authors deploy a blockchain consensus protocol for voting (p.3)\n")
    w = semantic_warnings(ev, _SOURCE, threshold=0.2)
    flagged = [s for s, _ in w]
    if not any("blockchain" in s for s in flagged):
        failures.append(f"무관 주장을 WARN 못함: {w}")
    if any("94.2% accuracy on the standard benchmark" in s for s in flagged):
        failures.append(f"직접 근거를 오탐 WARN: {w}")

    # 한계 정직성: 충실한 의역은 통과(WARN 아님) — 오탐보다 낫다
    para = "- the method reaches 94.2 percent correctness on the benchmark suite (p.2)\n"
    if semantic_warnings(para, _SOURCE, threshold=0.2):
        failures.append("의역을 WARN함(저오탐 목표 위반 — 임계가 너무 높음)")

    # 짧은 조각·좌표만인 줄은 대상서 제외
    if semantic_warnings("- (p.2, Table 1)\n- ok\n", _SOURCE, threshold=0.2):
        failures.append("짧은 조각/좌표를 주장으로 오인")

    # 원문 없으면 빈 결과(예외 아님)
    if semantic_warnings(ev, "", threshold=0.2) != []:
        failures.append("빈 원문에서 WARN 생성")

    # ★불간섭: run()의 exit code는 FAIL로만 결정 — 의미 WARN이 있어도 FAIL 0이면 exit 0
    dial = Dial(BUILTIN_PAPER_DIAL)
    with tempfile.TemporaryDirectory() as dd:
        ws = Path(dd)
        drafts = ws / "d"
        drafts.mkdir()
        # 규격·근거는 모두 통과하지만 의미적으로 붕 뜬 주장이 있는 노트
        (drafts / "clean_but_floaty.md").write_text(
            "## Summary\ns (p.2).\n## Why\ng (p.3).\n"
            "## Evidence\n- 94.2% accuracy (p.2)\n"
            "- a completely unrelated statement about quantum teleportation here (p.3)\n"
            "source_pdf: paper.pdf — arXiv:1234.56789\n", encoding="utf-8")
        corpus = ws / "c.json"
        corpus.write_text(json.dumps([{"id": "1234.56789", "title": "T",
                                       "abstract": _SOURCE}]), encoding="utf-8")
        buf = io.StringIO()
        rc = run(drafts, dial, corpus, out=buf)
        o = buf.getvalue()
        if rc != 0:
            failures.append(f"의미 WARN이 exit code에 반영됨(불간섭 위반): rc={rc}\n{o}")
        if "[WARN·의미]" not in o or "unrelated statement about quant" not in o:
            failures.append(f"붕 뜬 주장 의미 WARN 누락: {o}")
        # 진짜 규격/근거 FAIL은 여전히 exit 1
        (drafts / "real_fail.md").write_text(
            "## Summary\ns (p.2).\n## Why\ng (p.3).\n"
            "## Evidence\n- 77.7% invented accuracy (p.2)\n"
            "source_pdf: paper.pdf — arXiv:1234.56789\n", encoding="utf-8")
        buf = io.StringIO()
        if run(drafts, dial, corpus, out=buf) != 1:
            failures.append(f"발명 수치 FAIL이 exit 1 아님: {buf.getvalue()}")

    if failures:
        print("SELF-TEST FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print("SELF-TEST PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="의미 채널 — 붕 뜬 근거 WARN(판정 권한 없음·G1+)")
    ap.add_argument("--dir")
    ap.add_argument("--dial")
    ap.add_argument("--corpus")
    ap.add_argument("--source-dir")
    ap.add_argument("--sim-threshold", type=float, default=SIM_THRESHOLD,
                    help=f"이 값 미만 최대유사도면 WARN (기본 {SIM_THRESHOLD})")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if not (a.dir and a.corpus):
        ap.error("--dir 과 --corpus 필요 (또는 --self-test)")
    try:
        dial = load_dial(a.dial)
    except (ValueError, json.JSONDecodeError, OSError) as e:
        print(f"[semantic] 다이얼 오류: {e}", file=sys.stderr)
        return 2
    return run(a.dir, dial, a.corpus, a.source_dir, a.sim_threshold)


if __name__ == "__main__":
    sys.exit(main())
