#!/usr/bin/env python3
"""범용 요약 결정론 검수 — 3중 검증의 1차(자가검증)·2차(독립 실측) 공용 도구.

각 요약 md가 규격을 지키는지 결정론으로 검사한다(눈대중 대체):
  - 플레이스홀더 잔존 0 (스켈레톤 미작성 슬롯)
  - 필수 섹션 존재: '## Summary', '## Why', '## Evidence'
  - 페이지 인용 ≥ min-cites (기본 3) — 정규식 p.\d+ / Table \d / Figure \d
  - source_pdf 표기 존재

사용:  python verify_summaries.py --dir <워크스페이스>/40-drafts/<cat>   [--min-cites 3]
반환:  0=전건 PASS · 1=FAIL 존재 (FAIL 파일·사유 목록 출력)
"""
import argparse
import re
import sys
from pathlib import Path

PLACEHOLDER = re.compile(r"\(워커 작성|\(작성 필요|\bTODO\b|<채우세요>|\{\{[A-Z_]+\}\}")
CITE = re.compile(r"p\.\s*\d+|Table\s*\d|Figure\s*\d|Fig\.\s*\d|§\s*\d", re.IGNORECASE)
REQUIRED = ["## Summary", "## Why", "## Evidence"]


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--min-cites", type=int, default=3)
    args = ap.parse_args()
    d = Path(args.dir)
    if not d.exists():
        print(f"[verify] 없음: {d}", file=sys.stderr)
        return 2
    mds = sorted(d.glob("*.md"))
    total, bad = 0, 0
    for m in mds:
        total += 1
        fails = check(m, args.min_cites)
        if fails:
            bad += 1
            print(f"  [FAIL] {m.name}: {'; '.join(fails)}")
    ok = total - bad
    print(f"검수: 파일 {total} · PASS {ok} · FAIL {bad}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
