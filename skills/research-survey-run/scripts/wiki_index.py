#!/usr/bin/env python3
"""wiki_index — 워크스페이스 wiki 노트를 검색 색인 + 링크 그래프로 빌드.

대상: <workspace>/20-knowledge-base/wiki/notes/*.md (id/title/tags/body).
색인 산출: <workspace>/20-knowledge-base/wiki/.index/
  - FTS5 가용 시  : wiki.db (SQLite FTS5 가상테이블 — bm25() 랭킹은 wiki_query가 사용)
  - 어느 경우든   : manifest.json (mode·노트 수·id·sha 맵·감사 결과) + edges.json (링크 엣지)

LLM-wiki 운영 규칙(gbrain·knowledge-manager 증류 — LLM_WIKI_RULES_DISTILLED.md) 반영:
  - B6 zero-LLM 링크 추출: 매 색인마다 정규식으로 [[..]] 위키링크를 엣지 테이블로 추출
    (LLM 0토큰 — E3 메타연산 결정론). 엣지에 src·dst·exists·extracted_at 기록(B8 이력).
  - D2 감사 체크: orphan(들어오고 나가는 링크 0)·broken link(대상 노트 부재)를 리포트.
  - C4 델타 색인: manifest의 노트 sha256과 대조해 변경분(추가/수정/삭제)만 FTS5 행 갱신.
    변경 0이면 재색인 생략.

★FTS5 가용성은 이 머신 python에서 실측한다. 불가하면 순수 파이썬 bigram BM25 단독 폴백
(색인 db 없이 wiki_query가 노트를 직접 읽어 랭킹). 어느 쪽이든 동작 보장·mode 명시.

의존: python3 표준 라이브러리만 (pyyaml 금지 — frontmatter는 정규식 파싱).
자체 검사: `python3 wiki_index.py --self-test` (외부 의존 0·tempfile 격리).
"""
import argparse
import hashlib
import json
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

WIKI_REL = "20-knowledge-base/wiki"
NOTES_REL = f"{WIKI_REL}/notes"
INDEX_REL = f"{WIKI_REL}/.index"

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.S)
_KV_RE = re.compile(r"([A-Za-z_][\w-]*):\s*(.*)$")
_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")   # [[id]]·[[id|별칭]]·[[id#헤딩]]


def parse_frontmatter(text):
    """정규식 frontmatter 파서(pyyaml 미사용). 단일값·인라인 리스트([a, b])만 지원."""
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


REQUIRED_KEYS = ("id", "title", "created", "tags")   # A3 노트 스키마 필수 frontmatter 키


def load_notes(notes_dir):
    """notes/*.md → ([{id, title, tags, body, sha, path}], skipped).
    **스키마 fail-closed**: A3 필수키(id/title/created/tags)가 없는 .md는 노트로 취급하지 않고
    skip 목록에 명시 기록한다 — 템플릿 README.md 등 비노트 파일이 색인에 혼입되는 것을 차단
    (v0.4.0 R1 major-1, reviewer-codex 재현 시나리오). 노트 id 유일성은 wiki 기본 불변식 —
    중복 id 발견 시 fail-closed(SystemExit). 조용한 dict 붕괴 금지 (v0.3.0 R1 major-3)."""
    out = []
    skipped = []
    seen = {}
    for p in sorted(Path(notes_dir).glob("*.md")):
        text = p.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        missing = [k for k in REQUIRED_KEYS if not fm.get(k)]
        if missing:
            skipped.append({"path": str(p), "missing": missing})
            continue
        nid = fm["id"]
        if nid in seen:
            raise SystemExit(
                f"duplicate note id '{nid}' — {seen[nid]} ↔ {p}. 노트 id는 유일해야 한다"
                f"(fail-closed). 한쪽 노트의 frontmatter id를 바꾼 뒤 다시 색인하라.")
        seen[nid] = p
        tags = fm.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        out.append({
            "id": nid,
            "title": fm.get("title") or p.stem,
            "tags": tags,
            "source": fm.get("source", ""),
            "body": body.strip(),
            "sha": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "path": str(p),
        })
    return out, skipped


