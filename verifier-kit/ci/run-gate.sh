#!/usr/bin/env bash
# [verifier-kit] CI 게이트 러너 — 로컬·CI 동일 진입점 (이중 구현 금지)
#
# 모든 검수 에이전트를 한 번에 검증한다:
#   ① verify_core·grade_core self-test (엔진 무결성)
#   ② 각 다이얼(dials/*.json)의 매설 스위트를 grade_core로 채점 → 거부율 임계·과차단 게이트
#
# 다이얼은 자동 발견한다 — 새 에이전트(dials/X.json + ev/X/)를 추가해도 이 스크립트·CI를
# 고칠 필요가 없다. ev/<다이얼명>/ 폴더와 그 안 corpus.sample.json 이 있으면 자동 채점 대상.
#
# 임계는 환경변수로 조정: MIN_REJECT(기본 0.8). 미달·과차단·self-test 실패 시 exit 1.
# 사용:  bash ci/run-gate.sh            # 전체 게이트
#        MIN_REJECT=1.0 bash ci/run-gate.sh
set -uo pipefail

cd "$(dirname "$0")/.." || exit 2   # verifier-kit/ 로 이동
KIT="$PWD"
MIN_REJECT="${MIN_REJECT:-0.8}"
PY="${PYTHON:-python3}"
fail=0

hr() { printf '%s\n' "────────────────────────────────────────────────────────"; }

echo "verifier-kit CI 게이트 · MIN_REJECT=$MIN_REJECT · $($PY --version 2>&1)"
hr

# ── ① 엔진 self-test ────────────────────────────────────────────────
echo "[1/2] 엔진 self-test"
for mod in verify_core grade_core; do
  if $PY "$KIT/$mod.py" --self-test >/tmp/vk-$mod.log 2>&1; then
    echo "  ✓ $mod --self-test PASS"
  else
    echo "  ✗ $mod --self-test FAIL"; sed 's/^/      /' /tmp/vk-$mod.log; fail=1
  fi
done
hr

# ── ② 다이얼별 매설 스위트 채점 (자동 발견) ─────────────────────────
echo "[2/2] 에이전트 매설 스위트 채점 (거부율 ≥ $MIN_REJECT · 과차단 0)"
graded=0
for dial in "$KIT"/dials/*.json; do
  [ -e "$dial" ] || continue
  name="$(basename "$dial" .json)"
  evdir="$KIT/ev/$name"
  corpus="$evdir/corpus.sample.json"
  if [ ! -d "$evdir" ]; then
    echo "  ⚠ $name: ev/$name/ 없음 — 매설 스위트 미구성(스킵). 새 다이얼은 스위트를 갖춰야 게이트된다."
    continue
  fi
  if [ ! -f "$corpus" ]; then
    echo "  ✗ $name: ev/$name/corpus.sample.json 없음 — fail-closed(원문 없이 채점 불가)"; fail=1; continue
  fi
  graded=$((graded+1))
  out="$($PY "$KIT/grade_core.py" --ev-dir "$evdir" --dial "$dial" --corpus "$corpus" \
           --min-reject "$MIN_REJECT" 2>&1)"
  rc=$?
  summary="$(printf '%s\n' "$out" | grep '^채점' || true)"
  echo "  $name: $summary"
  if [ $rc -ne 0 ]; then
    printf '%s\n' "$out" | grep -E '^(FAIL|  ⚠)' | sed 's/^/      /'
    fail=1
  fi
done

if [ "$graded" -eq 0 ]; then
  echo "  ✗ 채점된 에이전트 0개 — dials/*.json 과 ev/*/ 를 확인하라"; fail=1
fi
hr

if [ "$fail" -ne 0 ]; then
  echo "게이트 실패 — 위 항목을 수정하라."
  exit 1
fi
echo "게이트 통과 — 엔진·전 에이전트 매설 거부율 충족·과차단 0."
