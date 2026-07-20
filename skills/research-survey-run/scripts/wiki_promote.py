#!/usr/bin/env python3
"""wiki_promote — 검증 통과 산출물을 wiki 정본으로 승격하는 게이트.

입력: 워크스페이스의 40-drafts/ 요약 또는 80-reports/ 서베이 (.md).
정본: <workspace>/20-knowledge-base/wiki/notes/<id>.md.

★"정본 직접 쓰기 금지"(phase_contracts §9)를 코드로 강제한다:
  - 기본은 dry-run — diff 미리보기만 출력하고 정본을 건드리지 않는다.
  - --apply 는 승인 후에만. 승격 전 노트 스키마 lint(frontmatter 필수키 + 출처 인용 존재)를
    강제하고, lint 실패 시 승격을 거부한다(garbage-in 차단).
  - 승격 이력을 manifest(JSONL)에 append 기록 — 되짚기 가능한 감사선.

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

REQUIRED_KEYS = ("id", "title", "source")   # 노트 스키마 필수 frontmatter 키
# 출처 인용 신호: source 프론트매터가 비어있어도 본문에 페이지/표/arXiv/DOI 인용이 있으면 통과
_CITATION_RE = re.compile(r"(p\.?\s?\d+|Table\s+\d+|Figure\s+\d+|arXiv:\S+|doi:\S+|https?://)", re.I)

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.S)
_KV_RE = re.compile(r"([A-Za-z_][\w-]*):\s*(.*)$")


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


def lint_note(text):
    """노트 스키마 lint → 위반 목록(빈 목록=통과). 필수키 + 출처 인용 존재."""
    fm, body = parse_frontmatter(text)
    problems = []
    for key in REQUIRED_KEYS:
        if not fm.get(key):
            problems.append(f"frontmatter 필수키 누락/빈값: {key}")
    has_source = bool(fm.get("source")) or bool(_CITATION_RE.search(body))
    if not has_source:
        problems.append("출처 인용 없음 (source 프론트매터 또는 본문에 페이지/표/arXiv/DOI/URL 인용 필요)")
    return problems, fm


def _target_id(text, src_path):
    fm, _ = parse_frontmatter(text)
    return fm.get("id") or Path(src_path).stem


def _diff(old, new, path):
    return "".join(difflib.unified_diff(
        old.splitlines(keepends=True), new.splitlines(keepends=True),
        fromfile=f"a/{path}", tofile=f"b/{path}"))


def promote(workspace, src_file, apply=False):
    """단일 산출물 승격. 반환: {id, action, problems, diff, manifest_line?}."""
    ws = Path(workspace)
    src = Path(src_file)
    if not src.exists():
        raise SystemExit(f"입력 파일 없음: {src}")
    text = src.read_text(encoding="utf-8")
    problems, _ = lint_note(text)
    nid = _target_id(text, src)
    notes_dir = ws / NOTES_REL
    dest = notes_dir / f"{nid}.md"
    old = dest.read_text(encoding="utf-8") if dest.exists() else ""
    diff = _diff(old, text, f"{NOTES_REL}/{nid}.md")
    action = ("update" if dest.exists() else "create") if not problems else "rejected"

    result = {"id": nid, "action": action, "problems": problems,
              "diff": diff, "dest": str(dest), "src": str(src)}

    if problems:
        return result  # lint 실패 → 승격 거부 (apply 여부 무관)
    if not apply:
        result["action"] = f"dry-run:{action}"
        return result

    # --apply: 정본 쓰기 + manifest append
    notes_dir.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    line = {
        "ts": str(date.today()),
        "id": nid,
        "action": action,
        "src": str(src),
        "dest": str(dest),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }
    manifest = ws / MANIFEST_REL
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    result["manifest_line"] = line
    return result


def _self_test():
    import tempfile
    failures = []

    # 단위: lint — 출처 없는 노트 거부, 있는 노트 통과
    bad = "---\nid: x\ntitle: T\n---\n출처 없는 본문.\n"
    good = "---\nid: x\ntitle: T\nsource: arXiv:1, p.2\n---\n근거 있는 본문.\n"
    if not lint_note(bad)[0]:
        failures.append("lint: 출처 없는 노트를 통과시킴")
    if lint_note(good)[0]:
        failures.append(f"lint: 정상 노트를 거부함: {lint_note(good)[0]}")

    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        drafts = ws / "40-drafts"
        drafts.mkdir(parents=True)
        src = drafts / "note1.md"
        src.write_text(
            "---\nid: note1\ntitle: Note One\nsource: arXiv:2401.1, Table 2, p.4\n---\n"
            "핵심 결과: Entity F1 39.11 (Table 1, p.6).\n", encoding="utf-8")

        # dry-run: 정본 미생성
        r = promote(str(ws), str(src), apply=False)
        dest = ws / NOTES_REL / "note1.md"
        if dest.exists():
            failures.append("dry-run인데 정본이 생성됨 (정본 직접 쓰기 금지 위반)")
        if not r["action"].startswith("dry-run"):
            failures.append(f"dry-run action 이상: {r['action']}")
        if not r["diff"]:
            failures.append("dry-run diff 비어있음")

        # apply: 정본 생성 + manifest append
        r2 = promote(str(ws), str(src), apply=True)
        if not dest.exists():
            failures.append("apply인데 정본 미생성")
        manifest = ws / MANIFEST_REL
        if not manifest.exists() or not manifest.read_text(encoding="utf-8").strip():
            failures.append("manifest JSONL 미기록")
        else:
            rec = json.loads(manifest.read_text(encoding="utf-8").strip().splitlines()[-1])
            if rec["id"] != "note1" or "sha256" not in rec:
                failures.append(f"manifest 레코드 이상: {rec}")

        # 출처 없는 산출물은 apply여도 거부
        badsrc = drafts / "bad.md"
        badsrc.write_text("---\nid: bad\ntitle: Bad\n---\n출처 없음.\n", encoding="utf-8")
        r3 = promote(str(ws), str(badsrc), apply=True)
        if r3["action"] != "rejected":
            failures.append(f"출처 없는 산출물을 승격함: {r3['action']}")
        if (ws / NOTES_REL / "bad.md").exists():
            failures.append("lint 실패 산출물이 정본에 쓰임 (garbage-in 차단 실패)")

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
        print(f"승격 거부 ({r['id']}) — lint 위반:")
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
