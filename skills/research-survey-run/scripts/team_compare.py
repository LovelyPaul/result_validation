#!/usr/bin/env python3
# [기능군: team] 멀티 LLM 팀 비교 실습 랩 — producer/reviewer 팀별 실행·결정론 채점
"""team_compare — 멀티 LLM '팀 구성'을 나란히 돌려 비교하는 실습 랩.

동기(references/TEAM_COMPARE.md): 본 플러그인 개발 중 **교차 벤더 리뷰**(한 벤더가 만든
요약을 다른 벤더가 검수)가 **단일 벤더로는 놓친 major 결함을 잡은** 실증이 있었다. 이 랩은
그 구성을 설치 직후 워크스페이스에서 바로 따라 해 보게 한다: 같은 논문을 팀별로
(producer가 요약 → reviewer가 검수)한 뒤, **판정·집계는 LLM이 아니라 결정론 채점기**
(verify_summaries의 source-coverage)로만 한다 — LLM 출력을 근거로 점수를 매기지 않는다
(garbage-in 차단·환각0).

팀 정의(00-system/teams.json — teams.sample.json 참고):
  { "teams": [ { "team_id": "A",
      "producer": {"cli":"codex","cmd_template":"exec --skip-git-repo-check -m {model}","model":"gpt-5.6-sol"},
      "reviewer": {"cli":"claude","cmd_template":"-p --model {model}","model":"claude-fable-5"} }, ... ] }
  - 팀별 분리 작업영역: 공유 = 60-data/corpus.json·gold·매설 / 분리 = 40-drafts/<team_id>/·산출.
  - producer = 헤드리스 요약(초록만 근거 지시), reviewer = producer 요약을 검수(오류 후보 JSON).

결정론 채점(집계):
  - producer 요약을 verify_summaries.check_evidence_grounding으로 원문(초록) 대조 →
    **인용 실재율**(= 1 - 부재건수/needle수)·coverage FAIL 목록.
  - `--seeded <manifest.json>` 지정 시: 매설 오류 문구가 producer 요약에 새어들어갔는지
    (오염 유입) + reviewer가 그 오염을 오류 후보로 지적했는지(검출) 결정론 대조 → **매설 검출률**.

비용 가드: 기본 **dry-run**(실 LLM 호출 0 — 호출 수·팀·논문 미리보기만). 실행하려면 `--yes`.
버그 회피(review-workspaces 실주행 + v0.6.0 R1 실측): ①Windows .ps1/.cmd npm shim은
shutil.which 해소 후 powershell 라우팅 ②★프롬프트는 **stdin**으로 전달한다 — argv로 넘기면
Windows npm .CMD 심이 개행 포함 인자를 **첫 개행에서 절단**해 producer가 첫 줄만 받고
비응답한다(R1 major 원인 입증·codex exec·claude -p 모두 stdin 수용) ③codex는
--skip-git-repo-check로 trusted-dir 거부 회피 ④reviewer 비수신·비응답은 flagged=[]를
'무결'로 오집계하지 않고 unchecked(검수 불능)로 구분(위장 무결 차단).

의존: python3 표준 라이브러리만. 자체 검사: `python3 team_compare.py --self-test`
(CLI 호출 0 — fake runner 주입으로 오케스트레이션·채점·invocation 빌드·dry-run 검증).
"""
import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_summaries import resolve_source, check_evidence_grounding  # noqa: E402 — 결정론 채점 공유

TEAMS_REL = "00-system/teams.json"
CORPUS_REL = "60-data/corpus.json"
DRAFTS_REL = "40-drafts"
REPORTS_REL = "80-reports"
LOW_EVIDENCE_MIN = 3   # 검증 가능 needle(수치·직접인용) 수 임계 — 미만이면 low-evidence 플래그(R2 [3])

# team_id·paper id 경로 위생(R2 [2]): 영숫자로 시작 + 영숫자·._- 만. arXiv id의 점(2303.08896)은
# 허용하되 '..'(상위참조)·경로 구분자·절대경로는 첫 글자 규칙+아래 명시 검사로 거부.
_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def _safe_id(value, kind):
    """식별자 경로 위생 검증 — 위반은 SystemExit(fail-closed). '.'·'..'·구분자·절대경로 거부."""
    v = str(value)
    if not _SAFE_ID.fullmatch(v) or ".." in v or "/" in v or "\\" in v:
        raise SystemExit(
            f"{kind} 식별자 경로 위생 위반: {value!r} — 영숫자로 시작하고 영숫자·. _ - 만 "
            f"허용된다(경로 구분자·'..'·절대경로 금지). 팀/논문 id를 안전한 값으로 바꿔라.")
    return v