def extract_edges(notes):
    """B6 zero-LLM 링크 추출 — 본문 [[..]] → 엣지 목록(결정 정렬·dedup).
    각 엣지: src·dst·exists(대상 노트 실존)·extracted_at (B8 이력)."""
    ids = {n["id"] for n in notes}
    today = str(date.today())
    edges = []
    seen = set()
    for n in notes:
        for dst in _WIKILINK_RE.findall(n["body"]):
            dst = dst.strip()
            key = (n["id"], dst)
            if not dst or key in seen:
                continue
            seen.add(key)
            edges.append({"src": n["id"], "dst": dst, "exists": dst in ids, "extracted_at": today})
    return sorted(edges, key=lambda e: (e["src"], e["dst"]))


def audit(notes, edges):
    """D2 감사 — orphan(in=out=0)·broken link(dst 부재) 결정론 리포트."""
    ids = {n["id"] for n in notes}
    has_out = {e["src"] for e in edges}
    has_in = {e["dst"] for e in edges if e["exists"]}
    orphans = sorted(ids - has_out - has_in)
    broken = [{"src": e["src"], "dst": e["dst"]} for e in edges if not e["exists"]]
    return {"orphans": orphans, "broken_links": broken}


def _load_prev_manifest(index_dir):
    p = Path(index_dir) / "manifest.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def build_index(workspace):
    ws = Path(workspace)
    notes_dir = ws / NOTES_REL
    index_dir = ws / INDEX_REL
    if not notes_dir.exists():
        raise SystemExit(f"노트 폴더 없음: {notes_dir} — 먼저 노트를 두거나 워크스페이스 경로를 확인하세요.")
    index_dir.mkdir(parents=True, exist_ok=True)
    notes, skipped = load_notes(notes_dir)
    has_fts5 = fts5_available()
    mode = "fts5" if has_fts5 else "python-fallback"
    db_path = index_dir / "wiki.db"

    # C4 델타 감지: 이전 manifest sha 맵과 대조
    prev = _load_prev_manifest(index_dir)
    prev_shas = (prev or {}).get("note_shas") or {}
    cur_shas = {n["id"]: n["sha"] for n in notes}
    added = sorted(set(cur_shas) - set(prev_shas))
    removed = sorted(set(prev_shas) - set(cur_shas))
    changed = sorted(i for i in set(cur_shas) & set(prev_shas) if cur_shas[i] != prev_shas[i])
    delta = {"added": added, "changed": changed, "removed": removed}
    no_change = not (added or changed or removed)

    if has_fts5:
        if db_path.exists() and prev and (prev.get("mode") == "fts5"):
            if not no_change:
                # 델타 반영: 변경/삭제 행 제거 → 추가/변경 행 삽입 (C4 — 변경 노트만)
                conn = sqlite3.connect(str(db_path))
                try:
                    for nid in changed + removed:
                        conn.execute("DELETE FROM notes WHERE id = ?", (nid,))
                    by_id = {n["id"]: n for n in notes}
                    conn.executemany(
                        "INSERT INTO notes(id, title, tags, body) VALUES (?,?,?,?)",
                        [(by_id[i]["id"], by_id[i]["title"], " ".join(by_id[i]["tags"]), by_id[i]["body"])
                         for i in added + changed],
                    )
                    conn.commit()
                finally:
                    conn.close()
        else:
            # 전체 빌드 (최초 또는 모드 전환)
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
        if db_path.exists():
            db_path.unlink()

    # B6 엣지 + D2 감사 (매 색인마다 — zero-LLM 결정론)
    edges = extract_edges(notes)
    audit_result = audit(notes, edges)
    # id↔파일 stem 불일치도 감사에 포함 (R1 major-3 — 위키링크 [[id]]와 파일명이 어긋나면 추적 혼선)
    audit_result["id_stem_mismatch"] = [
        {"id": n["id"], "stem": Path(n["path"]).stem} for n in notes
        if Path(n["path"]).stem != n["id"]]
    (index_dir / "edges.json").write_text(
        json.dumps(edges, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "mode": mode,
        "fts5_available": has_fts5,
        "note_count": len(notes),
        "note_ids": [n["id"] for n in notes],
        "skipped": skipped,
        "note_shas": cur_shas,
        "delta": delta,
        "edge_count": len(edges),
        "audit": audit_result,
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
            "---\nid: alpha\ntitle: Alpha\ncreated: 2026-07-20\ntags: [llm]\nsource: arXiv:1, p.6\n---\n"
            "## Compiled Truth\n\n[[beta]] 참조·[[ghost]] 참조.\n\n## Timeline\n\n- 2026-07-20 작성\n",
            encoding="utf-8")
        (notes / "beta.md").write_text(
            "---\nid: beta\ntitle: Beta\ncreated: 2026-07-20\ntags: [medical]\nsource: arXiv:2, p.3\n---\n"
            "## Compiled Truth\n\n내용.\n\n## Timeline\n\n- 2026-07-20 작성\n", encoding="utf-8")
        (notes / "loner.md").write_text(
            "---\nid: loner\ntitle: Loner\ncreated: 2026-07-20\ntags: [x]\nsource: p.1\n---\n"
            "## Compiled Truth\n\n링크 없음.\n\n## Timeline\n\n- 2026-07-20 작성\n", encoding="utf-8")

        m1, index_dir = build_index(str(ws))
        # B6: [[beta]](실존)·[[ghost]](부재) 엣지 추출
        edges = json.loads((index_dir / "edges.json").read_text(encoding="utf-8"))
        pairs = {(e["src"], e["dst"], e["exists"]) for e in edges}
        if ("alpha", "beta", True) not in pairs or ("alpha", "ghost", False) not in pairs:
            failures.append(f"B6 엣지 추출 오류: {pairs}")
        if edges and "extracted_at" not in edges[0]:
            failures.append("B6 엣지 extracted_at 누락")
        # D2: loner=orphan, alpha→ghost=broken
        if "loner" not in m1["audit"]["orphans"]:
            failures.append(f"D2 orphan 미탐지: {m1['audit']['orphans']}")
        if {"src": "alpha", "dst": "ghost"} not in m1["audit"]["broken_links"]:
            failures.append(f"D2 broken link 미탐지: {m1['audit']['broken_links']}")
        # C4: 재실행 → 변경 0
        m2, _ = build_index(str(ws))
        if m2["delta"] != {"added": [], "changed": [], "removed": []}:
            failures.append(f"C4 무변경 델타 오류: {m2['delta']}")
        # C4: beta 수정 → changed=[beta]
        (notes / "beta.md").write_text(
            "---\nid: beta\ntitle: Beta\ncreated: 2026-07-20\ntags: [medical]\nsource: arXiv:2, p.3\n---\n"
            "## Compiled Truth\n\n수정된 내용.\n\n## Timeline\n\n- 2026-07-20 작성\n- 2026-07-21 수정\n",
            encoding="utf-8")
        m3, _ = build_index(str(ws))
        if m3["delta"]["changed"] != ["beta"] or m3["delta"]["added"] or m3["delta"]["removed"]:
            failures.append(f"C4 변경 델타 오류: {m3['delta']}")
        # v0.4.0 R1 major-1: 필수키 없는 .md(README 등)는 노트로 취급하지 않고 skip 명시
        (notes / "README.md").write_text("# wiki notes 안내문 — frontmatter 없음\n", encoding="utf-8")
        m_r, _ = build_index(str(ws))
        if m_r["note_count"] != 3 or "README" in " ".join(m_r["note_ids"]):
            failures.append(f"README 혼입 차단 실패: count={m_r['note_count']} ids={m_r['note_ids']}")
        if not any(s["path"].endswith("README.md") and set(s["missing"]) == set(REQUIRED_KEYS)
                   for s in m_r["skipped"]):
            failures.append(f"skip 목록 기록 오류: {m_r['skipped']}")
        (notes / "README.md").unlink()

        # R1 major-3: 중복 frontmatter id → fail-closed (조용한 붕괴 금지)
        (notes / "dup1.md").write_text(
            "---\nid: dup\ntitle: D1\ncreated: 2026-07-20\ntags: [x]\nsource: p.1\n---\n"
            "## Compiled Truth\n\nA\n\n## Timeline\n\n- x\n", encoding="utf-8")
        (notes / "dup2.md").write_text(
            "---\nid: dup\ntitle: D2\ncreated: 2026-07-20\ntags: [x]\nsource: p.1\n---\n"
            "## Compiled Truth\n\nB\n\n## Timeline\n\n- x\n", encoding="utf-8")
        try:
            build_index(str(ws))
            failures.append("중복 id를 fail-closed하지 않음")
        except SystemExit as e:
            if "duplicate note id 'dup'" not in str(e):
                failures.append(f"중복 id 에러 메시지 이상: {e}")
        (notes / "dup2.md").unlink()
        # id↔stem 불일치 감사: dup1.md의 id=dup ≠ stem=dup1
        m4, _ = build_index(str(ws))
        if {"id": "dup", "stem": "dup1"} not in m4["audit"]["id_stem_mismatch"]:
            failures.append(f"id↔stem 불일치 감사 누락: {m4['audit'].get('id_stem_mismatch')}")
        (notes / "dup1.md").unlink()
        m5, _ = build_index(str(ws))  # 정리 후 다음 검증으로

        # FTS5 모드면 델타 반영 후에도 검색 가능해야
        if m3["mode"] == "fts5":
            conn = sqlite3.connect(str(index_dir / "wiki.db"))
            try:
                n = conn.execute("SELECT count(*) FROM notes").fetchone()[0]
                hit = conn.execute("SELECT id FROM notes WHERE notes MATCH ?", ('"수정된"',)).fetchall()
            finally:
                conn.close()
            if n != 3:
                failures.append(f"델타 후 행 수 오류: {n}")
            if not hit or hit[0][0] != "beta":
                failures.append(f"델타 후 FTS5 검색 오류: {hit}")

    if failures:
        print("SELF-TEST FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print(f"SELF-TEST PASS (fts5_available={fts5_available()})")
    return 0


def main():
    ap = argparse.ArgumentParser(description="wiki 노트 검색 색인+링크 그래프 빌드 (FTS5 또는 python 폴백)")
    ap.add_argument("--workspace", default=".", help="워크스페이스 루트 (기본: 현재 폴더)")
    ap.add_argument("--self-test", action="store_true", help="외부 의존 없는 자체 검사")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(_self_test())
    m, index_dir = build_index(a.workspace)
    d = m["delta"]
    print(f"색인 완료: mode={m['mode']} · 노트 {m['note_count']}건 · 엣지 {m['edge_count']}건 · {index_dir}")
    if m["skipped"]:
        print(f"스키마 미충족 skip {len(m['skipped'])}건 (노트로 취급 안 함): "
              f"{[(Path(s['path']).name, s['missing']) for s in m['skipped']]}")
    print(f"델타: +{len(d['added'])} ~{len(d['changed'])} -{len(d['removed'])}"
          + (" (변경 없음 — FTS5 재색인 생략)" if not any(d.values()) else ""))
    a_ = m["audit"]
    if a_["orphans"] or a_["broken_links"]:
        print(f"감사(D2): orphan {len(a_['orphans'])}건 {a_['orphans']} · "
              f"broken link {len(a_['broken_links'])}건 {[(b['src'], b['dst']) for b in a_['broken_links']]}")
    else:
        print("감사(D2): orphan 0 · broken link 0")
    if a_.get("id_stem_mismatch"):
        print(f"감사(D2): id↔stem 불일치 {len(a_['id_stem_mismatch'])}건 "
              f"{[(x['id'], x['stem']) for x in a_['id_stem_mismatch']]}")
    if m["mode"] == "python-fallback":
        print("  (FTS5 미가용 — wiki_query가 순수 파이썬 bigram BM25로 랭킹합니다.)")


if __name__ == "__main__":
    main()
