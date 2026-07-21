#!/usr/bin/env python3
# [기능군: state] 파이프라인 상태 머신 — 중단·재개 추적 (독립·상호 import 없음)
"""run_state — 서베이 run 사이클의 단계 상태를 `_meta/run-state.json`에 결정론으로 기록/재개.

agy#11(파이프라인 State Management): 장기 서베이가 중단·에러로 끊겨도 어느 단계까지 됐는지를
JSON 상태로 남겨 **누락 없이 재개**한다(하네스 견고성). LLM 판단이 아니라 단계 enum·완료
플래그·재개 포인터만 다루는 결정론 도구다.

상태 파일 스키마(`<workspace>/_meta/run-state.json`):
  {
    "category": "<대상 카테고리|null>",
    "created": "YYYY-MM-DD",
    "updated": "YYYY-MM-DD",
    "stages": [ {"name": "extract", "status": "done|pending|in_progress|failed", "note": ""}, ... ],
    "resume": "<첫 비-done 단계 이름|null(전부 done)>"
  }

run 사이클 단계(research-survey-run SKILL 절차와 일치):
  extract → shortlist → summarize → verify → organize → delta

사용:
  python3 run_state.py --workspace . init [--category <cat>]
  python3 run_state.py --workspace . mark <stage> <status> [--note "..."]
  python3 run_state.py --workspace . show          # 현재 상태·재개 포인터 출력
자체 검사: `python3 run_state.py --self-test` (외부 의존 0·날짜 주입·tempfile 격리).
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

STATE_REL = "_meta/run-state.json"
STAGES = ("extract", "shortlist", "summarize", "verify", "organize", "delta")
STATUSES = ("pending", "in_progress", "done", "failed")


def _path(workspace):
    return Path(workspace) / STATE_REL


def _resume(stages):
    """재개 포인터 — 첫 비-done 단계 이름(전부 done이면 None)."""
    for s in stages:
        if s["status"] != "done":
            return s["name"]
    return None


def init_state(workspace, category=None, stages=STAGES, today=None):
    """상태 파일 생성/초기화 — 모든 단계 pending. today는 자체검사 주입용(기본 오늘)."""
    d = today or date.today().isoformat()
    state = {
        "category": category,
        "created": d,
        "updated": d,
        "stages": [{"name": n, "status": "pending", "note": ""} for n in stages],
    }
    state["resume"] = _resume(state["stages"])
    _write(workspace, state)
    return state


def load(workspace):
    p = _path(workspace)
    if not p.exists():
        raise SystemExit(f"run-state 없음: {p} — 먼저 init 하라(python3 run_state.py --workspace . init).")
    return json.loads(p.read_text(encoding="utf-8"))


def _write(workspace, state):
    p = _path(workspace)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def mark(workspace, stage, status, note="", today=None):
    """단계 상태 갱신 + 재개 포인터 재계산. 미지 단계·상태는 fail-closed(SystemExit)."""
    if status not in STATUSES:
        raise SystemExit(f"미지 상태: {status!r} — 허용: {'/'.join(STATUSES)}")
    state = load(workspace)
    names = [s["name"] for s in state["stages"]]
    if stage not in names:
        raise SystemExit(f"미지 단계: {stage!r} — 허용: {'/'.join(names)}")
    for s in state["stages"]:
        if s["name"] == stage:
            s["status"] = status
            if note:
                s["note"] = note
    state["updated"] = today or date.today().isoformat()
    state["resume"] = _resume(state["stages"])
    _write(workspace, state)
    return state


def _self_test():
    import tempfile
    failures = []
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        st = init_state(str(ws), category="eval", today="2026-07-21")
        if not _path(ws).exists():
            failures.append("init이 상태 파일 미생성")
        if st["resume"] != "extract" or [s["status"] for s in st["stages"]] != ["pending"] * len(STAGES):
            failures.append(f"init 초기 상태 오류: resume={st['resume']}")
        # 순차 완료 → resume 포인터 전진
        mark(str(ws), "extract", "done", today="2026-07-21")
        st2 = mark(str(ws), "shortlist", "done", today="2026-07-21")
        if st2["resume"] != "summarize":
            failures.append(f"재개 포인터 전진 오류: {st2['resume']} (기대 summarize)")
        # 중간 failed는 done이 아니므로 resume이 거기서 멈춰야
        st3 = mark(str(ws), "summarize", "failed", note="PDF 손상", today="2026-07-22")
        if st3["resume"] != "summarize":
            failures.append(f"failed 단계에서 resume 정지 실패: {st3['resume']}")
        if st3["updated"] != "2026-07-22":
            failures.append(f"updated 갱신 오류: {st3['updated']}")
        loaded = load(str(ws))
        if [s for s in loaded["stages"] if s["name"] == "summarize"][0]["note"] != "PDF 손상":
            failures.append("note 영속 실패")
        # 전 단계 done → resume None
        for n in STAGES:
            mark(str(ws), n, "done", today="2026-07-22")
        if load(str(ws))["resume"] is not None:
            failures.append("전건 done인데 resume이 None 아님")
        # 미지 단계·상태 fail-closed
        for bad in (("nope", "done"), ("extract", "weird")):
            try:
                mark(str(ws), bad[0], bad[1])
                failures.append(f"미지 인자 통과: {bad}")
            except SystemExit:
                pass
        # init 없이 load → 명시 SystemExit
        with tempfile.TemporaryDirectory() as d2:
            try:
                load(d2)
                failures.append("init 없이 load가 통과")
            except SystemExit as e:
                if "없음" not in str(e):
                    failures.append(f"load 부재 진단 이상: {e}")
    if failures:
        print("SELF-TEST FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print("SELF-TEST PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="서베이 run 사이클 상태 머신 (중단·재개 추적)")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p_init = sub.add_parser("init", help="상태 파일 초기화(전 단계 pending)")
    p_init.add_argument("--category", default=None)
    p_mark = sub.add_parser("mark", help="단계 상태 갱신")
    p_mark.add_argument("stage")
    p_mark.add_argument("status")
    p_mark.add_argument("--note", default="")
    sub.add_parser("show", help="현재 상태·재개 포인터 출력")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(_self_test())
    if a.cmd == "init":
        st = init_state(a.workspace, category=a.category)
        print(f"run-state 초기화: {STATE_REL} · 단계 {len(st['stages'])} · 재개 {st['resume']}")
    elif a.cmd == "mark":
        st = mark(a.workspace, a.stage, a.status, note=a.note)
        print(f"[{a.stage}] → {a.status} · 재개 포인터: {st['resume'] or '(전건 완료)'}")
    elif a.cmd == "show":
        st = load(a.workspace)
        print(f"run-state (category={st['category']}, updated={st['updated']}):")
        for s in st["stages"]:
            mk = {"done": "✔", "in_progress": "▶", "failed": "✗", "pending": "·"}.get(s["status"], "?")
            print(f"  {mk} {s['name']:12s} {s['status']}" + (f"  — {s['note']}" if s["note"] else ""))
        print(f"재개 포인터: {st['resume'] or '(전건 완료)'}")
    else:
        ap.error("하위 명령이 필요합니다 (init/mark/show 또는 --self-test)")


if __name__ == "__main__":
    main()
