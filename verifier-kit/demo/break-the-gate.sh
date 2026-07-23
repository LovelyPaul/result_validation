#!/usr/bin/env bash
# 발표 클라이맥스 데모 — "검수기가 약해지면 CI가 막는다"를 라이브로.
#
# 어디서 실행하든 스크립트 위치 기준으로 verifier-kit/ 을 찾는다.
#   bash verifier-kit/demo/break-the-gate.sh
# 각 단계 사이 ⏎(엔터)로 진행. 매설 노트는 자동 원복된다(부작용 0).
set -u
KIT="$(cd "$(dirname "$0")/.." && pwd)"    # verifier-kit/
TARGET="$KIT/ev/code-review/ev-invented-metric.md"
BACKUP="$(mktemp)"

restore() { [ -f "$BACKUP" ] && mv "$BACKUP" "$TARGET" 2>/dev/null; }
trap restore EXIT                          # 중간에 Ctrl-C 해도 원복 보장

pause() { echo; read -rp "  ⏎ 계속..." _; echo; }

echo "═══ 1. 지금 게이트는 통과한다 (세 에이전트 거부율 100%) ═══"
bash "$KIT/ci/run-gate.sh" | tail -7
pause

echo "═══ 2. 매설 노트를 '완전 정상'으로 바꿔 검수기를 약화시킨다 ═══"
echo "   발명 수치를 원문 실재 값으로 → 검수기가 잡을 게 없어짐(= 검수기가 눈감음)."
cp "$TARGET" "$BACKUP"
cat > "$TARGET" <<'EOF'
<!-- ev_type: invented-metric -->
## 변경 요지
auth 토큰 만료 검사 (src/auth.py:42).
## 변경 근거
- coverage 91.2% 로 상승 (src/auth.py:42)
- "12 passed, 0 failed" (tests/test_auth.py:10)
## 리스크
낮음.
source_diff: PR#123.diff — PR#123
EOF
echo "   ✎ 매설 노트 무력화 완료."
pause

echo "═══ 3. 게이트 재실행 — 거부율이 떨어지면 CI가 막는다 ═══"
bash "$KIT/ci/run-gate.sh"; rc=$?
echo "   → exit code: $rc  (1 = 빌드 차단)"
pause

echo "═══ 4. 원복 ═══"
restore; trap - EXIT
bash "$KIT/ci/run-gate.sh" >/dev/null 2>&1 && echo "   ✓ 원복 후 게이트 통과 (exit 0)"
echo
echo "핵심: 누군가 검수기를 약하게 만들면(다이얼 완화·매설 우회) CI가 자동으로 잡는다."
echo "     검수 하네스가 스스로를 감시한다."
