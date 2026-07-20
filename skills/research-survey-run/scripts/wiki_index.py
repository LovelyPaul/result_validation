#!/usr/bin/env python3
"""wiki_index — 워크스페이스 wiki 노트를 검색 색인으로 빌드.

대상: <workspace>/20-knowledge-base/wiki/notes/*.md (id/title/tags/body).
색인 산출: <workspace>/20-knowledge-base/wiki/.index/
  - FTS5 가용 시  : wiki.db (SQLite FTS5 가상테이블 — bm25() 랭킹은 wiki_query가 사용)
  - 어느 경우든   : manifest.json (mode·노트 수·id 목록 — 지속 색인 아티팩트)

★FTS5 가용성은 이 머신 python에서 실측한다(CREATE VIRTUAL TABLE ... USING fts5). 가용하면
FTS5 경로, 불가하면 순수 파이썬 bigram BM25 단독 폴백(색인 db 없이 wiki_query가 노트를 직접
읽어 랭킹). 어느 쪽이든 동작을 보장하고 mode를 manifest·stdout에 명시한다.

의존: python3 표준 라이브러리만 (pyyaml 금지 — frontmatter는 정규식 파싱).
자체 검사: `python3 wiki_index.py --self-test` (외부 의존 0·tempfile 격리).
"""
import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

WIKI_REL = "20-knowledge-base/wiki"
NOTES_REL = f"{WIKI_REL}/notes"
INDEX_REL = f"{WIKI_REL}/.index"

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.S)
_KV_RE = re.compile(r"([A-Za-z_][\w-]*):\s*(.*)$")


def parse_frontmatter(text):
    """정규식 frontmatter 파서(pyyaml 미사용). 단일값·인라인 리스트([a, b])만 지원.
    반환: (frontmatter_dict, body_text)."""
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


def fts5_available():
    """이 머신 python에서 FTS5 실측 — 메모리 db에 가상테이블 생성 시도."""
    try:
        c = sqlite3.connect(":memory:")
        c.execute("CREATE VIRTUAL TABLE _probe USING fts5(a)")
        c.close()
        return True
    except sqlite3.OperationalError:
        return False


def load_notes(notes_dir):
    """notes/*.md → [{id, title, tags, body, path}]. id는 frontmatter id 우선, 없으면 파일 stem."""
    out = []
    for p in sorted(Path(notes_dir).glob("*.md")):
        fm, body = parse_frontmatter(p.read_text(encoding="utf-8"))
        tags = fm.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        out.append({
            "id": fm.get("id") or p.stem,
            "title": fm.get("title") or p.stem,
            "tags": tags,
            "body": body.strip(),
            "path": str(p),
        })
    return out


def build_index(workspace):
    ws = Path(workspace)
    notes_dir = ws / NOTES_REL
    index_dir = ws / INDEX_REL
    if not notes_dir.exists():
        raise SystemExit(f"노트 폴더 없음: {notes_dir} — 먼저 노트를 두거나 워크스페이스 경로를 확인하세요.")
    index_dir.mkdir(parents=True, exist_ok=True)
    notes = load_notes(notes_dir)
    has_fts5 = fts5_available()
    mode = "fts5" if has_fts5 else "python-fallback"
    db_path = index_dir / "wiki.db"

    if has_fts5:
        if db_path.exists():
            db_path.unlink()
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("CREATE VIRTUAL TABLE notes USING fts5(id, title, tags, body)")
            conn.executemany(
                "INSERT INTO notes(id, title, tags, body) VALUES (?,?,?,?)",
                [(n["id"], n["title"], " ".join(n["tags"]), n["body"]) for n in notes],
            )
            conn.commit()
        finally:
            conn.close()
    else:
        # 폴백: FTS5 db를 만들지 않는다. wiki_query의 순수 파이썬 bigram BM25가 노트를 직접 읽어 랭킹.
        if db_path.exists():
            db_path.unlink()

    manifest = {
        "mode": mode,
        "fts5_available": has_fts5,
        "note_count": len(notes),
        "note_ids": [n["id"] for n in notes],
        "db": "wiki.db" if has_fts5 else None,
    }
    (index_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest, index_dir


def _self_test():
    import tempfile
    failures = []
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        notes = ws / NOTES_REL
        notes.mkdir(parents=True)
        (notes / "alpha.md").write_text(
            "---\nid: alpha\ntitle: Alpha Note\ntags: [llm, pretraining]\n"
            "source: arXiv:2401.00001, Table 1, p.6\n---\n"
            "대규모 언어모델 사전학습에서 데이터 품질이 성능을 좌우한다.\n", encoding="utf-8")
        (notes / "beta.md").write_text(
            "---\nid: beta\ntitle: Beta Note\ntags: [medical]\n"
            "source: arXiv:2402.00002, p.3\n---\n"
            "의료 영상 분할에서 합성 데이터 증강 효과를 측정한다.\n", encoding="utf-8")

        manifest, index_dir = build_index(str(ws))

        if manifest["note_count"] != 2:
            failures.append(f"note_count 기대 2, 실제 {manifest['note_count']}")
        if set(manifest["note_ids"]) != {"alpha", "beta"}:
            failures.append(f"note_ids 불일치: {manifest['note_ids']}")
        if manifest["mode"] not in ("fts5", "python-fallback"):
            failures.append(f"mode 이상: {manifest['mode']}")
        if not (index_dir / "manifest.json").exists():
            failures.append("manifest.json 미생성")
        if manifest["mode"] == "fts5" and not (index_dir / "wiki.db").exists():
            failures.append("fts5 모드인데 wiki.db 미생성")

        # frontmatter 파서 단위 검증
        fm, body = parse_frontmatter(
            "---\nid: x\ntitle: T\ntags: [a, b]\n---\nBODY line\n")
        if fm.get("id") != "x" or fm.get("tags") != ["a", "b"] or "BODY" not in body:
            failures.append(f"frontmatter 파서 오류: {fm} / {body!r}")

    if failures:
        print("SELF-TEST FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print(f"SELF-TEST PASS (fts5_available={fts5_available()})")
    return 0


def main():
    ap = argparse.ArgumentParser(description="wiki 노트 검색 색인 빌드 (FTS5 또는 python 폴백)")
    ap.add_argument("--workspace", default=".", help="워크스페이스 루트 (기본: 현재 폴더)")
    ap.add_argument("--self-test", action="store_true", help="외부 의존 없는 자체 검사")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(_self_test())
    manifest, index_dir = build_index(a.workspace)
    print(f"색인 완료: mode={manifest['mode']} · 노트 {manifest['note_count']}건 · {index_dir}")
    if manifest["mode"] == "python-fallback":
        print("  (FTS5 미가용 — wiki_query가 순수 파이썬 bigram BM25로 랭킹합니다.)")


if __name__ == "__main__":
    main()
