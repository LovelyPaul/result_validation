#!/usr/bin/env python3
# [기능군: wiki] 승격 게이트(dry-run→apply·lint) — wiki_grade가 import
"""wiki_promote — 검증 통과 산출물을 wiki 정본으로 승격하는 게이트.

입력: 워크스페이스의 40-drafts/ 요약 또는 80-reports/ 서베이 (.md).
정본: <workspace>/20-knowledge-base/wiki/notes/<id>.md.

LLM-wiki 운영 규칙(gbrain·knowledge-manager 증류 — LLM_WIKI_RULES_DISTILLED.md) 반영:
  - A2 페이지 2분할: 노트 = 상단 `## Compiled Truth`(항상 현재값 — 갱신 시 통째 REWRITE) +
    하단 `## Timeline`(append-only — 기존 항목 수정·삭제 절대 금지). lint가 두 섹션을 강제.
  - A3 frontmatter 필수키: id·title·created·tags. + B8 출처 필수(source 프론트매터 또는
    본문 페이지/표/arXiv/DOI/URL 인용).
  - B4 dedup: 저장 전 제목/ID 중복 체크 — 같은 id는 갱신(B5), 다른 id·같은 제목은 거부
    (갱신이면 기존 id로, 신규면 제목 구분).
  - B5 갱신 규칙: 기존 노트면 Compiled Truth 교체 + Timeline append.
  - E1 Timeline 불변: 기존 Timeline 항목의 수정·삭제가 감지되면 승격 거부(append만 허용).
  - E3/E5: 전 연산 zero-LLM 결정론(정규식·diff) — 도구 응답만이 사실.

"정본 직접 쓰기 금지"(phase_contracts §9)를 코드로 강제: 기본 dry-run(diff 미리보기),
--apply 는 승인 후에만. 승격 이력은 manifest(JSONL) append.

의존: python3 표준 라이브러리만 (pyyaml 금지). 자체 검사: `python3 wiki_promote.py --self-test`.
"""
import argparse
import difflib
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

WIKI_REL = "20-knowledge-base/wiki"
NOTES_REL = f"{WIKI_REL}/notes"
MANIFEST_REL = f"{WIKI_REL}/promotion-manifest.jsonl"
ALLOWED_SRC_DIRS = ("40-drafts", "80-reports")   # 승격 입력 허용 위치 (phase_contracts §9)

REQUIRED_KEYS = ("id", "title", "created", "tags")   # A3 필수 frontmatter 키
# B8 출처 인용 신호: source 프론트매터가 비어도 본문에 페이지/표/arXiv/DOI/URL 인용이 있으면 통과
_CITATION_RE = re.compile(r"(p\.?\s?\d+|Table\s+\d+|Figure\s+\d+|arXiv:\S+|doi:\S+|https?://)", re.I)

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.S)
_KV_RE = re.compile(r"([A-Za-z_][\w-]*):\s*(.*)$")
_CT_HEAD = re.compile(r"^##\s+Compiled Truth\s*$", re.M)
_TL_HEAD = re.compile(r"^##\s+Timeline\s*$", re.M)


def parse_frontmatter(text):
    """정규식 frontmatter 파서(pyyaml 미사용)."""
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        mm = _KV_RE.match(line.strip())
        if not mm:
            continue
        key, val = mm.group(1), mm.group(2).strip()
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            fm[key] = [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()] if inner else []
        else:
            fm[key] = val.strip().strip('"').strip("'")
    return fm, text[m.end():]


def split_sections(body):
    """A2 2분할 파싱 → (compiled_truth, timeline). 섹션 헤딩 부재 시 None."""
    ct_m = _CT_HEAD.search(body)
    tl_m = _TL_HEAD.search(body)
    if not ct_m or not tl_m or tl_m.start() < ct_m.start():
        return None, None
    compiled = body[ct_m.end():tl_m.start()].strip()
    timeline = body[tl_m.end():].strip()
    return compiled, timeline


def _tl_lines(timeline):
    """Timeline을 비교 가능한 비어있지 않은 줄 목록으로 정규화."""
    return [ln.rstrip() for ln in (timeline or "").splitlines() if ln.strip()]


def lint_note(text):
    """노트 스키마 lint → 위반 목록(빈 목록=통과). A3 필수키 + B8 출처 + A2 2분할."""
    fm, body = parse_frontmatter(text)
    problems = []
    for key in REQUIRED_KEYS:
        if not fm.get(key):
            problems.append(f"frontmatter 필수키 누락/빈값: {key} (A3)")
    has_source = bool(fm.get("source")) or bool(_CITATION_RE.search(body))
    if not has_source:
        problems.append("출처 인용 없음 — source 프론트매터 또는 본문 페이지/표/arXiv/DOI/URL 인용 필요 (B8)")
    ct, tl = split_sections(body)
    if ct is None:
        problems.append("페이지 2분할 위반 — '## Compiled Truth' 다음 '## Timeline' 섹션 필수 (A2)")
    return problems, fm