def _ensure_within(path, root, label):
    """resolve한 대상이 허용 root 하위인지 fail-closed 확인(R2 [2] — 작업영역 이탈 차단)."""
    rp = Path(path).resolve()
    rr = Path(root).resolve()
    if not rp.is_relative_to(rr):
        raise SystemExit(f"{label} 작업영역 이탈: {rp} 는 {rr} 하위가 아니다 — 쓰기 거부.")
    return rp

PRODUCER_PROMPT = (
    "다음 논문 초록만 근거로 요약하라. 초록에 없는 수치·주장은 절대 지어내지 마라.\n"
    "형식(반드시 이 섹션명): ## Summary / ## Why / ## Evidence\n"
    "## Evidence 절에는 초록에 실재하는 수치·인용 문구만 페이지 없이라도 적어라.\n"
    "맨 끝 줄: source_pdf: {aid}.pdf — arXiv:{aid}\n\n제목: {title}\n초록: {abstract}\n")
REVIEWER_PROMPT = (
    "아래는 어떤 논문 요약이다. 원문 초록과 대조해 **오류 후보**(발명 수치·오인용·과장)를 찾아라.\n"
    "출력은 JSON 한 줄: {{\"flagged\": [\"의심 문구1\", ...]}} — 근거 없으면 flagged: [].\n\n"
    "원문 초록: {abstract}\n\n요약:\n{summary}\n")


def _wrap_shim(exe, args):
    """Windows 심 라우팅(순수 함수·테스트 가능). 직접 spawn 시 ENOENT/확장자 오류가 나는
    npm 심을 올바른 인터프리터로 감싼다: `.ps1`→powershell -File(.ps1 전용), `.cmd`/`.bat`→
    cmd /c(powershell -File은 .ps1만 받으므로 .CMD를 거기 넣으면 실패 — R1 재실행에서 실측).
    그 외(.exe 등)는 그대로."""
    low = exe.lower()
    if low.endswith(".ps1"):
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", exe, *args]
    if low.endswith((".cmd", ".bat")):
        return ["cmd", "/c", exe, *args]
    return [exe, *args]


def _resolve_invocation(cli, cmd_template, model):
    """CLI 호출 argv 빌드 (프롬프트 제외 — 프롬프트는 stdin으로 전달). 반환: argv 리스트.
    ★프롬프트를 argv에 넣지 않는다(R1): Windows npm .CMD/.ps1 심이 개행 포함 인자를 첫
    개행에서 절단하기 때문. 심 종류별 인터프리터 라우팅은 _wrap_shim."""
    exe = shutil.which(cli)
    if not exe:
        raise SystemExit(f"CLI 미설치: {cli!r} — teams.json에서 가용 CLI만 쓰거나 설치하라.")
    return _wrap_shim(exe, shlex.split(cmd_template.format(model=model)))


