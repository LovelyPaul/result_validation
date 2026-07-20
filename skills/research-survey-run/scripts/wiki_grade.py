#!/usr/bin/env python3
"""wiki_grade — retrieval·검수 게이트 평가 하네스 (wiki-demo gold+매설 패턴 이식).

"정보를 잘 가져오는지·검수가 잘 되는지"를 일화가 아니라 수치로 만든다:
  ① retrieval 채점: gold 질문셋(00-system/wiki-gold.json — 질문·기대 1위 노트 id·기대 근거
     문구)을 일괄 실행해 **1위 적중률·top-k recall**을 산출한다. 랭킹은 wiki_query.query()
     를 그대로 호출한다 — 채점기가 검색기와 다른 융합 코드를 쓰면 채점이 실물과 어긋난다
     (이중 구현 금지). 부수 산출인 질의 리포트는 wiki/queries/에 남는다(재생성 가능 산출물).
  ② gold 무결성 fail-closed: 각 문항의 기대 근거 문구가 기대 노트 본문에 글자 그대로
     존재하는지 함께 검사한다 — gold가 원문과 어긋나면 채점 자체가 무의미하다(garbage-in 차단).
  ③ 검수 게이트 채점: 오류 매설 노트(ev — 40-drafts/ev/*.md: 발명 수치·문구 오인용·출처
     없음·Timeline 변조·필수키 누락 유형)를 wiki_promote.promote(dry-run)에 통과시켜
     **거부율**을 산출한다. promote lint를 통과한 매설 노트는 2층 검사(source-coverage)로
     넘긴다 — verify_summaries의 resolve_source(원문 해결: arXiv id → corpus 초록, 또는
     --source-dir 전문 txt)와 check_evidence_grounding(수치·따옴표 문구의 원문 실재 grep)을
     **그대로 재사용**한다(이중 구현 금지 — 채점기와 검수기가 같은 코드로 판정).
     검사 범위는 Compiled Truth 본문이다(Timeline은 이력 메타라 검증 주장에 해당하지 않음).
  ④ JSON 리포트: 70-analysis/wiki-grade-report.json (문항별·매설별 상세 + 집계).

판정 어휘: rejected(게이트가 잡음) · passed(게이트가 놓침 — 거부율 하락으로 드러남) ·
unchecked(원문 해결 불가 — arXiv id 부재·코퍼스 미등재. 조용한 통과 금지, 명시 기록).

종료 코드: 기본 0(측정 리포트). --min-top1/--min-reject 임계 지정 시 미달이면 1.
gold 근거 문구 미존재(무결성 위반)는 임계와 무관하게 1 (fail-closed).

의존: python3 표준 라이브러리만. 자체 검사: `python3 wiki_grade.py --self-test`
(외부 의존 0·tempfile 격리 — source-coverage 층도 실제 verify_summaries 함수로 검증).
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wiki_query import query, load_notes, NOTES_REL          # noqa: E402 — 융합 랭킹 공유
from wiki_promote import promote, parse_frontmatter, split_sections   # noqa: E402
from verify_summaries import resolve_source, check_evidence_grounding  # noqa: E402 — 검수와 동일 코드

GOLD_REL = "00-system/wiki-gold.json"
EV_REL = "40-drafts/ev"
CORPUS_REL = "60-data/corpus.json"
REPORT_REL = "70-analysis/wiki-grade-report.json"
DEFAULT_K = 5


def grade_retrieval(workspace, questions, k):
    """gold 질문셋 일괄 실행 → 1위 적중률·top-k recall + gold 무결성(근거 문구 실재) 검사."""
    notes = load_notes(Path(workspace) / NOTES_REL)
    results = []
    for g in questions:
        q, exp = g["question"], g["expected_top1"]
        _out, union, _ch = query(workspace, q, k)   # wiki_query와 같은 코드 경로 (이중 구현 금지)
        top1 = union[0] if union else None
        exp_note = notes.get(exp)
        # gold 무결성 fail-closed (R1): expected_evidence 누락·빈 문자열·공백만이면 'in body'
        # 검사 전에 위반이다 — '' in body 는 항상 True라 조용히 통과하는 구멍(codex 재현).
        ev_phrase = (g.get("expected_evidence") or "").strip()
        results.append({
            "question": q,
            "expected_top1": exp,
            "got_top1": top1,
            "top1_hit": top1 == exp,
            "in_topk": exp in union,
            "rank": (union.index(exp) + 1) if exp in union else None,
            "evidence_in_note": bool(ev_phrase) and bool(exp_note) and ev_phrase in exp_note["body"],
        })
    n = len(results)
    hits = sum(r["top1_hit"] for r in results)
    recall = sum(r["in_topk"] for r in results)
    return {
        "n": n,
        "k": k,
        "top1_hits": hits,
        "top1_rate": round(hits / n, 4) if n else None,
        "topk_recall": round(recall / n, 4) if n else None,
        "gold_evidence_missing": sorted(
            {r["expected_top1"] for r in results if not r["evidence_in_note"]}),
        "per_question": results,
    }


def grade_gates(workspace, ev_dir, corpus_path, source_dir=None):
    """매설 노트를 검수 게이트 체인(①promote lint dry-run → ②source-coverage)에 통과시켜
    거부율 산출. dry-run만 사용 — 정본·manifest를 절대 건드리지 않는다.
    ②는 verify_summaries의 resolve_source·check_evidence_grounding 재사용 — 검사 대상은
    Compiled Truth 본문(Evidence 절 형태로 감싸 동일 코드 경로에 태운다)."""
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
        text = f.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        r = promote(str(workspace), str(f), apply=False)   # dry-run — 부작용 0
        # ev_expect: reject(기본 — 매설, 게이트가 잡아야 정상) | pass(clean 대조군 —
        # 게이트가 통과시켜야 정상: 과차단 감시. R1 claude-1 minor)
        expected = "pass" if fm.get("ev_expect", "reject") == "pass" else "reject"
        entry = {"file": f.name, "id": r["id"], "ev_type": fm.get("ev_type", ""),
                 "expected": expected}
        if r["problems"]:
            entry.update(verdict="rejected", layer="promote",
                         reasons=[str(p) for p in r["problems"]])
        else:
            # ② promote lint 통과분 → source-coverage 층 (Compiled Truth 본문만 검사)
            src_text, _abstract, why = resolve_source(text, corpus_by_id, source_dir)
            if src_text is None:
                entry.update(verdict="unchecked", layer="source-coverage",
                             reasons=[f"원문 해결 불가 — {why}"])
            else:
                ct, _tl = split_sections(body)
                fails = check_evidence_grounding(
                    "## Evidence\n" + (ct if ct is not None else body), src_text)
                if fails:
                    entry.update(verdict="rejected", layer="source-coverage",
                                 reasons=[str(x) for x in fails])
                elif expected == "pass":
                    entry.update(verdict="passed", layer="source-coverage",
                                 reasons=["대조군 통과 — 게이트 과차단 없음(정상)"])
                else:
                    entry.update(verdict="passed", layer="source-coverage",
                                 reasons=["게이트 체인이 잡지 못함 — 매설 유형·검사 규칙을 점검하라"])
        entry["as_expected"] = (entry["verdict"] == "rejected") == (expected == "reject")
        results.append(entry)

    seeded = [r for r in results if r["expected"] == "reject"]
    controls = [r for r in results if r["expected"] == "pass"]
    rejected = sum(1 for r in seeded if r["verdict"] == "rejected")
    return {
        "n": len(results),
        "seeded": len(seeded),
        "rejected": rejected,
        "passed": sum(1 for r in results if r["verdict"] == "passed"),
        "unchecked": sum(1 for r in results if r["verdict"] == "unchecked"),
        # 거부율 분모는 매설(expected=reject)만 — 대조군을 섞으면 수치가 조용히 희석된다
        "reject_rate": round(rejected / len(seeded), 4) if seeded else None,
        "controls": len(controls),
        "controls_passed": sum(1 for r in controls if r["verdict"] == "passed"),
        "overblocked_controls": [r["file"] for r in controls if r["verdict"] == "rejected"],
        "per_note": results,
    }


def run(workspace, gold_path, ev_dir, corpus_path, k=None, source_dir=None):
    gold_p = Path(gold_path)
    if not gold_p.exists():
        raise SystemExit(f"gold 질문셋 없음: {gold_p} — 템플릿 00-system/wiki-gold.sample.json 을 "
                         f"워크스페이스 00-system/wiki-gold.json 으로 복사하라.")
    gold = json.loads(gold_p.read_text(encoding="utf-8"))
    questions = gold.get("questions") or []
    if not questions:
        raise SystemExit(f"gold 질문 0건: {gold_p} — questions 배열이 비어 있다.")
    k = k or int(gold.get("k", DEFAULT_K))
    report = {
        "generated": str(date.today()),
        "workspace": str(Path(workspace).resolve()),
        "gold": str(gold_p),
        "retrieval": grade_retrieval(workspace, questions, k),
        "gate": grade_gates(workspace, ev_dir, corpus_path, source_dir=source_dir),
    }
    out = Path(workspace) / REPORT_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report, out


def _print_summary(report, out):
    r, g = report["retrieval"], report["gate"]
    print(f"채점 리포트: {out}")
    print(f"retrieval: 질문 {r['n']} · 1위 적중 {r['top1_hits']} ({r['top1_rate'] * 100:.1f}%) · "
          f"top-{r['k']} recall {r['topk_recall'] * 100:.1f}%")
    for q in r["per_question"]:
        mark = "O" if q["top1_hit"] else ("~" if q["in_topk"] else "X")
        print(f"  [{mark}] {q['question'][:44]} → 기대 {q['expected_top1']} / "
              f"실측 {q['got_top1']} (rank {q['rank']})")
    if r["gold_evidence_missing"]:
        print(f"  ⚠ gold 무결성 위반 — 기대 근거 문구가 비었거나 노트 본문에 없음: {r['gold_evidence_missing']}")
    rate = f"{g['reject_rate'] * 100:.1f}%" if g["reject_rate"] is not None else "판정 불가(매설 0건)"
    print(f"gate: 매설 {g['seeded']} · 거부 {g['rejected']} ({rate}) · "
          f"대조군 {g['controls']} 통과 {g['controls_passed']} · 미판정 {g['unchecked']}")
    if g["overblocked_controls"]:
        print(f"  ⚠ 대조군 과차단(정상 노트를 거부): {g['overblocked_controls']}")
    for e in g["per_note"]:
        mark = "" if e["as_expected"] else " ⚠기대 불일치"
        print(f"  [{e['verdict']}]{mark} {e['file']} ({e['ev_type']}) @ {e['layer']}: {e['reasons'][0][:80]}")


def _self_test():
    import tempfile
    failures = []
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        notes = ws / NOTES_REL
        notes.mkdir(parents=True)
        (notes / "alpha.md").write_text(
            "---\nid: alpha\ntitle: LLM Pretraining\ncreated: 2026-07-20\ntags: [llm]\n"
            "source: arXiv:2401.11111, p.3\n---\n## Compiled Truth\n\n"
            "대규모 언어모델 사전학습 데이터 품질과 중복 제거 (p.3)\n\n## Timeline\n\n- 2026-07-20 작성\n",
            encoding="utf-8")
        (notes / "beta.md").write_text(
            "---\nid: beta\ntitle: Medical Seg\ncreated: 2026-07-20\ntags: [medical]\n"
            "source: arXiv:2402.22222, p.5\n---\n## Compiled Truth\n\n"
            "의료 영상 분할 합성 데이터 증강 기법 (p.5)\n\n## Timeline\n\n- 2026-07-20 작성\n",
            encoding="utf-8")
        # gold: 적중 2 + 의도 미스 1(합성 데이터 증강 → beta가 1위, 기대는 alpha) + 무결성 위반 1
        gold = ws / "00-system" / "wiki-gold.json"
        gold.parent.mkdir(parents=True)
        gold.write_text(json.dumps({"k": 5, "questions": [
            {"question": "언어모델 사전학습 품질", "expected_top1": "alpha",
             "expected_evidence": "데이터 품질"},
            {"question": "의료 영상 분할", "expected_top1": "beta",
             "expected_evidence": "합성 데이터 증강"},
            {"question": "합성 데이터 증강 기법", "expected_top1": "alpha",
             "expected_evidence": "본문에 존재하지 않는 문구"},
            # R1: 공백만인 evidence — '' in body 항상 True 구멍의 회귀 케이스 (위반이어야 함)
            {"question": "의료 영상 분할 증강", "expected_top1": "beta",
             "expected_evidence": "   "},
        ]}, ensure_ascii=False), encoding="utf-8")
        # 코퍼스: ev 소스 검사용 초록 (88.8%만 실재 — 94.2%는 발명)
        corpus = ws / CORPUS_REL
        corpus.parent.mkdir(parents=True)
        corpus.write_text(json.dumps([
            {"id": "1234.56789", "title": "T",
             "abstract": "The measured accuracy is 88.8% on the benchmark."},
        ]), encoding="utf-8")
        # ev 3종: 출처없음(promote 거부) · 발명수치(coverage 거부) · 게이트가 못 잡는 대조군(passed)
        ev = ws / EV_REL
        ev.mkdir(parents=True)
        (ev / "ev-no-source.md").write_text(
            "---\nid: ev-no-source\ntitle: EV NoSource\ncreated: 2026-07-21\ntags: [ev]\n---\n"
            "## Compiled Truth\n\n무근거 주장.\n\n## Timeline\n\n- 매설\n", encoding="utf-8")
        (ev / "ev-num.md").write_text(
            "---\nid: ev-num\ntitle: EV Num\ncreated: 2026-07-21\ntags: [ev]\nsource: arXiv:1234.56789\n"
            "ev_type: invented-number\n---\n## Compiled Truth\n\n정확도 94.2%를 달성 (arXiv:1234.56789 abstract).\n\n"
            "## Timeline\n\n- 2026-07-21 매설\n", encoding="utf-8")
        (ev / "ev-clean.md").write_text(
            "---\nid: ev-clean\ntitle: EV Clean\ncreated: 2026-07-21\ntags: [ev]\nsource: arXiv:1234.56789\n"
            "ev_type: clean-control\nev_expect: pass\n---\n"
            "## Compiled Truth\n\n정확도 88.8%를 보고 (arXiv:1234.56789 abstract).\n\n"
            "## Timeline\n\n- 2026-07-21 대조군\n", encoding="utf-8")

        report, out = run(str(ws), gold, ev, corpus)
        r, g = report["retrieval"], report["gate"]
        if not out.exists():
            failures.append("리포트 JSON 미생성")
        if r["top1_hits"] != 3 or r["n"] != 4:
            failures.append(f"retrieval 적중 집계 오류: hits={r['top1_hits']} n={r['n']}")
        if r["topk_recall"] != 1.0:
            failures.append(f"top-k recall 오류(alpha는 rank>1이어도 top-k 내 기대): {r['topk_recall']}")
        # R1: 본문 미존재(alpha) + 공백만 evidence(beta) 둘 다 무결성 위반으로 잡혀야 한다
        if r["gold_evidence_missing"] != ["alpha", "beta"]:
            failures.append(f"gold 무결성 위반 미탐지(빈 evidence 포함): {r['gold_evidence_missing']}")
        by = {e["file"]: e for e in g["per_note"]}
        if by["ev-no-source.md"]["verdict"] != "rejected" or by["ev-no-source.md"]["layer"] != "promote":
            failures.append(f"출처없음 promote 거부 실패: {by['ev-no-source.md']}")
        if by["ev-num.md"]["verdict"] != "rejected" or by["ev-num.md"]["layer"] != "source-coverage":
            failures.append(f"발명수치 coverage 거부 실패: {by['ev-num.md']}")
        if not (by["ev-clean.md"]["verdict"] == "passed" and by["ev-clean.md"]["expected"] == "pass"
                and by["ev-clean.md"]["as_expected"]):
            failures.append(f"대조군(ev_expect: pass) 판정 오류: {by['ev-clean.md']}")
        if g["seeded"] != 2 or g["rejected"] != 2 or g["reject_rate"] != 1.0:
            failures.append(f"거부율 집계 오류(분모=매설만): seeded={g['seeded']} "
                            f"rejected={g['rejected']} rate={g['reject_rate']}")
        if g["controls"] != 1 or g["controls_passed"] != 1 or g["overblocked_controls"]:
            failures.append(f"대조군 집계 오류: {g['controls']}/{g['controls_passed']}/"
                            f"{g['overblocked_controls']}")
        # 정본·manifest 무변조 (dry-run 불변식)
        if (ws / NOTES_REL / "ev-num.md").exists() or (ws / "20-knowledge-base/wiki/promotion-manifest.jsonl").exists():
            failures.append("채점이 정본/manifest를 변조함 (dry-run 위반)")
        # 코퍼스에 없는 소스 id → unchecked (원문 해결 불가 — 조용한 통과 금지)
        (ev / "ev-clean.md").write_text(
            (ev / "ev-clean.md").read_text(encoding="utf-8").replace("1234.56789", "9999.99999"),
            encoding="utf-8")
        report3, _ = run(str(ws), gold, ev, corpus)
        by3 = {e["file"]: e for e in report3["gate"]["per_note"]}
        if by3["ev-clean.md"]["verdict"] != "unchecked" or "원문 해결 불가" not in by3["ev-clean.md"]["reasons"][0]:
            failures.append(f"미등재 소스 unchecked 미기록: {by3['ev-clean.md']}")
        # ev 폴더 없음 → 명시 SystemExit
        try:
            grade_gates(str(ws), ws / "40-drafts" / "none", corpus)
            failures.append("빈 ev 폴더를 조용히 통과시킴")
        except SystemExit as e:
            if "매설 노트 없음" not in str(e):
                failures.append(f"빈 ev 진단 메시지 이상: {e}")

    if failures:
        print("SELF-TEST FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print("SELF-TEST PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="wiki retrieval·검수 게이트 채점 (gold 질문셋 적중률·top-k recall + 매설 노트 거부율)")
    ap.add_argument("--workspace", default=".", help="워크스페이스 루트 (기본: 현재 폴더)")
    ap.add_argument("--gold", help=f"gold 질문셋 JSON (기본: <workspace>/{GOLD_REL})")
    ap.add_argument("--ev-dir", help=f"매설 노트 폴더 (기본: <workspace>/{EV_REL})")
    ap.add_argument("--corpus", help=f"소스 초록 코퍼스 (기본: <workspace>/{CORPUS_REL})")
    ap.add_argument("--source-dir", help="PDF 추출 .txt 폴더 — 실재 대조 원문으로 초록보다 우선(verify_summaries와 동일)")
    ap.add_argument("-k", "--topk", type=int, help="top-k (기본: gold의 k, 없으면 5)")
    ap.add_argument("--min-top1", type=float, help="1위 적중률 임계 (미달 시 exit 1)")
    ap.add_argument("--min-reject", type=float, help="매설 거부율 임계 (미달 시 exit 1)")
    ap.add_argument("--self-test", action="store_true", help="외부 의존 없는 자체 검사")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(_self_test())
    ws = Path(a.workspace)
    report, out = run(ws,
                      a.gold or ws / GOLD_REL,
                      a.ev_dir or ws / EV_REL,
                      a.corpus or ws / CORPUS_REL,
                      k=a.topk, source_dir=a.source_dir)
    _print_summary(report, out)
    bad = []
    if report["retrieval"]["gold_evidence_missing"]:
        bad.append("gold 무결성 위반 (기대 근거 문구가 노트 본문에 없음)")
    if a.min_top1 is not None and report["retrieval"]["top1_rate"] < a.min_top1:
        bad.append(f"1위 적중률 {report['retrieval']['top1_rate']} < 임계 {a.min_top1}")
    if a.min_reject is not None and (report["gate"]["reject_rate"] or 0.0) < a.min_reject:
        bad.append(f"매설 거부율 {report['gate']['reject_rate']} < 임계 {a.min_reject}")
    if bad:
        print("FAIL: " + " · ".join(bad))
        sys.exit(1)


if __name__ == "__main__":
    main()