def _target_id(text, src_path):
    fm, _ = parse_frontmatter(text)
    return fm.get("id") or Path(src_path).stem


def _diff(old, new, path):
    return "".join(difflib.unified_diff(
        old.splitlines(keepends=True), new.splitlines(keepends=True),
        fromfile=f"a/{path}", tofile=f"b/{path}"))


def _find_title_dup(notes_dir, title, exclude_id):
    """B4 dedup — 다른 id로 같은 제목의 기존 노트가 있으면 그 id를 반환."""
    norm = (title or "").strip().lower()
    if not norm:
        return None
    for p in sorted(Path(notes_dir).glob("*.md")):
        if p.stem == exclude_id:
            continue
        fm, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
        if (fm.get("title") or "").strip().lower() == norm:
            return fm.get("id") or p.stem
    return None


def _merge_update(existing_text, incoming_text):
    """B5+E1 갱신 병합 → (merged_text, problem|None).
    Compiled Truth = incoming으로 REWRITE. Timeline은 append-only — **엄격 규칙**:
    incoming TL은 기존 TL 전체를 글자 그대로(prefix) 포함하고 그 뒤에 새 항목만 덧붙여야 한다.
    기존 항목의 변경뿐 아니라 **생략(=삭제)도 E1 위반**으로 거부한다 — "새 항목만 제출" 허용
    분기는 변조본(기존과 한 글자라도 다른 사본)을 신규 항목으로 오인하는 루프홀이라 금지
    (2026-07-20 E2E 실측: 변조 항목이 교집합 0으로 append 통과 — 이 규칙으로 봉쇄).
    """
    in_fm_raw = _FM_RE.match(incoming_text)
    fm_block = incoming_text[:in_fm_raw.end()] if in_fm_raw else ""
    _, in_body = parse_frontmatter(incoming_text)
    _, ex_body = parse_frontmatter(existing_text)
    in_ct, in_tl = split_sections(in_body)
    ex_ct, ex_tl = split_sections(ex_body)
    ex_lines, in_lines = _tl_lines(ex_tl), _tl_lines(in_tl)

    if ex_lines and in_lines[:len(ex_lines)] != ex_lines:
        return None, ("Timeline 수정 감지 — 기존 Timeline 항목은 수정·삭제·생략할 수 없다"
                      "(append-only). 정본의 기존 Timeline 전체를 그대로 포함하고 그 뒤에 "
                      "새 항목만 덧붙여 다시 제출하라 (E1)")
    merged_lines = in_lines

    merged = (fm_block + "## Compiled Truth\n\n" + (in_ct or "").strip()
              + "\n\n## Timeline\n\n" + "\n".join(merged_lines) + "\n")
    return merged, None


def promote(workspace, src_file, apply=False):
    """단일 산출물 승격. 반환: {id, action, problems, diff, dest, src, manifest_line?}."""
    ws = Path(workspace)
    src = Path(src_file)
    if not src.exists():
        raise SystemExit(f"입력 파일 없음: {src}")
    text = src.read_text(encoding="utf-8")
    problems, fm = lint_note(text)

    # 승격 입력 위치 게이트 (R1 major-1): src는 workspace 하위 + 첫 디렉터리가 40-drafts/80-reports.
    # 이 검증이 없으면 workspace 밖 임의 markdown이 lint만 맞추면 --apply로 정본에 들어간다
    # (reviewer-codex 2026-07-20 실재현) — "검증 통과 산출물만 승격" 계약을 코드로 강제.
    try:
        rel = src.resolve().relative_to(ws.resolve())
        first_dir = rel.parts[0] if len(rel.parts) > 1 else ""
    except ValueError:
        rel, first_dir = None, None
    if rel is None or first_dir not in ALLOWED_SRC_DIRS:
        problems.append(
            f"승격 입력 위치 위반 — src는 workspace의 {'/'.join(ALLOWED_SRC_DIRS)} 아래 파일만 허용"
            f"(검증 라운드를 거친 산출물만 승격, phase_contracts §9): {src}")
    nid = _target_id(text, src)
    notes_dir = ws / NOTES_REL
    dest = notes_dir / f"{nid}.md"

    # B4 dedup: 다른 id·같은 제목 → 거부(갱신이면 기존 id로, 신규면 제목 구분)
    if not problems and notes_dir.exists():
        dup = _find_title_dup(notes_dir, fm.get("title"), nid)
        if dup:
            problems.append(f"제목 중복 — 기존 노트 id={dup} 와 같은 제목. "
                            f"갱신이면 id를 {dup} 로 맞추고, 신규 개념이면 제목을 구분하라 (B4)")

    final_text = text
    if not problems and dest.exists():
        # B5: Compiled Truth REWRITE + Timeline append (E1 위반 시 거부)
        merged, e1 = _merge_update(dest.read_text(encoding="utf-8"), text)
        if e1:
            problems.append(e1)
        else:
            final_text = merged

    old = dest.read_text(encoding="utf-8") if dest.exists() else ""
    diff = _diff(old, final_text, f"{NOTES_REL}/{nid}.md")
    action = ("update" if dest.exists() else "create") if not problems else "rejected"
    result = {"id": nid, "action": action, "problems": problems,
              "diff": diff, "dest": str(dest), "src": str(src)}

    if problems:
        return result  # lint/dedup/E1 실패 → 승격 거부 (apply 여부 무관)
    if not apply:
        result["action"] = f"dry-run:{action}"
        return result

    # --apply: 정본 쓰기 + manifest append (E2 감사선)
    notes_dir.mkdir(parents=True, exist_ok=True)
    dest.write_text(final_text, encoding="utf-8")
    line = {
        "ts": str(date.today()),
        "id": nid,
        "action": action,
        "src": str(src),
        "dest": str(dest),
        "sha256": hashlib.sha256(final_text.encode("utf-8")).hexdigest(),
    }
    manifest = ws / MANIFEST_REL
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    result["manifest_line"] = line
    return result


