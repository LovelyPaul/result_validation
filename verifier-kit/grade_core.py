#!/usr/bin/env python3
# [verifier-kit] 검수기 채점 하네스 — verify_core를 그대로 재사용(이중 구현 금지)
"""grade_core — "이 검수기를 믿을 수 있나?"를 일화가 아니라 수치로 만든다 (G3).

오류를 일부러 심은 노트(매설, seeded-error)를 검수 게이트에 통과시켜 **거부율**을 산출하고,
정상 노트(대조군, control)로 **과차단**(정상을 거부하는 것)까지 감시한다.

핵심 설계 (원본 wiki_grade.py에서 이식):
  - **이중 구현 금지**: 판정은 verify_core.check_structural·check_evidence_grounding을
    **그대로 호출**한다. 채점기가 검수기와 다른 코드를 쓰면 "채점은 통과인데 실물은 실패"
    하는 괴리가 생긴다 — 같은 코드 경로로 원천 차단.
  - **대조군 분리**: 거부율 분모는 매설(expected=reject)만. 대조군을 분모에 섞으면
    수치가 조용히 희석된다. 대조군은 과차단 감시에만 쓴다.
  - **fail-closed 존중**: verify_core가 원문 미해결을 FAIL로 내면 그대로 반영. 단 채점
    관점에서 "게이트가 오류라서 잡음"과 "원문을 못 찾아 잡음"은 다르므로 verdict를 구분한다.

매설 노트 형식 (도메인 무관 — 검수 대상 md에 헤더 메타 주석만 추가):
  <!-- ev_type: invented-number -->      ← 매설 유형(리포트 라벨)
  <!-- ev_expect: reject -->             ← 기대 판정. reject(기본·매설) | pass(대조군)
  ...나머지는 그 도메인 다이얼이 검수하는 정상 산출물 형식...

판정 어휘:
  rejected  — 게이트가 잡음 (매설이면 정상, 대조군이면 과차단)
  passed    — 게이트가 통과 (대조군이면 정상, 매설이면 놓침 → 거부율 하락)
  unchecked — 원문 해결 불가(id 부재·코퍼스 미등재). 조용한 통과 금지, 명시 기록.

사용:  python3 grade_core.py --ev-dir <매설 폴더> --dial dials/<도메인>.json --corpus <corpus.json>
           [--source-dir <txt폴더>] [--min-reject 0.8] [--report <경로>]
반환:  0=측정 완료(또는 임계 충족) · 1=임계 미달/과차단 · 2=입력 오류
자체 검사: python3 grade_core.py --self-test (외부 의존 0·tempfile 격리 — 실제 verify_core로 판정)
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_core import (load_dial, check_structural,           # noqa: E402 — 검수와 동일 코드
                         resolve_source, check_evidence_grounding)

_EV_TYPE = re.compile(r"<!--\s*ev_type:\s*([^\s>-][^>]*?)\s*-->", re.I)
_EV_EXPECT = re.compile(r"<!--\s*ev_expect:\s*(reject|pass|unchecked)\s*-->", re.I)


def _meta(text):
    """매설 노트 헤더 메타 파싱 → (ev_type, expected). 기본 expected=reject.
    expected 값: reject(매설·게이트가 잡아야) | pass(대조군·통과해야) |
    unchecked(fail-closed 시연·원문 미해결로 unchecked가 나와야 정상)."""
    tm = _EV_TYPE.search(text)
    em = _EV_EXPECT.search(text)
    ev_type = tm.group(1).strip() if tm else ""
    expected = (em.group(1).lower() if em else "reject")
    return ev_type, expected


def grade_gate(ev_dir, dial, corpus_path, source_dir=None):
    """매설 노트를 검수 게이트(규격 → 근거)에 통과시켜 거부율 산출.
    검수 대상·부작용 없음(read-only) — 정본을 만들지 않는다."""
    ev_files = sorted(Path(ev_dir).glob("*.md"))
    if not ev_files:
        raise SystemExit(f"매설 노트 없음: {ev_dir} — ev 노트를 두거나 --ev-dir 을 지정하라.")
    corpus_by_id = {}
    cp = Path(corpus_path)
    if cp.exists():
        try:
            for e in json.loads(cp.read_text(encoding="utf-8")):
                if isinstance(e, dict) and e.get("id"):
                    corpus_by_id[str(e["id"])] = e
        except json.JSONDecodeError as e:
            raise SystemExit(f"코퍼스 JSON 파싱 실패: {cp} — {e}")

    results = []
    for f in ev_files:
        text = f.read_text(encoding="utf-8", errors="replace")
        ev_type, expected = _meta(text)
        entry = {"file": f.name, "ev_type": ev_type, "expected": expected}

        # ① 규격 층 (다이얼 required_sections·cite·placeholder·source_marker)
        struct_fails = check_structural(text, dial)
        if struct_fails:
            entry.update(verdict="rejected", layer="structural",
                         reasons=struct_fails)
        else:
            # ② 근거 층 — verify_core와 동일 코드로 원문 실재 대조
            src_text, _abstract, why = resolve_source(text, corpus_by_id, source_dir, dial)
            if src_text is None:
                entry.update(verdict="unchecked", layer="grounding",
                             reasons=[f"원문 해결 불가 — {why}"])
            else:
                fails = check_evidence_grounding(text, src_text, dial)
                if fails:
                    entry.update(verdict="rejected", layer="grounding", reasons=fails)
                elif expected == "pass":
                    entry.update(verdict="passed", layer="grounding",
                                 reasons=["대조군 통과 — 과차단 없음(정상)"])
                else:
                    entry.update(verdict="passed", layer="grounding",
                                 reasons=["게이트가 못 잡음 — 매설 유형·검사 규칙을 점검하라"])
        # 기대 판정: reject→rejected, pass→passed, unchecked→unchecked 여야 as_expected
        want = {"reject": "rejected", "pass": "passed", "unchecked": "unchecked"}[expected]
        entry["as_expected"] = entry["verdict"] == want
        results.append(entry)

    seeded = [r for r in results if r["expected"] == "reject"]
    controls = [r for r in results if r["expected"] == "pass"]
    rejected = sum(1 for r in seeded if r["verdict"] == "rejected")
    return {
        "dial": dial.name,
        "n": len(results),
        "seeded": len(seeded),
        "rejected": rejected,
        # 거부율 분모 = 매설만 (대조군 섞으면 조용히 희석)
        "reject_rate": round(rejected / len(seeded), 4) if seeded else None,
        "unchecked": sum(1 for r in results if r["verdict"] == "unchecked"),
        "controls": len(controls),
        "controls_passed": sum(1 for r in controls if r["verdict"] == "passed"),
        "overblocked_controls": [r["file"] for r in controls if r["verdict"] == "rejected"],
        "per_note": results,
    }


def run(ev_dir, dial, corpus_path, source_dir=None, report_path=None):
    report = {"generated": str(date.today()), "gate": grade_gate(ev_dir, dial, corpus_path, source_dir)}
    if report_path:
        rp = Path(report_path)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _print_summary(report, out=sys.stdout):
    g = report["gate"]
    rate = f"{g['reject_rate'] * 100:.1f}%" if g["reject_rate"] is not None else "판정 불가(매설 0건)"
    print(f"채점[{g['dial']}]: 매설 {g['seeded']} · 거부 {g['rejected']} ({rate}) · "
          f"대조군 {g['controls']} 통과 {g['controls_passed']} · 미판정 {g['unchecked']}", file=out)
    if g["overblocked_controls"]:
        print(f"  ⚠ 대조군 과차단(정상 노트를 거부): {g['overblocked_controls']}", file=out)
    for e in g["per_note"]:
        mark = "" if e["as_expected"] else " ⚠기대 불일치"
        print(f"  [{e['verdict']}]{mark} {e['file']} ({e['ev_type']}) @ {e['layer']}: "
              f"{e['reasons'][0][:80]}", file=out)


# ── self-test (실제 verify_core로 판정 — 이중 구현 금지 검증) ────────
def _self_test():
    import io
    import tempfile
    from verify_core import Dial, BUILTIN_PAPER_DIAL
    failures = []
    dial = Dial(BUILTIN_PAPER_DIAL)

    _CORPUS = [{"id": "1234.56789", "title": "T",
                "abstract": "The measured accuracy is 88.8% on the benchmark suite here."}]

    # 매설 5종 + 대조군 1종
    NOTES = {
        # 발명 수치 (근거 층이 잡아야) — reject
        "ev-invented.md": ("<!-- ev_type: invented-number -->\n"
            "## Summary\nHigh accuracy (p.2).\n## Why\ng (p.3).\n"
            "## Evidence\n- 94.2% accuracy achieved (Table 1, p.6)\n"
            "source_pdf: 1234.56789.pdf — arXiv:1234.56789\n"),
        # 오인용 문구 (근거 층) — reject
        "ev-miscite.md": ("<!-- ev_type: quote-miscite -->\n"
            "## Summary\ns (p.2).\n## Why\ng (p.3).\n"
            "## Evidence\n- \"outperforms every human baseline decisively\" (p.4)\n"
            "- 88.8% (Table 1)\n"
            "source_pdf: 1234.56789.pdf — arXiv:1234.56789\n"),
        # 섹션 누락 (규격 층) — reject
        "ev-missing-sec.md": ("<!-- ev_type: missing-section -->\n"
            "## Summary\ns (p.2, p.3, Table 1).\n"
            "source_pdf: 1234.56789.pdf — arXiv:1234.56789\n"),
        # 소스 표기 없음 (규격 층) — reject
        "ev-no-source.md": ("<!-- ev_type: no-source -->\n"
            "## Summary\ns (p.2).\n## Why\ng (p.3).\n## Evidence\n- 88.8% (Table 1)\n"),
        # 원문 미등재 id → unchecked (조용한 통과 금지·fail-closed 시연)
        "ev-noid.md": ("<!-- ev_type: unresolved-source -->\n<!-- ev_expect: unchecked -->\n"
            "## Summary\ns (p.2).\n## Why\ng (p.3).\n## Evidence\n- 88.8% (Table 1)\n"
            "source_pdf: 9999.99999.pdf — arXiv:9999.99999\n"),
        # 대조군: 모든 수치 실재 (88.8%) — pass 기대
        "ev-clean.md": ("<!-- ev_type: clean-control -->\n<!-- ev_expect: pass -->\n"
            "## Summary\nThe measured accuracy is 88.8% (p.2).\n## Why\ng (p.3).\n"
            "## Evidence\n- 88.8% accuracy (Table 1)\n"
            "source_pdf: 1234.56789.pdf — arXiv:1234.56789\n"),
    }

    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        ev = ws / "ev"
        ev.mkdir()
        for name, body in NOTES.items():
            (ev / name).write_text(body, encoding="utf-8")
        corpus = ws / "corpus.json"
        corpus.write_text(json.dumps(_CORPUS), encoding="utf-8")

        report = run(ev, dial, corpus, report_path=ws / "report.json")
        g = report["gate"]
        by = {e["file"]: e for e in g["per_note"]}

        # 리포트 파일 생성
        if not (ws / "report.json").exists():
            failures.append("리포트 JSON 미생성")
        # 발명 수치·오인용 → 근거 층 rejected
        if by["ev-invented.md"]["verdict"] != "rejected" or by["ev-invented.md"]["layer"] != "grounding":
            failures.append(f"발명 수치 근거 거부 실패: {by['ev-invented.md']}")
        if by["ev-miscite.md"]["verdict"] != "rejected" or by["ev-miscite.md"]["layer"] != "grounding":
            failures.append(f"오인용 근거 거부 실패: {by['ev-miscite.md']}")
        # 섹션 누락·소스 없음 → 규격 층 rejected
        if by["ev-missing-sec.md"]["verdict"] != "rejected" or by["ev-missing-sec.md"]["layer"] != "structural":
            failures.append(f"섹션 누락 규격 거부 실패: {by['ev-missing-sec.md']}")
        if by["ev-no-source.md"]["verdict"] != "rejected" or by["ev-no-source.md"]["layer"] != "structural":
            failures.append(f"소스 없음 규격 거부 실패: {by['ev-no-source.md']}")
        # 미등재 id → unchecked (조용한 통과 금지)·ev_expect:unchecked 선언이라 as_expected여야
        if by["ev-noid.md"]["verdict"] != "unchecked" or "원문 해결 불가" not in by["ev-noid.md"]["reasons"][0]:
            failures.append(f"미등재 id unchecked 미기록: {by['ev-noid.md']}")
        if not by["ev-noid.md"]["as_expected"]:
            failures.append(f"unchecked 선언 노트를 기대 불일치로 표기: {by['ev-noid.md']}")
        # 대조군 → passed·과차단 없음
        if by["ev-clean.md"]["verdict"] != "passed" or by["ev-clean.md"]["expected"] != "pass":
            failures.append(f"대조군 통과 판정 오류: {by['ev-clean.md']}")
        # 집계: 매설 4(noid는 expected=unchecked라 제외) · 거부 4 · 분모=매설만 → 100%
        if g["seeded"] != 4:
            failures.append(f"매설 집계 오류(noid·대조군 제외해야 4): seeded={g['seeded']}")
        if g["rejected"] != 4:
            failures.append(f"거부 집계 오류: rejected={g['rejected']}")
        if g["reject_rate"] != 1.0:
            failures.append(f"거부율 오류(분모=매설4·전건 거부→1.0): {g['reject_rate']}")
        if g["controls"] != 1 or g["controls_passed"] != 1 or g["overblocked_controls"]:
            failures.append(f"대조군 집계 오류: {g['controls']}/{g['controls_passed']}/{g['overblocked_controls']}")

        # 과차단 감지: 대조군을 발명 수치로 오염시키면 overblocked에 잡혀야
        (ev / "ev-clean.md").write_text(
            "<!-- ev_type: clean-control -->\n<!-- ev_expect: pass -->\n"
            "## Summary\ns (p.2).\n## Why\ng (p.3).\n"
            "## Evidence\n- 77.7% accuracy (Table 1)\n"   # 원문에 없는 수치
            "source_pdf: 1234.56789.pdf — arXiv:1234.56789\n", encoding="utf-8")
        g2 = run(ev, dial, corpus)["gate"]
        if g2["overblocked_controls"] != ["ev-clean.md"]:
            failures.append(f"과차단 감지 실패: {g2['overblocked_controls']}")

        # 빈 ev 폴더 → 명시 SystemExit
        try:
            grade_gate(ws / "none", dial, corpus)
            failures.append("빈 ev 폴더를 조용히 통과시킴")
        except SystemExit as e:
            if "매설 노트 없음" not in str(e):
                failures.append(f"빈 ev 진단 이상: {e}")

    if failures:
        print("SELF-TEST FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print("SELF-TEST PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="검수기 채점 하네스 — 매설 거부율·대조군 과차단 (G3)")
    ap.add_argument("--ev-dir", help="매설 노트 폴더")
    ap.add_argument("--dial", help="도메인 다이얼 JSON (미지정 시 내장 논문 다이얼)")
    ap.add_argument("--corpus", help="원문 초록 코퍼스 JSON")
    ap.add_argument("--source-dir", help="원문 추출 .txt 폴더 — abstract보다 우선(verify_core와 동일)")
    ap.add_argument("--report", help="리포트 JSON 출력 경로")
    ap.add_argument("--min-reject", type=float, help="매설 거부율 임계 (미달 시 exit 1)")
    ap.add_argument("--self-test", action="store_true", help="외부 의존 없는 자체 검사")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if not a.ev_dir or not a.corpus:
        ap.error("--ev-dir 과 --corpus 필요 (또는 --self-test)")
    try:
        dial = load_dial(a.dial)
    except (ValueError, json.JSONDecodeError, OSError) as e:
        print(f"[grade] 다이얼 오류: {e}", file=sys.stderr)
        return 2
    report = run(a.ev_dir, dial, a.corpus, a.source_dir, a.report)
    _print_summary(report)
    g = report["gate"]
    bad = []
    if a.min_reject is not None and (g["reject_rate"] or 0.0) < a.min_reject:
        bad.append(f"매설 거부율 {g['reject_rate']} < 임계 {a.min_reject}")
    if g["overblocked_controls"]:
        bad.append(f"대조군 과차단: {g['overblocked_controls']}")
    if bad:
        print("FAIL: " + " · ".join(bad))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
