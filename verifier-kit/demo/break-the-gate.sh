#!/usr/bin/env bash
# 발표 클라이맥스 데모 — "검수기가 약해지면 CI가 막는다"를 라이브로.
#
# 어디서 실행하든 스크립트 위치 기준으로 verifier-kit/ 을 찾는다.
#   bash verifier-kit/demo/break-the-gate.sh
#
# 흐름: BEFORE 거부율 측정 → 매설 하나 무력화 → AFTER 거부율 측정 → 대비 표 → 원복.
# 각 단계는 tty에서 ⏎(엔터)로 멈춘다. 파이프·자동입력으로 돌리면 안 멈추되 단계 라벨은 유지.
# 매설 노트는 자동 원복(Ctrl-C 해도 trap 복구) — 부작용 0.
set -u
KIT="$(cd "$(dirname "$0")/.." && pwd)"                 # verifier-kit/
DIAL="$KIT/dials/code-review.json"
EVDIR="$KIT/ev/code-review"
CORPUS="$EVDIR/corpus.sample.json"
TARGET="$EVDIR/ev-invented-metric.md"                    # 무력화할 매설 노트
BACKUP="$(mktemp)"
MINR=0.8
PY="${PYTHON:-python3}"

restore() { [ -f "$BACKUP" ] && mv "$BACKUP" "$TARGET" 2>/dev/null; }
trap restore EXIT                                         # 중간 이탈에도 원복 보장

# tty일 때만 진짜 멈춤 — 비대화형이면 즉시 통과(단계 라벨은 그대로 보임)
pause() {
  echo
  if [ -t 0 ]; then read -rp "  ⏎ 계속..." _; else echo "  (비대화형 — 자동 진행)"; fi
  echo
}
hr() { printf '%s\n' "──────────────────────────────────────────────"; }

# code-review 에이전트만 채점해 '거부율%'와 exit code를 캡처
grade() {   # $1=라벨 → 전역 RATE, RC 설정 + 요약 1줄 출력
  local out; out="$($PY "$KIT/grade_core.py" --ev-dir "$EVDIR" --dial "$DIAL" \
                      --corpus "$CORPUS" --min-reject "$MINR" 2>&1)"; RC=$?
  RATE="$(printf '%s\n' "$out" | grep -oE '\([0-9]+\.[0-9]+%\)' | head -1 | tr -d '()')"
  printf '  %-8s code-review 거부율 %-7s → exit %s%s\n' \
         "[$1]" "${RATE:-?}" "$RC" "$([ "$RC" -ne 0 ] && echo '  ⛔ 빌드 차단' || echo '  ✅ 통과')"
}

echo "╔══════════════════════════════════════════════╗"
echo "║  검수기가 약해지면 CI가 막는가? — 라이브 증명   ║"
echo "╚══════════════════════════════════════════════╝"
echo
echo "무력화 대상 매설 노트: ev-invented-metric.md — '변경 근거' 절:"
hr
sed -n '/## 변경 근거/,/## 리스크/p' "$TARGET" | sed '/## 리스크/d;/^$/d' | sed 's/^/  /'
hr
echo "  ↑ '99.9%'·'45 tests' 는 원문(diff)에 없는 발명 수치 → 검수기가 잡아야 정상."
pause

echo "═══ 1. BEFORE — 매설 온전한 지금 상태 ═══"
grade BEFORE
BEFORE_RATE="$RATE"; BEFORE_RC="$RC"
echo "     매설 4개(발명 수치 포함) 전부 거부됨."
pause

echo "═══ 2. 검수기 약화 — 매설 하나를 '정상 노트'로 바꿔치기 ═══"
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
echo "  ✎ 발명 수치를 원문 실재 값(91.2% · 12 passed)으로 교체."
echo "     → 이제 이 노트엔 검수기가 잡을 오류가 없다 (검수기가 '눈감음')."
pause

echo "═══ 3. AFTER — 같은 게이트 재실행 ═══"
grade AFTER
AFTER_RATE="$RATE"; AFTER_RC="$RC"
echo "     ev-invented-metric.md 가 'passed'로 새어나가 거부율 하락."
pause

echo "═══ 결과 대비 ═══"
hr
printf '  %-10s %-14s %-12s\n' "" "거부율" "게이트"
printf '  %-10s %-14s %-12s\n' "BEFORE" "${BEFORE_RATE:-?}" "$([ "$BEFORE_RC" -eq 0 ] && echo '✅ 통과' || echo '⛔ 차단')"
printf '  %-10s %-14s %-12s\n' "AFTER"  "${AFTER_RATE:-?}"  "$([ "$AFTER_RC"  -eq 0 ] && echo '✅ 통과' || echo '⛔ 차단')"
hr
echo "  검수기가 오류 하나를 놓치기 시작하자, 게이트가 자동으로 빌드를 막았다."
echo

# 원복
restore; trap - EXIT
grade "원복"
echo
echo "핵심: 누군가 검수기를 약하게 만들면(다이얼 완화·매설 우회) CI가 자동으로 잡는다."
echo "     검수 하네스가 스스로를 감시한다."