def _note(nid, title, ct, tl, source="arXiv:1, p.2"):
    return (f"---\nid: {nid}\ntitle: {title}\ncreated: 2026-07-20\ntags: [t1, t2]\n"
            f"source: {source}\n---\n## Compiled Truth\n\n{ct}\n\n## Timeline\n\n{tl}\n")


def _self_test():
    import tempfile
    failures = []

    # lint: A3 필수키·B8 출처·A2 2분할
    if not lint_note("---\nid: x\ntitle: T\n---\n본문.\n")[0]:
        failures.append("lint: created/tags/출처/2분할 없는 노트를 통과시킴")
    if lint_note(_note("x", "T", "내용 (p.3)", "- 2026-07-20 작성"))[0]:
        failures.append(f"lint: 정상 노트를 거부: {lint_note(_note('x','T','내용 (p.3)','- v'))[0]}")

    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        drafts = ws / "40-drafts"
        drafts.mkdir(parents=True)

        # dry-run: 정본 미생성
        src = drafts / "n1.md"
        src.write_text(_note("n1", "Note One", "F1 39.11 (Table 1, p.6)", "- 2026-07-20 초기 승격"),
                       encoding="utf-8")
        promote(str(ws), str(src), apply=False)
        if (ws / NOTES_REL / "n1.md").exists():
            failures.append("dry-run인데 정본 생성 (직접 쓰기 금지 위반)")

        # apply: create + manifest
        r = promote(str(ws), str(src), apply=True)
        if r["action"] != "create" or not (ws / NOTES_REL / "n1.md").exists():
            failures.append(f"apply create 실패: {r['action']}")
        if not (ws / MANIFEST_REL).exists():
            failures.append("manifest JSONL 미기록")

        # B5 갱신: CT REWRITE + TL append(기존 TL 전체 + 새 항목 형태 — 엄격 규칙)
        src2 = drafts / "n1-update.md"
        src2.write_text(_note("n1", "Note One", "F1 42.0 (Table 2, p.7) — 개정",
                              "- 2026-07-20 초기 승격\n- 2026-07-21 재검증 갱신"),
                        encoding="utf-8")
        r2 = promote(str(ws), str(src2), apply=True)
        merged = (ws / NOTES_REL / "n1.md").read_text(encoding="utf-8")
        if r2["action"] != "update" or "F1 42.0" not in merged or "F1 39.11" in merged.split("## Timeline")[0]:
            failures.append(f"B5 CT REWRITE 실패: {r2['action']}")
        if "- 2026-07-20 초기 승격" not in merged or "- 2026-07-21 재검증 갱신" not in merged:
            failures.append("B5 TL append 실패 (기존/신규 항목 누락)")

        # E1-a: 기존 Timeline 항목 변조 → 거부
        src3 = drafts / "n1-tamper.md"
        src3.write_text(_note("n1", "Note One", "무엇이든 (p.1)",
                              "- 2026-07-20 초기 승격(변조됨)\n- 2026-07-21 재검증 갱신"),
                        encoding="utf-8")
        r3 = promote(str(ws), str(src3), apply=True)
        if r3["action"] != "rejected" or not any("E1" in p for p in r3["problems"]):
            failures.append(f"E1 변조 미탐지: {r3['action']} {r3['problems']}")

        # E1-b: 기존 Timeline 생략(새 항목만 제출) → 거부 (2026-07-20 E2E 루프홀 회귀 방지)
        src3b = drafts / "n1-omit.md"
        src3b.write_text(_note("n1", "Note One", "무엇이든 (p.1)", "- 2026-07-22 새 항목만 제출"),
                         encoding="utf-8")
        r3b = promote(str(ws), str(src3b), apply=True)
        if r3b["action"] != "rejected" or not any("E1" in p for p in r3b["problems"]):
            failures.append(f"E1 생략 미탐지: {r3b['action']} {r3b['problems']}")

        # B4: 다른 id·같은 제목 → 거부
        src4 = drafts / "n2.md"
        src4.write_text(_note("n2", "Note One", "다른 내용 (p.1)", "- 2026-07-21 작성"), encoding="utf-8")
        r4 = promote(str(ws), str(src4), apply=True)
        if r4["action"] != "rejected" or not any("B4" in p for p in r4["problems"]):
            failures.append(f"B4 제목 중복 미탐지: {r4['action']} {r4['problems']}")

        # R1 major-1: workspace 밖 src → apply=True여도 거부·정본 미생성 (외부 입력 승격 우회 봉쇄)
        import tempfile as _tf
        with _tf.TemporaryDirectory() as outside:
            ext = Path(outside) / "valid-looking.md"
            ext.write_text(_note("ext-note", "External Note", "완벽한 lint 통과 내용 (p.1)",
                                 "- 2026-07-20 작성"), encoding="utf-8")
            r_out = promote(str(ws), str(ext), apply=True)
            if r_out["action"] != "rejected" or not any("위치 위반" in p for p in r_out["problems"]):
                failures.append(f"outside-src 미거부: {r_out['action']} {r_out['problems']}")
            if (ws / NOTES_REL / "ext-note.md").exists():
                failures.append("outside-src가 정본에 쓰임 (위치 게이트 실패)")
        # workspace 하위지만 허용 외 폴더(60-data 등)도 거부
        other = ws / "60-data"
        other.mkdir(exist_ok=True)
        src_other = other / "sneak.md"
        src_other.write_text(_note("sneak", "Sneak Note", "내용 (p.1)", "- 2026-07-20 작성"),
                             encoding="utf-8")
        r_sn = promote(str(ws), str(src_other), apply=True)
        if r_sn["action"] != "rejected" or (ws / NOTES_REL / "sneak.md").exists():
            failures.append(f"허용 외 폴더 src 미거부: {r_sn['action']}")

        # 출처 없는 산출물 거부(B8)
        src5 = drafts / "bad.md"
        src5.write_text("---\nid: bad\ntitle: Bad\ncreated: 2026-07-20\ntags: [x]\n---\n"
                        "## Compiled Truth\n\n출처 없음\n\n## Timeline\n\n- x\n", encoding="utf-8")
        r5 = promote(str(ws), str(src5), apply=True)
        if r5["action"] != "rejected" or (ws / NOTES_REL / "bad.md").exists():
            failures.append(f"B8 출처 게이트 실패: {r5['action']}")

    if failures:
        print("SELF-TEST FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print("SELF-TEST PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="wiki 정본 승격 게이트 (기본 dry-run · --apply는 승인 후)")
    ap.add_argument("src", nargs="?", help="승격할 산출물 .md (40-drafts/ 또는 80-reports/)")
    ap.add_argument("--workspace", default=".", help="워크스페이스 루트 (기본: 현재 폴더)")
    ap.add_argument("--apply", action="store_true", help="정본에 실제 쓰기 (미지정 시 dry-run)")
    ap.add_argument("--self-test", action="store_true", help="외부 의존 없는 자체 검사")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(_self_test())
    if not a.src:
        ap.error("src 인자가 필요합니다 (또는 --self-test)")
    r = promote(a.workspace, a.src, apply=a.apply)
    if r["problems"]:
        print(f"승격 거부 ({r['id']}) — 게이트 위반:")
        for p in r["problems"]:
            print("  -", p)
        sys.exit(1)
    if r["action"].startswith("dry-run"):
        print(f"[dry-run] {r['id']}: {r['action']} → {r['dest']}")
        print("--- diff 미리보기 ---")
        print(r["diff"] or "(변경 없음)")
        print("승인되면 --apply 로 실제 승격하세요.")
    else:
        print(f"[applied] {r['id']}: {r['action']} → {r['dest']}")
        print(f"manifest 기록: {r.get('manifest_line')}")


if __name__ == "__main__":
    main()