def _default_runner(argv, cwd, prompt, timeout=300):
    """실 CLI 실행 — ★프롬프트를 stdin으로 전달(R1: argv 개행 절단 회피)·텍스트 캡처.
    실패는 명시 진단. codex exec·claude -p 모두 stdin에서 프롬프트를 읽는다."""
    try:
        p = subprocess.run(argv, cwd=cwd, input=prompt,
                           capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        raise SystemExit(f"실행 실패(경로/shim): {argv[0]} — {e}")
    except subprocess.TimeoutExpired:
        raise SystemExit(f"CLI 응답 타임아웃({timeout}s): {argv[0]}")
    if p.returncode != 0:
        raise SystemExit(f"CLI 비정상 종료(exit {p.returncode}): {argv[0]}\n{p.stderr[:300]}")
    return p.stdout


def grade_summary(summary_text, paper):
    """결정론 채점 — producer 요약을 초록 대조. verify_summaries 재사용(이중 구현 금지).
    ★지표 범위 한정(R2 [3]): citation_existence_rate는 **Evidence의 수치·직접인용(12자+ 따옴표)
    substring 실재율만** 측정한다 — qualitative 주장·의미 오용은 검사 범위 밖(reviewer 검수와
    병행 해석해야 함). needle(검증 가능 성분) 수가 LOW_EVIDENCE_MIN 미만이면 low_evidence=True
    로 표시해 '실재 인용 1개 + 허위 Summary' 조합이 100%로 과신되는 것을 드러낸다.
    반환: {needles, absent, citation_existence_rate, low_evidence, fails}."""
    corpus_by_id = {str(paper["id"]): paper}
    src_text, _abstract, why = resolve_source(summary_text, corpus_by_id, None)
    if src_text is None:
        # arXiv id를 요약이 안 달았어도 대상 논문 초록으로 직접 대조(fail-closed 회피 — 대상 확정 상황)
        src_text = (paper.get("title") or "") + " " + (paper.get("abstract") or "")
    from verify_summaries import extract_claim_numbers, extract_claim_quotes, EVIDENCE_SEC
    # provenance 메타(source_pdf: <파일>) 라인은 claim이 아니므로 채점서 제외 — 파일명의
    # 숫자가 수치 주장으로 오인식되는 것을 막는다(예: source_pdf: 1.pdf 의 '1').
    cleaned = re.sub(r"(?m)^\s*source_pdf:.*$", "", summary_text)
    # producer 요약은 이미 ## Evidence 섹션을 가지므로 그대로 대조 — 있으면 그 절만, 없으면 전체를
    # Evidence로 감싸 검사(중복 헤더 삽입 금지 — EVIDENCE_SEC가 엉뚱한 절을 잡지 않게).
    graded = cleaned if EVIDENCE_SEC.search(cleaned) else "## Evidence\n" + cleaned
    fails = check_evidence_grounding(graded, src_text)
    m = EVIDENCE_SEC.search(graded)
    ev = m.group(1) if m else graded
    total = len(extract_claim_numbers(ev)) + len(extract_claim_quotes(ev))
    absent = len(fails)
    rate = round(1 - absent / total, 4) if total else None
    return {"needles": total, "absent": absent,
            "citation_existence_rate": rate,
            "low_evidence": total < LOW_EVIDENCE_MIN,
            "fails": [str(f) for f in fails]}


def _parse_review(reviewer_out):
    """reviewer 출력 결정론 파싱 → (flagged 리스트, checked). **스키마 엄격**(R2 [1]):
    - checked=True  : root가 object이고 flagged가 **list이며 모든 원소가 비어있지 않은 string**
      일 때만(빈 리스트=검수함·0건). `{"flagged":[]}` 대조군은 checked=True.
    - checked=False : JSON 부재·비object·flagged 키 부재·flagged가 null/string/number/object·
      비string 원소·빈 문자열 포함 = **검수 불능(unchecked)**. schema-invalid JSON도 unchecked로
      막는다(null→[]·string→문자별 리스트로 위장 통과하던 우회 봉쇄·위장 무결 차단).
    - **배열 envelope 정합(v0.7.0 minor)**: 일부 CLI는 출력을 단일 object를 감싼 1원소 배열
      `[{"flagged":[...]}]`로 낸다 — 이 경우만 언랩해 같은 엄격 규칙을 적용한다. 2원소 이상
      배열·비object 원소는 여전히 unchecked(엄격성 유지).
    """
    m = re.search(r"[\[{].*[\]}]", reviewer_out or "", re.S)   # object 또는 배열 envelope
    if not m:
        return [], False
    try:
        obj = json.loads(m.group(0))
    except (json.JSONDecodeError, ValueError):
        return [], False
    if isinstance(obj, list):   # 1원소 배열 envelope만 언랩 (그 외 배열은 unchecked)
        if len(obj) == 1 and isinstance(obj[0], dict):
            obj = obj[0]
        else:
            return [], False
    if not isinstance(obj, dict) or "flagged" not in obj:
        return [], False
    flagged = obj["flagged"]
    if not isinstance(flagged, list):
        return [], False   # null·string·number·object 모두 거부
    if not all(isinstance(x, str) and x.strip() for x in flagged):
        return [], False   # 비string 원소·빈 문자열 → 스키마 무효
    return list(flagged), True


def run_team(team, paper, workspace, runner, seeded=None):
    """한 팀: producer 요약 → reviewer 검수 → 결정론 채점. 작업영역 분리.
    ★쓰기 전 team_id·paper id 경로 위생 검증 + 작업영역 봉쇄 확인(R2 [2] — RUNBOOK 산출물
    위치 안전핀·팀별 격리 유지)."""
    ws = Path(workspace)
    tid = _safe_id(team["team_id"], "team_id")
    aid = _safe_id(paper["id"], "paper id")
    drafts_root = ws / DRAFTS_REL
    tdir = _ensure_within(drafts_root / tid, drafts_root, "팀 작업영역")
    tdir.mkdir(parents=True, exist_ok=True)

    pr = team["producer"]
    p_argv = _resolve_invocation(pr["cli"], pr["cmd_template"], pr.get("model", ""))
    p_prompt = PRODUCER_PROMPT.format(aid=aid, title=paper.get("title", ""),
                                      abstract=paper.get("abstract", ""))
    summary = runner(p_argv, str(tdir), p_prompt)     # 프롬프트 stdin 전달(R1)
    (tdir / f"{aid}.md").write_text(summary, encoding="utf-8")

    rv = team["reviewer"]
    r_argv = _resolve_invocation(rv["cli"], rv["cmd_template"], rv.get("model", ""))
    r_prompt = REVIEWER_PROMPT.format(abstract=paper.get("abstract", ""), summary=summary)
    review_out = runner(r_argv, str(tdir), r_prompt)
    flagged, reviewer_checked = _parse_review(review_out)
    (tdir / f"{aid}.review.json").write_text(
        json.dumps({"flagged": flagged, "checked": reviewer_checked, "raw": review_out},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    score = grade_summary(summary, paper)
    # agy#11: 팀별 단계 상태 기록 — 중단 시 어느 단계까지 됐는지 남긴다(하네스 견고성).
    stages = {"produce": "done", "review": "checked" if reviewer_checked else "unchecked",
              "grade": "done"}
    entry = {"team_id": team["team_id"], "paper": aid,
             "producer": f"{pr['cli']}:{pr.get('model', '')}",
             "reviewer": f"{rv['cli']}:{rv.get('model', '')}",
             "score": score, "reviewer_flagged": flagged,
             "reviewer_checked": reviewer_checked, "stages": stages}
    if seeded is not None:
        leaked = [s for s in seeded if s in summary]       # 매설 문구가 요약에 유입됐나
        caught = [s for s in leaked if any(s in f for f in flagged)]  # reviewer가 그 유입을 지적했나
        entry["seeded"] = {"leaked": leaked, "caught": caught,
                           "catch_rate": round(len(caught) / len(leaked), 4) if leaked else None}
    return entry


def preview(teams, papers):
    """비용 가드 — 실 LLM 호출 수 미리보기(dry-run)."""
    calls = len(teams) * len(papers) * 2   # 팀×논문×(producer+reviewer)
    lines = [f"[dry-run] 팀 {len(teams)} · 논문 {len(papers)} · 예상 실 LLM 호출 {calls}회"]
    for t in teams:
        lines.append(f"  · 팀 {t['team_id']}: producer={t['producer']['cli']}:"
                     f"{t['producer'].get('model','')} / reviewer={t['reviewer']['cli']}:"
                     f"{t['reviewer'].get('model','')}")
    lines.append("실행하려면 --yes 를 붙여라(실 LLM 호출·비용 발생).")
    return "\n".join(lines), calls


def load_papers(corpus_path, ids=None, limit=1):
    corpus = json.loads(Path(corpus_path).read_text(encoding="utf-8"))
    by_id = {str(e["id"]): e for e in corpus if isinstance(e, dict) and e.get("id")}
    if ids:
        picked = [by_id[i] for i in ids if i in by_id]
        missing = [i for i in ids if i not in by_id]
        if missing:
            raise SystemExit(f"코퍼스에 없는 논문 id: {missing}")
        return picked
    return corpus[:limit]


def run(workspace, teams_path, corpus_path, ids=None, limit=1, yes=False,
        seeded_path=None, runner=None):
    teams = (json.loads(Path(teams_path).read_text(encoding="utf-8")).get("teams") or [])
    if not teams:
        raise SystemExit(f"teams 정의 0건: {teams_path}")
    # team_id 사전 위생 검증 + 중복 거부(R2 [2] — 팀별 격리·경로 안전이 실행 전에 확정돼야)
    seen_tids = set()
    for t in teams:
        tid = _safe_id(t.get("team_id", ""), "team_id")
        if tid in seen_tids:
            raise SystemExit(f"중복 team_id: {tid!r} — 팀별 작업영역이 겹친다(고유해야 한다).")
        seen_tids.add(tid)
    papers = load_papers(corpus_path, ids, limit)
    if not papers:
        raise SystemExit("대상 논문 0편 — --ids 또는 코퍼스를 확인하라.")
    pv, calls = preview(teams, papers)
    if not yes:
        print(pv)
        return None, None
    seeded = None
    if seeded_path:
        sd = json.loads(Path(seeded_path).read_text(encoding="utf-8"))
        seeded = sd.get("phrases") or sd if isinstance(sd, list) else sd.get("phrases", [])
    runner = runner or _default_runner
    results = []
    for paper in papers:
        for team in teams:
            results.append(run_team(team, paper, workspace, runner, seeded=seeded))

    report = {"teams": len(teams), "papers": [str(p["id"]) for p in papers],
              "calls": calls, "results": results}
    out_dir = Path(workspace) / REPORTS_REL
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "team-compare-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md = _render_md(report)
    (out_dir / "team-compare-report.md").write_text(md, encoding="utf-8")
    return report, out_dir


def _render_md(report):
    lines = ["# team-compare 결과 (결정론 채점)", "",
             f"팀 {report['teams']} · 논문 {report['papers']} · 실 LLM 호출 {report['calls']}회", "",
             "| 팀 | 논문 | producer | reviewer | Evidence 실재율(수치·직접인용) | coverage FAIL | reviewer 지적 | 매설 검출률 |",
             "|---|---|---|---|---|---|---|---|"]
    for r in report["results"]:
        s = r["score"]
        seeded = r.get("seeded") or {}
        # rate None = 집계 불가 (producer 요약에 Evidence needle 0 — 비응답·형식 미준수 등)
        if s["citation_existence_rate"] is None:
            cr = "집계 불가(needle 0)"
        else:
            cr = f"{s['citation_existence_rate']*100:.0f}% (needle {s['needles']})"
            if s.get("low_evidence"):   # needle < 임계 — 100%라도 과신 금지(R2 [3])
                cr += f" ⚠low-evidence(<{LOW_EVIDENCE_MIN})"
        # reviewer 비수신·비응답이면 '0건'이 아니라 unchecked (위장 무결 차단)
        rv = f"{len(r['reviewer_flagged'])}건" if r.get("reviewer_checked") else "unchecked(검수 불능)"
        sd = "" if not seeded or seeded.get("catch_rate") is None else f"{seeded['catch_rate']*100:.0f}% ({len(seeded['caught'])}/{len(seeded['leaked'])})"
        lines.append(f"| {r['team_id']} | {r['paper']} | {r['producer']} | {r['reviewer']} | "
                     f"{cr} | {s['absent']}건 | {rv} | {sd} |")
    lines += ["", "## 해석 (지표 범위 — 정직하게 읽기)",
              "- **Evidence 실재율(수치·직접인용)**: producer 요약 **Evidence 절의 수치·12자+ 직접인용**이 "
              "원문 초록에 substring으로 실재하는 비율. **이것만** 본다 — Summary/Why의 **qualitative "
              "주장·의미 오용은 검사 범위 밖**이다. '실재 인용 1개 + 원문에 없는 허위 Summary' 조합도 "
              "이 지표만으론 100%가 될 수 있으므로, **needle 수가 적으면(⚠low-evidence) 100%를 근거 충실로 "
              "과신하지 말고 reviewer 검수·본문 정독과 병행 해석**하라. '집계 불가'=needle 0(producer 형식·근거 실패).",
              "- **coverage FAIL**: Evidence의 수치·직접인용 중 원문 부재 건수(발명·오인용 — 낮을수록 좋음). "
              "이 역시 qualitative 허위는 못 잡는다.",
              "- **reviewer 지적**: 교차 벤더 reviewer가 오류 후보로 든 건수. **unchecked**=reviewer 비수신·비응답·"
              "스키마 무효 JSON(지적 0건과 구분 — 비응답을 '무결'로 위장 집계하지 않는다). qualitative 오류는 "
              "결정론 채점이 못 보므로 이 reviewer 후보가 보완 신호다.",
              "- **매설 검출률**(--seeded): 매설 오류가 요약에 유입됐을 때 reviewer가 잡은 비율.",
              "- 판정·집계는 전부 결정론 채점기(verify_summaries) — LLM 출력을 점수 근거로 쓰지 않는다."]
    return "\n".join(lines) + "\n"


def _self_test():
    import tempfile
    failures = []
    ABS = ("The system achieves 94.2% accuracy on the benchmark. It uses seven datasets "
           "and a novel retrieval mechanism.")

    # 단위: invocation 빌드 — 프롬프트는 argv에 없음(stdin 전달·R1), codex 인자 포함
    try:
        argv = _resolve_invocation("python", "exec --skip-git-repo-check -m {model}", "m1")
        if "--skip-git-repo-check" not in argv or "m1" not in argv:
            failures.append(f"codex 템플릿 인자 누락: {argv}")
        if any("\n" in a for a in argv):
            failures.append(f"argv에 개행 포함(절단 위험): {argv}")
    except SystemExit as e:
        failures.append(f"invocation 빌드 실패(python which): {e}")
    # 미설치 CLI → 명시 SystemExit
    try:
        _resolve_invocation("no-such-cli-xyz", "-p", "m")
        failures.append("미설치 CLI를 통과시킴")
    except SystemExit as e:
        if "미설치" not in str(e):
            failures.append(f"미설치 진단 이상: {e}")
    # 단위: 심 라우팅 — .ps1→powershell -File / .cmd·.bat→cmd /c / .exe→그대로 (R1 재실행 실패 원인)
    if _wrap_shim(r"C:\x\codex.CMD", ["exec", "-m", "g"]) != ["cmd", "/c", r"C:\x\codex.CMD", "exec", "-m", "g"]:
        failures.append(".cmd 심을 cmd /c로 라우팅 안 함")
    if _wrap_shim(r"C:\x\gemini.ps1", ["-p"])[:5] != ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]:
        failures.append(".ps1 심을 powershell -File로 라우팅 안 함")
    if _wrap_shim(r"C:\x\claude.exe", ["-p"]) != [r"C:\x\claude.exe", "-p"]:
        failures.append(".exe는 그대로여야")

    # 단위: _parse_review — 유효 JSON=checked / 비JSON·flagged 키 부재=unchecked (R1 1b)
    if _parse_review('{"flagged": ["88.8", "999"]}') != (["88.8", "999"], True):
        failures.append("flagged 유효 JSON 파싱 오류")
    if _parse_review('{"flagged": []}') != ([], True):
        failures.append("flagged 빈 리스트는 checked=True여야(정상 검수)")
    if _parse_review("죄송합니다 요약이 첨부되지 않았습니다") != ([], False):
        failures.append("비JSON 비응답은 unchecked(checked=False)여야")
    if _parse_review('{"note": "no flagged key"}') != ([], False):
        failures.append("flagged 키 부재는 unchecked여야")
    # R2 [1]: schema-invalid JSON은 unchecked — null·string·number·비string원소·빈문자열 전부 거부
    for bad_json, label in (('{"flagged": null}', "null"),
                            ('{"flagged": "ABC"}', "string"),
                            ('{"flagged": 5}', "number"),
                            ('{"flagged": {"a": 1}}', "object"),
                            ('{"flagged": ["ok", 7]}', "혼합(비string 원소)"),
                            ('{"flagged": ["ok", "  "]}', "빈 문자열 원소"),
                            ('["not", "object"]', "root 비object")):
        if _parse_review(bad_json) != ([], False):
            failures.append(f"R2 스키마 무효({label})를 unchecked로 안 막음: {_parse_review(bad_json)}")
    # 유효 대조군은 여전히 checked=True (회귀 방지)
    if _parse_review('{"flagged": ["진짜 지적"]}') != (["진짜 지적"], True):
        failures.append("유효 flagged 대조군 회귀")
    # v0.7.0 minor: 1원소 배열 envelope는 언랩·검수 인정 / 2원소 배열은 unchecked(엄격 유지)
    if _parse_review('[{"flagged": ["지적"]}]') != (["지적"], True):
        failures.append("1원소 배열 envelope 언랩 실패")
    if _parse_review('[{"flagged": []}]') != ([], True):
        failures.append("1원소 배열 envelope 빈 리스트 처리 오류")
    if _parse_review('[{"flagged": []}, {"flagged": ["x"]}]') != ([], False):
        failures.append("2원소 배열은 unchecked여야(엄격 유지)")

    # 단위: 채점 — 충실 요약(94.2·seven 실재)=FAIL 0 / 발명 요약(88.8·999)=FAIL
    good = "## Summary\nx\n## Why\ny\n## Evidence\n- 94.2% accuracy · seven datasets\nsource_pdf: 1.pdf — arXiv:1234.56789\n"
    bad = "## Summary\nx\n## Why\ny\n## Evidence\n- 88.8% accuracy · 999 datasets\nsource_pdf: 1.pdf\n"
    paper = {"id": "1234.56789", "title": "T", "abstract": ABS}
    gs = grade_summary(good, paper)
    bs = grade_summary(bad, paper)
    if gs["absent"] != 0 or gs["citation_existence_rate"] != 1.0:
        failures.append(f"충실 요약 채점 오류: {gs}")
    if gs.get("low_evidence"):   # needle 2(<3)면 low_evidence여야 — good은 needle 2
        pass   # good은 needle 2라 low_evidence=True가 정상(아래 별도 단언에서 확인)
    if bs["absent"] < 1 or "88.8" not in " ".join(bs["fails"]):
        failures.append(f"발명 요약 채점 오류: {bs}")

    # R2 [3]: qualitative 우회 반례 — 실재 인용 1개 + 원문에 없는 허위 Summary → rate 1.0·FAIL 0
    # 이지만 needle 1(<3)이라 low_evidence=True로 '전체 통과' 과신을 차단해야 한다.
    fabricated = ("## Summary\n환자 개인정보를 외부로 전송하며 보편적 안전을 보장한다(원문에 없는 허위).\n"
                  "## Why\nx\n## Evidence\n- \"a novel retrieval mechanism\"\n"
                  "source_pdf: 1234.56789.pdf — arXiv:1234.56789\n")
    fg = grade_summary(fabricated, paper)
    if fg["citation_existence_rate"] != 1.0 or fg["absent"] != 0:
        failures.append(f"qualitative 반례 채점 전제 오류: {fg}")
    if not fg["low_evidence"] or fg["needles"] >= LOW_EVIDENCE_MIN:
        failures.append(f"qualitative 반례가 low-evidence로 안 잡힘(100% 과신 위험): {fg}")
    # 리포트 렌더에 low-evidence 경고가 실제로 표기되는지(전체 통과로 표현 안 됨)
    fake_rep = {"teams": 1, "papers": ["1234.56789"], "calls": 2, "results": [
        {"team_id": "A", "paper": "1234.56789", "producer": "x:m", "reviewer": "y:m",
         "score": fg, "reviewer_flagged": [], "reviewer_checked": True}]}
    if "low-evidence" not in _render_md(fake_rep):
        failures.append("리포트에 low-evidence 경고 미표기(qualitative 과신 방지 실패)")

    # R2 [2]: 식별자 경로 위생 — arXiv id(점 포함)는 허용, 이탈 시도는 거부
    if _safe_id("2303.08896", "paper id") != "2303.08896":
        failures.append("정상 arXiv id(점 포함)를 거부함")
    for bad_id in ("../../outside-team", "../../../outside-paper", "/abs", "a/b", "a\\b", "..", "."):
        try:
            _safe_id(bad_id, "test")
            failures.append(f"경로 위생 위반 미거부: {bad_id!r}")
        except SystemExit:
            pass

    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        (ws / "00-system").mkdir(parents=True); (ws / "60-data").mkdir(parents=True)
        teams = {"teams": [
            {"team_id": "A", "producer": {"cli": "python", "cmd_template": "-c {model}", "model": "pass"},
             "reviewer": {"cli": "python", "cmd_template": "-c {model}", "model": "pass"}},
            {"team_id": "B", "producer": {"cli": "python", "cmd_template": "-c {model}", "model": "pass"},
             "reviewer": {"cli": "python", "cmd_template": "-c {model}", "model": "pass"}}]}
        (ws / TEAMS_REL).write_text(json.dumps(teams), encoding="utf-8")
        (ws / CORPUS_REL).write_text(json.dumps([paper]), encoding="utf-8")

        # dry-run: 실행 0·호출 수 미리보기 (--yes 없이)
        rep, _ = run(str(ws), ws / TEAMS_REL, ws / CORPUS_REL, yes=False)
        if rep is not None:
            failures.append("dry-run인데 결과 생성됨")
        if list((ws / DRAFTS_REL).glob("*")) if (ws / DRAFTS_REL).exists() else []:
            failures.append("dry-run이 작업영역을 만듦")

        # --yes: fake runner 주입 (CLI 호출 0) — 프롬프트 stdin 전달·분리 작업영역·집계 검증
        calls = {"n": 0, "prompts": []}
        def fake_runner(argv, cwd, prompt, timeout=300):
            calls["n"] += 1
            calls["prompts"].append(prompt)
            # ★프롬프트는 stdin으로 온다 — 개행 포함 전문이 절단 없이 도착해야(R1 원인 회귀 방지)
            if "오류 후보" in prompt:   # reviewer
                return '{"flagged": ["발명"]}'
            return good   # producer 요약(충실)
        rep, out_dir = run(str(ws), ws / TEAMS_REL, ws / CORPUS_REL, yes=True, runner=fake_runner)
        if calls["n"] != 4:   # 2팀 × 1논문 × 2(producer+reviewer)
            failures.append(f"호출 수 오류: {calls['n']} (기대 4)")
        # R1: producer 프롬프트가 개행 다중 줄 전문으로 도착(첫 줄만 절단되지 않음)
        prod_prompts = [p for p in calls["prompts"] if "오류 후보" not in p]
        if not prod_prompts or not all("\n" in p and "초록:" in p and "## Evidence" in p for p in prod_prompts):
            failures.append(f"producer 프롬프트 개행 전문 미도달(절단 회귀): {prod_prompts[:1]}")
        if not rep or len(rep["results"]) != 2:
            failures.append(f"결과 집계 오류: {rep and len(rep['results'])}")
        if not (out_dir / "team-compare-report.md").exists():
            failures.append("리포트 md 미생성")
        for r in rep["results"]:
            if not r.get("reviewer_checked"):
                failures.append(f"정상 reviewer가 unchecked로 오집계: {r['team_id']}")
            # agy#11: 팀별 단계 상태 기록
            if r.get("stages") != {"produce": "done", "review": "checked", "grade": "done"}:
                failures.append(f"팀별 단계 상태 기록 오류: {r.get('stages')}")
        # 팀별 분리 작업영역
        for tid in ("A", "B"):
            if not (ws / DRAFTS_REL / tid / "1234.56789.md").exists():
                failures.append(f"팀 {tid} 분리 작업영역 미생성")

        # R2 [2]: 경로 이탈 team_id → 쓰기 전 SystemExit·workspace 밖 파일 미생성
        esc_teams = {"teams": [{"team_id": "../../outside-team",
                                "producer": {"cli": "python", "cmd_template": "-c {model}", "model": "p"},
                                "reviewer": {"cli": "python", "cmd_template": "-c {model}", "model": "p"}}]}
        (ws / TEAMS_REL).write_text(json.dumps(esc_teams), encoding="utf-8")
        def bomb_runner(argv, cwd, prompt, timeout=300):
            failures.append("경로 이탈 team_id인데 runner가 호출됨(쓰기 발생 위험)")
            return good
        try:
            run(str(ws), ws / TEAMS_REL, ws / CORPUS_REL, yes=True, runner=bomb_runner)
            failures.append("경로 이탈 team_id를 거부하지 않음")
        except SystemExit as e:
            if "위생 위반" not in str(e):
                failures.append(f"경로 이탈 진단 메시지 이상: {e}")
        if (Path(d).parent / "outside-team").exists():
            failures.append("경로 이탈 team_id가 workspace 밖에 파일을 씀")
        # R2 [2]: 경로 이탈 paper id → run_team 진입 시 SystemExit
        try:
            run_team({"team_id": "A", "producer": {"cli": "python", "cmd_template": "-c {model}"},
                      "reviewer": {"cli": "python", "cmd_template": "-c {model}"}},
                     {"id": "../../../outside-paper", "title": "t", "abstract": ABS},
                     str(ws), bomb_runner)
            failures.append("경로 이탈 paper id를 거부하지 않음")
        except SystemExit as e:
            if "위생 위반" not in str(e):
                failures.append(f"paper id 이탈 진단 이상: {e}")
        # R2 [2]: 중복 team_id → SystemExit
        dup_teams = {"teams": [
            {"team_id": "A", "producer": {"cli": "python", "cmd_template": "-c {model}", "model": "p"},
             "reviewer": {"cli": "python", "cmd_template": "-c {model}", "model": "p"}},
            {"team_id": "A", "producer": {"cli": "python", "cmd_template": "-c {model}", "model": "p"},
             "reviewer": {"cli": "python", "cmd_template": "-c {model}", "model": "p"}}]}
        (ws / TEAMS_REL).write_text(json.dumps(dup_teams), encoding="utf-8")
        try:
            run(str(ws), ws / TEAMS_REL, ws / CORPUS_REL, yes=True, runner=bomb_runner)
            failures.append("중복 team_id를 거부하지 않음")
        except SystemExit as e:
            if "중복 team_id" not in str(e):
                failures.append(f"중복 team_id 진단 이상: {e}")
        (ws / TEAMS_REL).write_text(json.dumps(teams), encoding="utf-8")   # 원복

        # R1 1b: reviewer 비응답(JSON 미반환) → unchecked 구분(위장 무결 차단)
        def mute_reviewer(argv, cwd, prompt, timeout=300):
            if "오류 후보" in prompt:
                return "죄송합니다. 요약이 첨부되지 않았습니다."   # 비응답(JSON 없음)
            return good
        rep_u, out_u = run(str(ws), ws / TEAMS_REL, ws / CORPUS_REL, yes=True, runner=mute_reviewer)
        if any(r.get("reviewer_checked") for r in rep_u["results"]):
            failures.append("reviewer 비응답을 checked로 오집계(위장 무결)")
        if "unchecked" not in (out_u / "team-compare-report.md").read_text(encoding="utf-8"):
            failures.append("리포트에 unchecked 표기 누락")

        # --seeded: 매설 문구가 요약에 유입·reviewer 검출 결정론 대조
        seeded_summary = "## Summary\nx\n## Why\ny\n## Evidence\n- 발명수치 없음\nsource_pdf: 1.pdf — arXiv:1234.56789\n"
        def seeded_runner(argv, cwd, prompt, timeout=300):
            if "오류 후보" in prompt:
                return '{"flagged": ["INVENTED-PHRASE-X 의심"]}'
            return seeded_summary + "\nINVENTED-PHRASE-X\n"
        (ws / "seeds.json").write_text(json.dumps({"phrases": ["INVENTED-PHRASE-X"]}), encoding="utf-8")
        rep2, _ = run(str(ws), ws / TEAMS_REL, ws / CORPUS_REL, yes=True,
                      seeded_path=ws / "seeds.json", runner=seeded_runner)
        sd = rep2["results"][0].get("seeded")
        if not sd or sd["catch_rate"] != 1.0 or sd["leaked"] != ["INVENTED-PHRASE-X"]:
            failures.append(f"--seeded 검출 집계 오류: {sd}")

    if failures:
        print("SELF-TEST FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print("SELF-TEST PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="멀티 LLM 팀 비교 실습 랩 (기본 dry-run · --yes로 실행)")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--teams", help=f"팀 정의 JSON (기본 <ws>/{TEAMS_REL})")
    ap.add_argument("--corpus", help=f"코퍼스 (기본 <ws>/{CORPUS_REL})")
    ap.add_argument("--ids", help="대상 arXiv id 콤마 목록 (미지정 시 코퍼스 앞 --limit편)")
    ap.add_argument("--limit", type=int, default=1, help="--ids 미지정 시 대상 편수 (기본 1)")
    ap.add_argument("--seeded", help="매설 문구 manifest JSON(phrases:[...]) — 검출률 채점")
    ap.add_argument("--yes", action="store_true", help="실 LLM 호출 실행(미지정 시 dry-run 미리보기)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(_self_test())
    ws = Path(a.workspace)
    rep, out_dir = run(ws, a.teams or ws / TEAMS_REL, a.corpus or ws / CORPUS_REL,
                       ids=[i.strip() for i in a.ids.split(",")] if a.ids else None,
                       limit=a.limit, yes=a.yes, seeded_path=a.seeded)
    if rep is None:
        return   # dry-run 미리보기 출력됨
    print(f"팀 비교 완료 — 리포트: {out_dir / 'team-compare-report.md'}")
    print(_render_md(rep))


if __name__ == "__main__":
    main()
